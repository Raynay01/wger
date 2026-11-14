# This file is part of wger Workout Manager.
#
# wger Workout Manager is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wger Workout Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Workout Manager.  If not, see <http://www.gnu.org/licenses/>.

# Standard Library
import datetime
import zoneinfo

# Django
from django.urls import reverse

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.models import (
    Appointment,
    AppointmentStatus,
)
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.manager.models import Routine
from wger.nutrition.models import (
    Meal,
    NutritionPlan,
)
from wger.physio.models import PhysioProtocol


SAO_PAULO = zoneinfo.ZoneInfo('America/Sao_Paulo')


class CalendarTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    The patient's calendar per day, in the patient's timezone
    """

    monday = datetime.date(2026, 3, 9)

    def setUp(self):
        super().setUp()
        self.build_team()
        self.patient.userprofile.time_zone = 'America/Sao_Paulo'
        self.patient.userprofile.save()
        self.url = reverse('care-calendar')

        routine = Routine(name='Força', start=self.monday)
        start_prescription(routine, self.training_rel, self.trainer)
        routine.end = self.monday + datetime.timedelta(days=27)
        routine.save()
        routine.days.create(name='Pernas', order=1)
        routine.days.create(name='', order=2, is_rest=True)
        routine.publish()

        plan = NutritionPlan(description='Hipertrofia', start=self.monday)
        start_prescription(plan, self.nutrition_rel, self.nutritionist)
        plan.start = self.monday + datetime.timedelta(days=2)
        plan.save()
        Meal.objects.create(plan=plan, name='Almoço', order=1)
        plan.publish()

        protocol = PhysioProtocol(name='Joelho')
        start_prescription(protocol, self.physio_rel, self.physio)
        protocol.start = self.monday
        protocol.end = self.monday + datetime.timedelta(days=1)
        protocol.save()
        protocol.publish()

    def calendar(self, start=None, end=None):
        self.client.force_authenticate(self.patient)
        start = start or self.monday
        end = end or self.monday + datetime.timedelta(days=6)
        return self.client.get(self.url, {'start': start.isoformat(), 'end': end.isoformat()})

    def test_days(self):
        response = self.calendar()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        days = {d['date']: d for d in response.data['days']}
        monday, tuesday, wednesday = (self.monday + datetime.timedelta(days=i) for i in range(3))
        self.assertEqual(days[monday]['training']['day'], 'Pernas')
        self.assertTrue(days[tuesday]['training']['is_rest'])
        self.assertIsNone(days[tuesday]['nutrition'])
        self.assertEqual(days[wednesday]['nutrition'], {'plan': 'Hipertrofia', 'meals': 1})
        self.assertEqual(days[monday]['physio'], ['Joelho'])
        self.assertEqual(days[wednesday]['physio'], [])

    def test_appointment_on_the_patients_day(self):
        """22:30 in São Paulo is the next day in UTC, but the same day for the patient"""
        Appointment.objects.create(
            relationship=self.physio_rel,
            start=datetime.datetime.combine(self.monday, datetime.time(22, 30), tzinfo=SAO_PAULO),
        )
        cancelled = Appointment.objects.create(
            relationship=self.physio_rel,
            start=datetime.datetime.combine(self.monday, datetime.time(9), tzinfo=SAO_PAULO),
            status=AppointmentStatus.CANCELLED,
        )
        days = {d['date']: d for d in self.calendar().data['days']}
        self.assertEqual(len(days[self.monday]['appointments']), 1)
        self.assertNotEqual(days[self.monday]['appointments'][0]['id'], cancelled.pk)
        self.assertEqual(days[self.monday + datetime.timedelta(days=1)]['appointments'], [])

    def test_only_own_modules(self):
        """A nutrition-only patient gets no training in the calendar"""
        self.training_rel.status = 'ended'
        self.training_rel.save()
        self.physio_rel.status = 'ended'
        self.physio_rel.save()
        data = self.calendar().data
        self.assertEqual(data['modules'], ['nutrition'])
        self.assertTrue(all(d['training'] is None and d['physio'] == [] for d in data['days']))

    def test_range_is_limited(self):
        response = self.calendar(end=self.monday + datetime.timedelta(days=62))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AppointmentTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Professionals schedule appointments, both sides can cancel
    """

    def setUp(self):
        super().setUp()
        self.build_team()
        self.url = reverse('appointment-list')

    def schedule(self, user=None, relationship=None):
        self.client.force_authenticate(user or self.physio)
        return self.client.post(
            self.url,
            {
                'relationship': str((relationship or self.physio_rel).pk),
                'kind': 'session',
                'start': '2026-03-10T14:00:00-03:00',
                'duration_minutes': 50,
            },
        )

    def test_schedule_and_cancel_by_patient(self):
        response = self.schedule()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        pk = response.data['id']

        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.get(self.url).data['count'], 1)
        detail = reverse('appointment-detail', kwargs={'pk': pk})
        self.assertEqual(
            self.client.patch(detail, {'duration_minutes': 10}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(reverse('appointment-done', kwargs={'pk': pk})).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        response = self.client.post(reverse('appointment-cancel', kwargs={'pk': pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appointment = Appointment.objects.get(pk=pk)
        self.assertEqual(appointment.status, AppointmentStatus.CANCELLED)
        self.assertEqual(appointment.cancelled_by, self.patient)

    def test_only_for_own_patients(self):
        self.assertEqual(
            self.schedule(user=self.trainer).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.client.force_authenticate(self.trainer)
        self.schedule()
        self.client.force_authenticate(self.trainer)
        self.assertEqual(self.client.get(self.url).data['count'], 0)

    def test_done_by_professional(self):
        pk = self.schedule().data['id']
        response = self.client.post(reverse('appointment-done', kwargs={'pk': pk}))
        self.assertEqual(response.data['status'], AppointmentStatus.DONE)
        response = self.client.patch(
            reverse('appointment-detail', kwargs={'pk': pk}), {'notes': 'x'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

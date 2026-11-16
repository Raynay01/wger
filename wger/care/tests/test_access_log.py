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

# Django
from django.urls import reverse

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.export import export_user_data
from wger.care.models import AccessLog
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.manager.models import (
    Routine,
    TrainingPlan,
)
from wger.physio.models import PainRecord


class OwnModuleReadLogTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Reading the records a patient writes in the professional's own module is
    logged once per patient, resource and day, and shows in the patient's export
    """

    def setUp(self):
        super().setUp()
        self.build_team()

    def read(self, user, url):
        self.client.force_authenticate(user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response

    def logged(self, resource: str):
        return list(
            AccessLog.objects.filter(resource=resource).values_list(
                'actor', 'patient', 'relationship'
            )
        )

    def test_nutrition_diary_once_per_day(self):
        url = reverse('care-relationship-nutrition-diary', kwargs={'pk': self.nutrition_rel.pk})
        self.read(self.nutritionist, url)
        self.read(self.nutritionist, url)
        self.assertEqual(
            self.logged('nutrition_diary'),
            [(self.nutritionist.pk, self.patient.pk, self.nutrition_rel.pk)],
        )

        # The next day counts again
        AccessLog.objects.update(
            timestamp=AccessLog.objects.get().timestamp - datetime.timedelta(days=1)
        )
        self.read(self.nutritionist, url)
        self.assertEqual(len(self.logged('nutrition_diary')), 2)

    def test_workout_logs(self):
        url = reverse('care-relationship-workout-logs', kwargs={'pk': self.training_rel.pk})
        self.read(self.trainer, url)
        self.assertEqual(
            self.logged('workout_logs'),
            [(self.trainer.pk, self.patient.pk, self.training_rel.pk)],
        )

    def test_prescribed_routine_logs(self):
        routine = Routine(name='Força', start=datetime.date(2026, 3, 2))
        start_prescription(routine, self.training_rel, self.trainer)
        routine.end = routine.start + datetime.timedelta(days=27)
        routine.save()
        routine.publish()
        for name in ('routine-logs', 'routine-stats'):
            AccessLog.objects.all().delete()
            self.read(self.trainer, reverse(name, kwargs={'pk': routine.pk}))
            self.assertEqual(
                self.logged('workout_logs'),
                [(self.trainer.pk, self.patient.pk, self.training_rel.pk)],
            )

        # The patient reading their own logs is not a professional's access
        AccessLog.objects.all().delete()
        self.read(self.patient, reverse('routine-logs', kwargs={'pk': routine.pk}))
        self.assertEqual(self.logged('workout_logs'), [])

    def test_training_plan_progress(self):
        self.client.force_authenticate(self.trainer)
        response = self.client.post(
            reverse('training-plan-list'),
            {
                'name': 'Temporada',
                'goal': 'hypertrophy',
                'start': '2026-03-02',
                'care_relationship': str(self.training_rel.pk),
            },
        )
        plan = TrainingPlan.objects.get(pk=response.data['id'])
        self.read(self.trainer, reverse('training-plan-progress', kwargs={'pk': plan.pk}))
        self.assertEqual(
            self.logged('training_progress'),
            [(self.trainer.pk, self.patient.pk, self.training_rel.pk)],
        )

    def test_pain_records_of_followed_patients(self):
        PainRecord.objects.create(user=self.patient, moment='other', value=3)
        PainRecord.objects.create(user=self.physio, moment='other', value=1)
        self.read(self.physio, reverse('pain-record-list'))
        self.assertEqual(
            self.logged('pain_records'),
            [(self.physio.pk, self.patient.pk, self.physio_rel.pk)],
        )

        AccessLog.objects.all().delete()
        self.read(self.patient, reverse('pain-record-list'))
        self.assertEqual(self.logged('pain_records'), [])

    def test_export(self):
        url = reverse('care-relationship-workout-logs', kwargs={'pk': self.training_rel.pk})
        self.read(self.trainer, url)
        reads = export_user_data(self.patient)['care']['reads_of_your_shared_data']
        self.assertEqual(
            [(r['resource'], r['actor__username']) for r in reads],
            [('workout_logs', self.trainer.username)],
        )

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
from unittest import mock

# Django
from django.urls import reverse

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.models import RelationshipStatus
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.exercises.models import Exercise
from wger.manager.models import (
    WorkoutLog,
    WorkoutSession,
)
from wger.nutrition.models import (
    Ingredient,
    LogItem,
    MealAdherence,
    NutritionPlan,
    WaterLog,
)
from wger.physio.models import (
    ExerciseRecord,
    PainRecord,
    PhysioProtocol,
)


SAO_PAULO = zoneinfo.ZoneInfo('America/Sao_Paulo')


class ActivityTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    The last day with a record per follow-up of the professional, in the
    patient's time zone
    """

    monday = datetime.date(2026, 3, 9)

    def setUp(self):
        super().setUp()
        self.build_team()
        self.patient.userprofile.time_zone = 'America/Sao_Paulo'
        self.patient.userprofile.save()
        self.plan = NutritionPlan.objects.create(user=self.patient, description='Plano')
        self.meal = self.plan.meal_set.create(name='Almoço', order=1)
        protocol = PhysioProtocol.objects.create(user=self.patient, name='Joelho')
        self.protocol_exercise = protocol.exercises.create(name='Ponte', order=1)

    def day(self, offset: int) -> datetime.date:
        return self.monday + datetime.timedelta(days=offset)

    def at(self, offset: int, hour: int, minute: int = 0) -> datetime.datetime:
        return datetime.datetime.combine(
            self.day(offset),
            datetime.time(hour, minute),
            tzinfo=SAO_PAULO,
        )

    def activity(self, user, today_offset: int = 6) -> dict:
        self.client.force_authenticate(user)
        with mock.patch('wger.care.consistency.local_today', return_value=self.day(today_offset)):
            response = self.client.get(reverse('care-activity'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return {row['relationship']: row for row in response.data}

    def last(self, user, relationship) -> tuple:
        row = self.activity(user)[str(relationship.pk)]
        return row['last_day'], row['days_since']

    def test_training(self):
        """Sessions and sets count, on the patient's local day"""
        self.assertEqual(self.last(self.trainer, self.training_rel), (None, None))
        WorkoutSession.objects.create(user=self.patient, datetime_start=self.at(3, 23))
        self.assertEqual(self.last(self.trainer, self.training_rel), (self.day(3).isoformat(), 3))
        # A set after midnight joins the session of the evening before
        log = WorkoutLog.objects.create(
            user=self.patient,
            exercise=Exercise.objects.first(),
            repetitions=10,
            date=self.at(4, 0, 30),
        )
        self.assertEqual(log.session.datetime_start, self.at(3, 23))
        self.assertEqual(self.last(self.trainer, self.training_rel), (self.day(4).isoformat(), 2))

    def test_nutrition(self):
        """Diary, meal adherence and water count, the latest of them wins"""
        MealAdherence.objects.create(
            user=self.patient,
            meal=self.meal,
            date=self.day(2),
            status='skipped',
        )
        self.assertEqual(
            self.last(self.nutritionist, self.nutrition_rel), (self.day(2).isoformat(), 4)
        )
        WaterLog.objects.create(user=self.patient, amount_ml=300, datetime=self.at(1, 10))
        self.assertEqual(
            self.last(self.nutritionist, self.nutrition_rel)[0], self.day(2).isoformat()
        )
        LogItem.objects.create(
            plan=self.plan,
            ingredient=Ingredient.objects.first(),
            amount=100,
            datetime=self.at(3, 12),
        )
        self.assertEqual(
            self.last(self.nutritionist, self.nutrition_rel)[0], self.day(3).isoformat()
        )
        # 23:30 in São Paulo is already the next day in UTC
        WaterLog.objects.create(user=self.patient, amount_ml=300, datetime=self.at(4, 23, 30))
        self.assertEqual(
            self.last(self.nutritionist, self.nutrition_rel), (self.day(4).isoformat(), 2)
        )

    def test_physio(self):
        """Exercises and pain records count"""
        ExerciseRecord.objects.create(
            user=self.patient,
            protocol_exercise=self.protocol_exercise,
            datetime=self.at(2, 8),
        )
        self.assertEqual(self.last(self.physio, self.physio_rel)[0], self.day(2).isoformat())
        PainRecord.objects.create(
            user=self.patient, moment='after', value=3, datetime=self.at(6, 9)
        )
        self.assertEqual(self.last(self.physio, self.physio_rel), (self.day(6).isoformat(), 0))

    def test_only_the_own_area(self):
        """A record of another area does not count for the professional"""
        WaterLog.objects.create(user=self.patient, amount_ml=300, datetime=self.at(5, 10))
        self.assertEqual(self.last(self.trainer, self.training_rel), (None, None))
        self.assertEqual(self.last(self.physio, self.physio_rel), (None, None))

    def test_future_record(self):
        WorkoutSession.objects.create(user=self.patient, datetime_start=self.at(8, 7))
        self.assertEqual(self.last(self.trainer, self.training_rel)[1], 0)

    def test_only_open_follow_ups_of_the_professional(self):
        self.assertEqual(list(self.activity(self.trainer)), [str(self.training_rel.pk)])
        self.training_rel.status = RelationshipStatus.ENDED
        self.training_rel.save()
        self.assertEqual(self.activity(self.trainer), {})
        self.assertEqual(self.activity(self.patient), {})

    def test_login_required(self):
        response = self.client.get(reverse('care-activity'))
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

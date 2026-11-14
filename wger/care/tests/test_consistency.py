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
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.exercises.models import Exercise
from wger.manager.models import (
    Routine,
    WorkoutLog,
    WorkoutSession,
)
from wger.nutrition.models import (
    Ingredient,
    LogItem,
    Meal,
    MealAdherence,
    NutritionPlan,
    WaterLog,
)
from wger.physio.models import (
    ExerciseRecord,
    PhysioProtocol,
)


SAO_PAULO = zoneinfo.ZoneInfo('America/Sao_Paulo')


class ConsistencyTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Records per day and week, and the streak, in the patient's timezone
    """

    monday = datetime.date(2026, 3, 9)

    def setUp(self):
        super().setUp()
        self.build_team()
        self.patient.userprofile.time_zone = 'America/Sao_Paulo'
        self.patient.userprofile.save()

        # Training on Monday, Wednesday, Friday and Sunday, rest in between
        self.routine = Routine(name='Força', start=self.monday)
        start_prescription(self.routine, self.training_rel, self.trainer)
        self.routine.end = self.monday + datetime.timedelta(days=27)
        self.routine.save()
        self.routine.days.create(name='Pernas', order=1)
        self.routine.days.create(name='', order=2, is_rest=True)
        self.routine.publish()

        # Food plan from Wednesday on
        self.plan = NutritionPlan(description='Hipertrofia', start=self.monday)
        start_prescription(self.plan, self.nutrition_rel, self.nutritionist)
        self.plan.start = self.day(2)
        self.plan.goal_water_ml = 2000
        self.plan.save()
        self.meal = Meal.objects.create(plan=self.plan, name='Almoço', order=1)
        self.plan.publish()

        # Physio on Monday and Tuesday
        protocol = PhysioProtocol(name='Joelho')
        start_prescription(protocol, self.physio_rel, self.physio)
        protocol.start = self.monday
        protocol.end = self.day(1)
        protocol.save()
        self.protocol_exercise = protocol.exercises.create(name='Ponte', order=1)
        protocol.publish()

    def day(self, offset: int) -> datetime.date:
        return self.monday + datetime.timedelta(days=offset)

    def at(self, offset: int, hour: int, minute: int = 0) -> datetime.datetime:
        return datetime.datetime.combine(
            self.day(offset),
            datetime.time(hour, minute),
            tzinfo=SAO_PAULO,
        )

    def get(self, today: datetime.date, **params):
        self.client.force_authenticate(self.patient)
        with mock.patch('wger.care.consistency.local_today', return_value=today):
            return self.client.get(reverse('care-consistency'), params)

    def record_week(self):
        # Monday: training session and physio
        WorkoutSession.objects.create(
            user=self.patient,
            routine=self.routine,
            datetime_start=self.at(0, 7),
        )
        ExerciseRecord.objects.create(
            user=self.patient,
            protocol_exercise=self.protocol_exercise,
            datetime=self.at(0, 8),
        )
        # Wednesday: no training; food at 22:30, already Thursday in UTC; water goal
        LogItem.objects.create(
            plan=self.plan,
            ingredient=Ingredient.objects.first(),
            amount=100,
            datetime=self.at(2, 22, 30),
        )
        WaterLog.objects.create(user=self.patient, amount_ml=2000, datetime=self.at(2, 12))
        # Thursday: meal recorded as not followed, some water
        MealAdherence.objects.create(
            user=self.patient,
            meal=self.meal,
            date=self.day(3),
            status='skipped',
        )
        WaterLog.objects.create(user=self.patient, amount_ml=500, datetime=self.at(3, 12))
        # Friday: a set logged without a session
        WorkoutLog.objects.create(
            user=self.patient,
            exercise=Exercise.objects.first(),
            repetitions=10,
            date=self.at(4, 18),
        )
        # Saturday (rest): only water
        WaterLog.objects.create(user=self.patient, amount_ml=300, datetime=self.at(5, 10))

    def test_days_and_week(self):
        """Each area per day, the weekly totals and a streak across rest days and today"""
        self.record_week()
        response = self.get(self.day(6), end=self.monday.isoformat(), weeks=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        days = response.data['days']
        self.assertEqual([d['date'] for d in days], [self.day(i).isoformat() for i in range(7)])
        self.assertEqual(
            [d['training'] for d in days],
            ['done', 'rest', 'missed', 'rest', 'done', 'rest', 'planned'],
        )
        self.assertEqual(
            [d['meals'] for d in days],
            [None, None, True, True, False, False, False],
        )
        self.assertEqual(
            [d['water_goal'] for d in days],
            [None, None, True, False, False, False, False],
        )
        self.assertEqual([d['water_ml'] for d in days][2:], [2000, 500, 0, 300, 0])
        self.assertEqual(
            [d['physio'] for d in days],
            [True, False, None, None, None, None, None],
        )
        self.assertEqual(
            [d['recorded'] for d in days],
            [True, False, True, True, True, True, False],
        )

        (week,) = response.data['weeks']
        self.assertEqual(week['start'], self.monday.isoformat())
        self.assertEqual(week['end'], self.day(6).isoformat())
        self.assertEqual(week['training_done'], 2)
        self.assertEqual(week['training_planned'], 4)
        self.assertEqual(week['meals_days'], 2)
        self.assertEqual(week['water_goal_days'], 1)
        self.assertEqual(week['physio_days'], 1)
        self.assertEqual(week['recorded_days'], 5)

        # Saturday to Wednesday, Tuesday (rest), Monday; Sunday is today
        self.assertEqual(response.data['streak'], 5)

    def test_missed_day_breaks_the_streak(self):
        """A day without records that is not a prescribed rest day ends the streak"""
        self.record_week()
        WorkoutSession.objects.filter(user=self.patient, datetime_start=self.at(0, 7)).delete()
        ExerciseRecord.objects.filter(user=self.patient).delete()
        LogItem.objects.filter(plan=self.plan).delete()
        WaterLog.objects.filter(user=self.patient, amount_ml=2000).delete()
        # Wednesday now has nothing: Saturday, Friday and Thursday count
        self.assertEqual(self.get(self.day(6), end=self.monday.isoformat()).data['streak'], 3)
        # On Saturday, the streak is the same
        self.assertEqual(self.get(self.day(5), end=self.monday.isoformat()).data['streak'], 3)
        # On Monday of the next week, the planned Sunday without records ends it
        self.assertEqual(self.get(self.day(7), end=self.day(7).isoformat()).data['streak'], 0)

    def test_eight_weeks_by_default(self):
        """Weeks run from Monday to Sunday, the last one is the week of today"""
        response = self.get(self.day(2))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['weeks']), 8)
        self.assertEqual(len(response.data['days']), 56)
        self.assertEqual(response.data['days'][-1]['date'], self.day(6).isoformat())
        self.assertEqual(response.data['today'], self.day(2).isoformat())

    def test_only_own_modules(self):
        """Areas of disciplines the patient is not followed in stay empty"""
        self.training_rel.status = 'ended'
        self.training_rel.save()
        self.record_week()
        days = self.get(self.day(6), end=self.monday.isoformat(), weeks=1).data['days']
        self.assertEqual({d['training'] for d in days}, {None})
        self.assertFalse(days[4]['recorded'])

    def test_weeks_validation(self):
        """Weeks must be a whole number from 1 to 26"""
        for weeks in ['0', '27', 'x']:
            response = self.get(self.day(6), weeks=weeks)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, weeks)
            self.assertIn('weeks', response.data)

    def test_login_required(self):
        response = self.client.get(reverse('care-consistency'))
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

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
from wger.care.disciplines import Discipline
from wger.care.prescription import (
    PrescriptionStatus,
    start_prescription,
)
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.manager.models import Routine
from wger.nutrition.models import (
    LogItem,
    Meal,
    MealAdherence,
    MealItem,
    NutritionPlan,
    WaterLog,
)


SAO_PAULO = zoneinfo.ZoneInfo('America/Sao_Paulo')


class MyDayTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    The Meu Dia overview with training and food of one calendar day
    """

    day = datetime.date(2026, 3, 10)

    def setUp(self):
        super().setUp()
        self.trainer = self.make_professional('rp_trainer', Discipline.TRAINING)
        self.nutritionist = self.make_professional('rp_nutri', Discipline.NUTRITION)
        self.patient = self.make_user('rp_patient')
        self.patient.userprofile.time_zone = 'America/Sao_Paulo'
        self.patient.userprofile.save()
        self.nutrition_rel = self.follow(self.nutritionist, self.patient, Discipline.NUTRITION)

        self.plan = NutritionPlan(description='Plan', goal_energy=2000, goal_water_ml=2500)
        start_prescription(self.plan, self.nutrition_rel, self.nutritionist)
        self.plan.start = self.day - datetime.timedelta(days=5)
        self.plan.save()
        self.meal = Meal.objects.create(plan=self.plan, name='Lunch', order=1)
        MealItem.objects.create(meal=self.meal, ingredient_id=1, amount=100, order=1)
        self.plan.publish()
        self.url = reverse('care-my-day')

    def get_day(self, day=None):
        self.client.force_authenticate(self.patient)
        return self.client.get(self.url, {'date': (day or self.day).isoformat()})

    def at(self, day, hour, minute=0):
        return datetime.datetime.combine(day, datetime.time(hour, minute), tzinfo=SAO_PAULO)

    def test_nutrition_only_has_no_training(self):
        """Test 2: a nutrition-only patient gets no training section"""
        response = self.get_day()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['training'])
        self.assertIsNone(response.data['physio'])
        self.assertEqual(response.data['nutrition']['plan']['id'], self.plan.pk)
        self.assertEqual(response.data['nutrition']['meals'][0]['name'], 'Lunch')

    def test_training_and_nutrition_together(self):
        """Test 4: training and food of the same day side by side"""
        training_rel = self.follow(self.trainer, self.patient, Discipline.TRAINING)
        routine = Routine(name='Strength', start=self.day - datetime.timedelta(days=1))
        start_prescription(routine, training_rel, self.trainer)
        routine.end = self.day + datetime.timedelta(days=30)
        routine.save()
        routine.days.create(name='Legs', order=1)
        routine.publish()

        data = self.get_day().data
        self.assertTrue(data['combined_view'])
        self.assertEqual(data['training']['routine']['name'], 'Strength')
        self.assertIsNotNone(data['training']['day'])
        self.assertIsNotNone(data['nutrition']['plan'])

    def test_draft_routine_not_shown(self):
        training_rel = self.follow(self.trainer, self.patient, Discipline.TRAINING)
        routine = Routine(name='Draft', start=self.day, end=self.day)
        start_prescription(routine, training_rel, self.trainer)
        routine.save()
        self.assertIsNone(self.get_day().data['training']['routine'])

    def test_day_boundaries_in_patient_timezone(self):
        """Logs and water count on the patient's calendar day, not the UTC one"""
        LogItem.objects.create(
            plan=self.plan,
            ingredient_id=1,
            amount=100,
            datetime=self.at(self.day, 0, 0),
        )
        LogItem.objects.create(
            plan=self.plan,
            ingredient_id=1,
            amount=100,
            datetime=self.at(self.day, 23, 59),
        )
        LogItem.objects.create(
            plan=self.plan,
            ingredient_id=1,
            amount=100,
            datetime=self.at(self.day + datetime.timedelta(days=1), 0, 0),
        )
        WaterLog.objects.create(user=self.patient, amount_ml=300, datetime=self.at(self.day, 22))
        WaterLog.objects.create(
            user=self.patient,
            amount_ml=500,
            datetime=self.at(self.day - datetime.timedelta(days=1), 23, 59),
        )

        single = self.get_day(self.day + datetime.timedelta(days=1)).data['nutrition']['logged']
        both = self.get_day().data['nutrition']
        self.assertAlmostEqual(float(both['logged']['energy']), 2 * float(single['energy']))
        self.assertEqual(both['water'], {'total_ml': 300, 'goal_ml': 2500})
        self.assertEqual(
            float(both['remaining']['energy']),
            2000 - float(both['logged']['energy']),
        )

    def test_superseded_plan_replaced(self):
        draft = self.plan.new_version()
        draft.goal_energy = 1800
        draft.save()
        draft.publish()
        data = self.get_day().data['nutrition']
        self.assertEqual(data['plan']['id'], draft.pk)
        self.assertEqual(data['goals']['energy'], 1800)

    def test_bad_date(self):
        self.client.force_authenticate(self.patient)
        response = self.client.get(self.url, {'date': '10/03/2026'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_adherence_is_one_per_meal_and_day(self):
        """Recording a meal again updates the day's record"""
        self.client.force_authenticate(self.patient)
        url = reverse('meal-adherence-list')
        data = {'meal': str(self.meal.pk), 'date': self.day.isoformat(), 'status': 'partial'}
        self.assertEqual(self.client.post(url, data).status_code, status.HTTP_201_CREATED)
        data['status'] = 'full'
        self.assertEqual(self.client.post(url, data).status_code, status.HTTP_200_OK)
        self.assertEqual(MealAdherence.objects.get(user=self.patient).status, 'full')
        self.assertEqual(self.get_day().data['nutrition']['meals'][0]['adherence'], 'full')

    def test_adherence_needs_own_meal(self):
        other = self.make_user('rp_other')
        self.client.force_authenticate(other)
        response = self.client.post(
            reverse('meal-adherence-list'),
            {'meal': str(self.meal.pk), 'date': self.day.isoformat(), 'status': 'full'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_water_log_is_private(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post(reverse('water-log-list'), {'amount_ml': 250})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(self.nutritionist)
        self.assertEqual(self.client.get(reverse('water-log-list')).data['count'], 0)

    def test_substitutions_only_by_author(self):
        """The nutritionist adds substitutions to drafts, the patient cannot"""
        draft = self.plan.new_version()
        item = MealItem.objects.get(meal__plan=draft)
        data = {'meal_item': str(item.pk), 'ingredient': 2, 'amount': 120, 'criterion': 'energy'}

        self.client.force_authenticate(self.patient)
        url = reverse('substitution-option-list')
        self.assertEqual(self.client.post(url, data).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.nutritionist)
        self.assertEqual(self.client.post(url, data).status_code, status.HTTP_201_CREATED)
        draft.publish()

        self.client.force_authenticate(self.patient)
        info = self.client.get(reverse('nutritionplaninfo-detail', kwargs={'pk': draft.pk}))
        item_data = info.data['meals'][0]['meal_items'][0]
        self.assertEqual(item_data['substitutions'][0]['ingredient'], 2)
        self.assertEqual(draft.status, PrescriptionStatus.PUBLISHED)

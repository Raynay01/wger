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
from django.utils import timezone

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.disciplines import Discipline
from wger.care.models import (
    AccessLog,
    RelationshipStatus,
    SharingScope,
)
from wger.care.prescription import PrescriptionStatus
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.manager.models import Routine
from wger.nutrition.models import (
    LogItem,
    Meal,
    MealItem,
    NutritionPlan,
)
from wger.utils.powersync import REGISTRY


class ModulesTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    The modules a patient sees follow the disciplines of their professionals
    """

    url = '/api/v2/care/modules/'

    def setUp(self):
        super().setUp()
        self.url = reverse('care-modules')
        self.patient = self.make_user('rp_patient')

    def modules(self):
        self.client.force_authenticate(self.patient)
        return self.client.get(self.url).data

    def test_training_only(self):
        """Test 1: a training-only patient sees only training"""
        trainer = self.make_professional('rp_trainer', Discipline.TRAINING)
        self.follow(trainer, self.patient, Discipline.TRAINING)
        data = self.modules()
        self.assertEqual(data['modules'], ['training'])
        self.assertEqual(data['mode'], 'guided')
        self.assertFalse(data['combined_view'])

    def test_nutrition_only(self):
        """Test 2: a nutrition-only patient gets no training module"""
        nutritionist = self.make_professional('rp_nutri', Discipline.NUTRITION)
        self.follow(nutritionist, self.patient, Discipline.NUTRITION)
        self.assertEqual(self.modules()['modules'], ['nutrition'])

    def test_physio_only(self):
        """Test 3: a physio patient sees the physio module"""
        physio = self.make_professional('rp_physio', Discipline.PHYSIO)
        self.follow(physio, self.patient, Discipline.PHYSIO)
        self.assertEqual(self.modules()['modules'], ['physio'])

    def test_training_and_nutrition(self):
        """Test 4: training and nutrition together enable the combined view"""
        trainer = self.make_professional('rp_trainer', Discipline.TRAINING)
        nutritionist = self.make_professional('rp_nutri', Discipline.NUTRITION)
        self.follow(trainer, self.patient, Discipline.TRAINING)
        self.follow(nutritionist, self.patient, Discipline.NUTRITION)
        data = self.modules()
        self.assertEqual(data['modules'], ['training', 'nutrition'])
        self.assertTrue(data['combined_view'])

    def test_ended_and_invited_do_not_count(self):
        trainer = self.make_professional('rp_trainer', Discipline.TRAINING)
        relationship = self.follow(trainer, self.patient, Discipline.TRAINING)
        relationship.status = RelationshipStatus.ENDED
        relationship.save()
        data = self.modules()
        self.assertEqual(data['mode'], 'self')
        self.assertEqual(data['modules'], ['training', 'nutrition'])


class SharingTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Tests 5 and 8: professionals see only what the patient shares with them
    """

    def setUp(self):
        super().setUp()
        self.build_team()
        self.shared_url = reverse('care-relationship-shared', kwargs={'pk': self.nutrition_rel.pk})

    def test_nothing_shared_by_default(self):
        self.client.force_authenticate(self.nutritionist)
        response = self.client.get(self.shared_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['scopes'], [])
        self.assertEqual(response.data['data'], {})

    def test_shared_scopes_and_access_log(self):
        """Only granted scopes are returned and each read is logged"""
        self.grant(self.nutrition_rel, SharingScope.TRAINING_SCHEDULE)
        self.client.force_authenticate(self.nutritionist)
        response = self.client.get(self.shared_url)
        self.assertEqual(response.data['scopes'], [SharingScope.TRAINING_SCHEDULE])
        self.assertIn('routines', response.data['data'][SharingScope.TRAINING_SCHEDULE])
        self.assertNotIn(SharingScope.PHYSIO_PAIN, response.data['data'])
        self.assertTrue(
            AccessLog.objects.filter(
                actor=self.nutritionist,
                patient=self.patient,
                resource=SharingScope.TRAINING_SCHEDULE,
            ).exists()
        )

    def test_revocation_is_immediate(self):
        grant = self.grant(self.nutrition_rel, SharingScope.TRAINING_SCHEDULE)
        grant.revoked_at = timezone.now()
        grant.save()
        self.client.force_authenticate(self.nutritionist)
        self.assertEqual(self.client.get(self.shared_url).data['scopes'], [])

    def test_other_professional_cannot_read(self):
        """The shared data of a relationship is only for its own professional"""
        self.grant(self.nutrition_rel, SharingScope.TRAINING_SCHEDULE)
        self.client.force_authenticate(self.trainer)
        self.assertEqual(self.client.get(self.shared_url).status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.get(self.shared_url).status_code, status.HTTP_403_FORBIDDEN)

    def test_module_records_need_the_discipline(self):
        """A nutritionist reads the food diary, not the training logs"""
        self.client.force_authenticate(self.nutritionist)
        diary = reverse('care-relationship-nutrition-diary', kwargs={'pk': self.nutrition_rel.pk})
        logs = reverse('care-relationship-workout-logs', kwargs={'pk': self.nutrition_rel.pk})
        self.assertEqual(self.client.get(diary).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(logs).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.get(diary, {'date': 'yesterday'}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_notes_need_the_scope(self):
        """Notes of others are visible only with the notes scope, never editable"""
        self.client.force_authenticate(self.trainer)
        response = self.client.post(
            reverse('multidisciplinary-note-list'),
            {'relationship': str(self.training_rel.pk), 'text': 'Knee pain on squats'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        note_id = response.data['id']

        self.client.force_authenticate(self.nutritionist)
        url = reverse('multidisciplinary-note-list')
        self.assertEqual(self.client.get(url).data['count'], 0)

        self.grant(self.nutrition_rel, SharingScope.NOTES)
        self.assertEqual(self.client.get(url).data['count'], 1)
        detail = reverse('multidisciplinary-note-detail', kwargs={'pk': note_id})
        self.assertEqual(
            self.client.patch(detail, {'text': 'changed'}).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.get(url).data['count'], 0)


class PrescriptionTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Tests 6, 7 and 9: each professional writes only their own prescription,
    published versions are frozen and kept
    """

    def setUp(self):
        super().setUp()
        self.build_team()

    def create_plan(self):
        self.client.force_authenticate(self.nutritionist)
        response = self.client.post(
            reverse('nutritionplan-list'),
            {
                'description': 'Hypertrophy',
                'care_relationship': str(self.nutrition_rel.pk),
                'goal_energy': 2500,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        plan = NutritionPlan.objects.get(pk=response.data['id'])
        response = self.client.post(
            reverse('meal-list'),
            {'plan': str(plan.pk), 'name': 'Breakfast', 'time': '07:00'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response = self.client.post(
            reverse('mealitem-list'),
            {'meal': response.data['id'], 'ingredient': 1, 'amount': 100},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return plan

    def publish(self, plan):
        self.client.force_authenticate(self.nutritionist)
        response = self.client.post(reverse('nutritionplan-publish', kwargs={'pk': plan.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        plan.refresh_from_db()

    def test_plan_belongs_to_patient_as_draft(self):
        plan = self.create_plan()
        self.assertEqual(plan.user, self.patient)
        self.assertEqual(plan.author, self.nutritionist)
        self.assertEqual(plan.status, PrescriptionStatus.DRAFT)
        self.assertEqual(plan.organization, self.nutrition_rel.organization)

        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.get(reverse('nutritionplan-list')).data['count'], 0)
        self.assertEqual(self.client.get(reverse('meal-list')).data['count'], 0)

    def test_publish_makes_visible(self):
        plan = self.create_plan()
        self.publish(plan)
        self.assertEqual(plan.status, PrescriptionStatus.PUBLISHED)
        self.assertEqual(len(plan.snapshot_hash), 64)
        self.assertEqual(plan.snapshot['meals'][0]['name'], 'Breakfast')

        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.get(reverse('nutritionplan-list')).data['count'], 1)
        info = self.client.get(reverse('nutritionplaninfo-detail', kwargs={'pk': plan.pk}))
        self.assertEqual(info.data['author'], self.nutritionist.pk)

    def test_patient_cannot_change_prescription(self):
        plan = self.create_plan()
        self.publish(plan)
        meal = plan.meal_set.first()
        self.client.force_authenticate(self.patient)

        response = self.client.patch(
            reverse('nutritionplan-detail', kwargs={'pk': plan.pk}),
            {'goal_energy': 4000},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(
            reverse('meal-detail', kwargs={'pk': meal.pk}),
            {'name': 'Pizza'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.post(reverse('meal-list'), {'plan': str(plan.pk), 'name': 'Extra'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_cannot_change_prescription_via_powersync(self):
        plan = self.create_plan()
        self.publish(plan)
        meal = plan.meal_set.first()
        result = REGISTRY['nutrition_meal'].dispatch(
            'PATCH',
            {'id': str(meal.pk), 'name': 'Pizza'},
            self.patient.pk,
        )
        self.assertEqual(result['error'], 'Forbidden')
        meal.refresh_from_db()
        self.assertEqual(meal.name, 'Breakfast')

        result = REGISTRY['nutrition_meal'].dispatch(
            'PUT',
            {'plan': str(plan.pk), 'name': 'Extra'},
            self.patient.pk,
        )
        self.assertEqual(result['error'], 'Forbidden')

    def test_patient_logs_diary_on_prescription(self):
        """The patient records what they ate against the prescribed plan"""
        plan = self.create_plan()
        self.publish(plan)
        self.client.force_authenticate(self.patient)
        response = self.client.post(
            reverse('nutritiondiary-list'),
            {
                'plan': str(plan.pk),
                'meal': str(plan.meal_set.first().pk),
                'ingredient': 1,
                'amount': 80,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_published_is_frozen_for_author(self):
        plan = self.create_plan()
        self.publish(plan)
        response = self.client.patch(
            reverse('nutritionplan-detail', kwargs={'pk': plan.pk}),
            {'goal_energy': 3000},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_new_version_keeps_history(self):
        """Test 9: a new version copies the content and the old one stays readable"""
        plan = self.create_plan()
        self.publish(plan)
        log = LogItem.objects.create(
            plan=plan,
            meal=plan.meal_set.first(),
            ingredient_id=1,
            amount=100,
        )

        response = self.client.post(reverse('nutritionplan-new-version', kwargs={'pk': plan.pk}))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        draft = NutritionPlan.objects.get(pk=response.data['id'])
        self.assertEqual(draft.version, 2)
        self.assertEqual(draft.lineage_id, plan.lineage_id)
        self.assertEqual(draft.previous_version, plan)
        self.assertEqual(draft.meal_set.count(), 1)
        self.assertEqual(MealItem.objects.filter(meal__plan=draft).count(), 1)

        response = self.client.patch(
            reverse('nutritionplan-detail', kwargs={'pk': draft.pk}),
            {'goal_energy': 2300},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.publish(draft)

        plan.refresh_from_db()
        self.assertEqual(plan.status, PrescriptionStatus.SUPERSEDED)
        self.assertEqual(plan.goal_energy, 2500)
        log.refresh_from_db()
        self.assertEqual(log.plan, plan)

        self.client.force_authenticate(self.patient)
        ids = {p['id'] for p in self.client.get(reverse('nutritionplan-list')).data['results']}
        self.assertEqual(ids, {str(plan.pk), str(draft.pk)})

        self.client.force_authenticate(self.nutritionist)
        response = self.client.delete(reverse('nutritionplan-detail', kwargs={'pk': plan.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_trainer_cannot_change_diet(self):
        """Test 7: the trainer cannot reach the nutrition prescription"""
        plan = self.create_plan()
        self.publish(plan)
        self.client.force_authenticate(self.trainer)
        response = self.client.patch(
            reverse('nutritionplan-detail', kwargs={'pk': plan.pk}),
            {'goal_energy': 1000},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.post(reverse('meal-list'), {'plan': str(plan.pk), 'name': 'x'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            reverse('nutritionplan-list'),
            {'description': 'x', 'care_relationship': str(self.training_rel.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nutritionist_cannot_change_training(self):
        """Test 6: the nutritionist cannot reach or create the training prescription"""
        self.client.force_authenticate(self.trainer)
        today = datetime.date.today()
        response = self.client.post(
            reverse('routine-list'),
            {
                'name': 'Strength',
                'start': today.isoformat(),
                'end': (today + datetime.timedelta(days=30)).isoformat(),
                'care_relationship': str(self.training_rel.pk),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        routine = Routine.objects.get(pk=response.data['id'])
        self.assertEqual(routine.user, self.patient)
        self.assertEqual(routine.author, self.trainer)

        response = self.client.post(
            reverse('day-list'),
            {'routine': routine.pk, 'name': 'Legs', 'order': 1},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response = self.client.post(reverse('routine-publish', kwargs={'pk': routine.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.client.force_authenticate(self.nutritionist)
        response = self.client.patch(
            reverse('routine-detail', kwargs={'pk': routine.pk}),
            {'name': 'Changed'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.post(
            reverse('routine-list'),
            {
                'name': 'Mine',
                'start': today.isoformat(),
                'end': today.isoformat(),
                'care_relationship': str(self.nutrition_rel.pk),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(self.patient)
        response = self.client.patch(
            reverse('routine-detail', kwargs={'pk': routine.pk}),
            {'name': 'Changed'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        result = REGISTRY['manager_routine'].dispatch(
            'PATCH',
            {'id': routine.pk, 'name': 'Changed'},
            self.patient.pk,
        )
        self.assertEqual(result['error'], 'Forbidden')

    def test_routine_new_version_copies_days(self):
        self.client.force_authenticate(self.trainer)
        today = datetime.date.today()
        routine = Routine.objects.create(
            user=self.patient,
            name='Strength',
            start=today,
            end=today + datetime.timedelta(days=30),
            author=self.trainer,
            care_relationship=self.training_rel,
            organization=self.training_rel.organization,
            status=PrescriptionStatus.DRAFT,
            lineage_id='00000000-0000-0000-0000-000000000001',
        )
        routine.days.create(name='Legs', order=1)
        routine.publish()
        response = self.client.post(reverse('routine-new-version', kwargs={'pk': routine.pk}))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        clone = Routine.objects.get(pk=response.data['id'])
        self.assertEqual([d.name for d in clone.days.all()], ['Legs'])
        self.assertEqual(clone.status, PrescriptionStatus.DRAFT)

    def test_ended_relationship_blocks_author(self):
        plan = self.create_plan()
        self.nutrition_rel.status = RelationshipStatus.ENDED
        self.nutrition_rel.save()
        response = self.client.get(reverse('nutritionplan-detail', kwargs={'pk': plan.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_start_is_the_patients_today(self):
        """A plan without start date starts on the calendar day of the patient"""
        # A zone whose calendar day differs from the UTC one right now
        zone = 'Pacific/Pago_Pago' if timezone.now().hour < 11 else 'Pacific/Kiritimati'
        self.patient.userprofile.time_zone = zone
        self.patient.userprofile.save()
        self.client.force_authenticate(self.nutritionist)
        response = self.client.post(
            reverse('nutritionplan-list'),
            {'description': 'Plano', 'care_relationship': str(self.nutrition_rel.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        expected = timezone.localdate(timezone=self.patient.userprofile.zone_info)
        self.assertEqual(response.data['start'], expected.isoformat())

    def test_self_managed_plans_unchanged(self):
        """Users without professionals keep editing their own plans"""
        self.client.force_authenticate(self.patient)
        response = self.client.post(reverse('nutritionplan-list'), {'description': 'Mine'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], PrescriptionStatus.PUBLISHED)
        self.assertIsNone(response.data['author'])
        response = self.client.post(
            reverse('meal-list'),
            {'plan': response.data['id'], 'name': 'Lunch'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Meal.objects.filter(name='Lunch').exists())

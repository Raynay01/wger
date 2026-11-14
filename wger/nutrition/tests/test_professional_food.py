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

# Django
from django.urls import reverse

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.disciplines import Discipline
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.models import Language
from wger.core.tests.base_testcase import BaseTestCase
from wger.nutrition.models import (
    Ingredient,
    IngredientWeightUnit,
    Meal,
    MealItem,
    NutritionPlan,
    Source,
)


class ProfessionalFoodTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Nutritionists add shared foods, corrections keep the base food untouched
    """

    def setUp(self):
        super().setUp()
        Language.objects.get_or_create(short_name='pt', defaults={'full_name': 'Português'})
        self.nutritionist = self.make_professional('rp_nutri', Discipline.NUTRITION)
        self.organization = self.nutritionist.care_memberships.first().organization
        self.url = reverse('professional-food-list')
        self.base = Ingredient.objects.get(pk=1)
        IngredientWeightUnit.objects.create(ingredient=self.base, name='colher de sopa', gram=25)

    def create(self, user=None, **data):
        self.client.force_authenticate(user or self.nutritionist)
        payload = {'organization': str(self.organization.pk), 'name': 'Pão de queijo da casa'}
        payload.update(data)
        return self.client.post(self.url, payload)

    def test_create_new_food(self):
        response = self.create(energy=363, protein=5.1, carbohydrates=34.2, fat=24.6, fiber=0.6)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        food = Ingredient.objects.get(pk=response.data['ingredient'])
        self.assertEqual(food.source_name, Source.PROFESSIONAL.value)
        self.assertEqual(food.license_author, self.organization.name)
        self.assertEqual(food.language.short_name, 'pt')

        # Shared: anyone finds it like any other food
        self.client.force_authenticate(self.make_user('rp_someone'))
        listing = self.client.get(
            reverse('api-ingredient-list'), {'name__search': 'queijo da casa'}
        )
        self.assertEqual([i['id'] for i in listing.data['results']], [food.pk])

    def test_correction_copies_base_and_keeps_it(self):
        """Values not given come from the base food, with its household measures"""
        base_energy = self.base.energy
        response = self.create(
            name='Ingrediente corrigido', based_on=self.base.pk, energy=base_energy + 10
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        food = Ingredient.objects.get(pk=response.data['ingredient'])
        self.assertEqual(food.energy, base_energy + 10)
        self.assertEqual(food.protein, self.base.protein)
        self.assertEqual(
            set(food.ingredientweightunit_set.values_list('name', 'gram')),
            set(self.base.ingredientweightunit_set.values_list('name', 'gram')),
        )
        self.assertIn(
            ('colher de sopa', 25), food.ingredientweightunit_set.values_list('name', 'gram')
        )
        self.base.refresh_from_db()
        self.assertEqual(self.base.energy, base_energy)

    def test_only_nutritionists(self):
        trainer = self.make_professional('rp_trainer', Discipline.TRAINING)
        self.client.force_authenticate(trainer)
        response = self.client.post(
            self.url,
            {
                'organization': str(trainer.care_memberships.first().organization.pk),
                'name': 'X',
                'energy': 100,
                'protein': 1,
                'carbohydrates': 20,
                'fat': 1,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_implausible_values_refused(self):
        response = self.create(energy=10, protein=50, carbohydrates=10, fat=10)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Ingredient.objects.filter(name='Pão de queijo da casa').exists())

    def test_other_organizations_cannot_change(self):
        pk = self.create(energy=363, protein=5.1, carbohydrates=34.2, fat=24.6).data['id']
        other = self.make_professional('rp_other_nutri', Discipline.NUTRITION)
        self.client.force_authenticate(other)
        detail = reverse('professional-food-detail', kwargs={'pk': pk})
        self.assertEqual(
            self.client.patch(detail, {'energy': 1}).status_code, status.HTTP_404_NOT_FOUND
        )
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_404_NOT_FOUND)

    def test_frozen_once_used_in_published_plans(self):
        """Editing is allowed while only drafts use the food, deleting while nothing does"""
        response = self.create(energy=363, protein=5.1, carbohydrates=34.2, fat=24.6)
        pk, ingredient_id = response.data['id'], response.data['ingredient']
        detail = reverse('professional-food-detail', kwargs={'pk': pk})

        patient = self.make_user('rp_patient')
        relationship = self.follow(self.nutritionist, patient, Discipline.NUTRITION)
        plan = NutritionPlan(description='Plano')
        start_prescription(plan, relationship, self.nutritionist)
        plan.save()
        meal = Meal.objects.create(plan=plan, name='Lanche', order=1)
        MealItem.objects.create(meal=meal, ingredient_id=ingredient_id, amount=50, order=1)

        self.client.force_authenticate(self.nutritionist)
        response = self.client.patch(detail, {'energy': 360})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_400_BAD_REQUEST)

        plan.publish()
        self.assertEqual(
            self.client.patch(detail, {'energy': 300}).status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertEqual(Ingredient.objects.get(pk=ingredient_id).energy, 360)

    def test_delete_unused(self):
        response = self.create(energy=363, protein=5.1, carbohydrates=34.2, fat=24.6)
        detail = reverse('professional-food-detail', kwargs={'pk': response.data['id']})
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(pk=response.data['ingredient']).exists())

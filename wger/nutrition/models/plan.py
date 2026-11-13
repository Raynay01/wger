#  This file is part of wger Workout Manager <https://github.com/wger-project>.
#  Copyright (C) 2013 - 2021 wger Team
#
#  wger Workout Manager is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  wger Workout Manager is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Standard Library
import datetime
import logging

# Django
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models
from django.urls import reverse
from django.utils.timezone import make_aware

# wger
from wger.care.disciplines import Discipline
from wger.care.prescription import PrescriptionMixin
from wger.measurements.models import Measurement
from wger.nutrition.consts import ENERGY_FACTOR
from wger.nutrition.helpers import NutritionalValues
from wger.utils.cache import cache_mapper
from wger.utils.uuid import uuid7


logger = logging.getLogger(__name__)


class NutritionPlan(PrescriptionMixin, models.Model):
    """
    A nutrition plan
    """

    # Metaclass to set some other properties
    class Meta:
        ordering = [
            '-start',
        ]

    id = models.UUIDField(
        default=uuid7,
        primary_key=True,
    )

    user = models.ForeignKey(
        User,
        verbose_name='User',
        editable=False,
        on_delete=models.CASCADE,
    )

    creation_date = models.DateField(
        'Creation date',
        auto_now_add=True,
    )

    start = models.DateField(
        verbose_name='Start date',
        blank=True,
        default=datetime.date.today,
    )

    end = models.DateField(
        verbose_name='End date',
        null=True,
        blank=True,
    )

    description = models.CharField(
        max_length=80,
        blank=True,
        verbose_name='Description',
        help_text='A description of the goal of the plan, e.g. "Gain mass" or "Prepare for summer"',
    )

    only_logging = models.BooleanField(
        verbose_name='Only logging',
        default=False,
    )
    """Flag to indicate that the nutritional plan will only used for logging"""

    goal_energy = models.IntegerField(null=True, default=None)

    goal_protein = models.IntegerField(null=True, default=None)

    goal_carbohydrates = models.IntegerField(null=True, default=None)

    goal_fiber = models.IntegerField(null=True, default=None)

    goal_fat = models.IntegerField(null=True, default=None)

    goal_water_ml = models.PositiveIntegerField(null=True, blank=True, default=None)
    """Daily water goal, set individually, there is no default goal"""

    has_goal_calories = models.BooleanField(
        verbose_name='Use daily calories',
        default=False,
        help_text=(
            'Tick the box if you want to mark this '
            'plan as having a goal amount of calories. '
            'You can use the calculator or enter the '
            'value yourself.'
        ),
    )
    """A flag indicating whether the plan has a goal amount of calories"""

    def __str__(self):
        """
        Return a more human-readable representation
        """
        if self.description:
            return self.description
        else:
            return 'Nutrition plan'

    def get_absolute_url(self):
        """
        Returns the canonical URL to view this object
        """
        return reverse('nutrition:plan:view', kwargs={'id': self.id})

    def get_nutritional_values(self):
        """
        Sums the nutritional info of all items in the plan
        """
        nutritional_representation = cache.get(cache_mapper.get_nutrition_cache_by_key(self.pk))
        if not nutritional_representation:
            nutritional_values = NutritionalValues()
            result = {
                'total': NutritionalValues(),
                'percent': {'protein': 0, 'carbohydrates': 0, 'fat': 0},
                'per_kg': {'protein': 0, 'carbohydrates': 0, 'fat': 0},
            }

            # Energy
            for meal in self.meal_set.select_related():
                nutritional_values += meal.get_nutritional_values()
            result['total'] = nutritional_values

            energy = nutritional_values.energy

            # In percent
            if energy:
                result['percent']['protein'] = (
                    nutritional_values.protein * ENERGY_FACTOR['protein'] / energy * 100
                )
                result['percent']['carbohydrates'] = (
                    nutritional_values.carbohydrates * ENERGY_FACTOR['carbohydrates'] / energy * 100
                )
                result['percent']['fat'] = (
                    nutritional_values.fat * ENERGY_FACTOR['fat'] / energy * 100
                )

            # Per body weight
            weight_entry = self.get_closest_weight_entry()
            if weight_entry and weight_entry.value:
                weight_kg = weight_entry.value_in('kg')
                result['per_kg']['protein'] = nutritional_values.protein / weight_kg
                result['per_kg']['carbohydrates'] = nutritional_values.carbohydrates / weight_kg
                result['per_kg']['fat'] = nutritional_values.fat / weight_kg

            nutritional_representation = result
            cache.set(cache_mapper.get_nutrition_cache_by_key(self.pk), nutritional_representation)
        return nutritional_representation

    def get_closest_weight_entry(self):
        """
        Returns the closest weight entry for the nutrition plan.
        Returns None if there are no entries.
        """
        target = self.creation_date
        target_aware = make_aware(datetime.datetime.combine(target, datetime.time()))
        closest_entry_gte = (
            Measurement.body_weight_for(self.user)
            .filter(date__gte=target_aware)
            .order_by('date')
            .first()
        )
        closest_entry_lte = (
            Measurement.body_weight_for(self.user)
            .filter(date__lte=target_aware)
            .order_by('-date')
            .first()
        )
        if closest_entry_gte is None or closest_entry_lte is None:
            return closest_entry_gte or closest_entry_lte
        if abs(closest_entry_gte.date.date() - target) < abs(
            closest_entry_lte.date.date() - target
        ):
            return closest_entry_gte
        else:
            return closest_entry_lte

    def get_owner_object(self):
        """
        Returns the object that has owner information
        """
        return self

    discipline = Discipline.NUTRITION

    def build_snapshot(self) -> dict:
        return {
            'description': self.description,
            'start': self.start,
            'end': self.end,
            'goals': {
                'energy': self.goal_energy,
                'protein': self.goal_protein,
                'carbohydrates': self.goal_carbohydrates,
                'fat': self.goal_fat,
                'fiber': self.goal_fiber,
                'water_ml': self.goal_water_ml,
            },
            'meals': [
                {
                    'name': meal.name,
                    'time': meal.time,
                    'order': meal.order,
                    'items': [
                        {
                            'ingredient': item.ingredient_id,
                            'ingredient_name': item.ingredient.name,
                            'amount': item.amount,
                            'weight_unit': item.weight_unit_id,
                            'order': item.order,
                        }
                        for item in meal.mealitem_set.select_related('ingredient')
                    ],
                }
                for meal in self.meal_set.all()
            ],
        }

    def copy_content_to(self, target) -> None:
        for meal in self.meal_set.all():
            items = list(meal.mealitem_set.all())
            options = {item.pk: list(item.substitutions.all()) for item in items}
            meal.pk = None
            meal._state.adding = True
            meal.plan = target
            meal.save()
            for item in items:
                item_options = options[item.pk]
                item.pk = None
                item._state.adding = True
                item.meal = meal
                item.save()
                for option in item_options:
                    option.pk = None
                    option._state.adding = True
                    option.meal_item = item
                    option.save()

    def get_calories_approximation(self):
        """
        Calculates the deviation from the goal calories and the actual
        amount of the current plan
        """

        goal_calories = self.user.userprofile.calories
        actual_calories = self.get_nutritional_values()['total']['energy']

        # Within 3%
        if (actual_calories < goal_calories * 1.03) and (actual_calories > goal_calories * 0.97):
            return 1
        # within 7%
        elif (actual_calories < goal_calories * 1.07) and (actual_calories > goal_calories * 0.93):
            return 2
        # within 10%
        elif (actual_calories < goal_calories * 1.10) and (actual_calories > goal_calories * 0.9):
            return 3
        # even more
        else:
            return 4

    def get_log_entries(self, date=None):
        """
        Convenience function that returns the log entries for a given date
        """
        if not date:
            date = datetime.date.today()

        return self.logitem_set.filter(datetime__date=date).select_related()

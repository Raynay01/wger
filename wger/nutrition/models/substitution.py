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
from decimal import Decimal

# Django
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _

# wger
from wger.utils.uuid import uuid7

# Local
from .ingredient import Ingredient
from .ingredient_weight_unit import IngredientWeightUnit
from .meal_item import MealItem


class SubstitutionCriterion(models.TextChoices):
    ENERGY = 'energy', _('Same energy')
    MACRONUTRIENT = 'macronutrient', _('Same main macronutrient')
    MANUAL = 'manual', _('Defined by the nutritionist')
    PREFERENCE = 'preference', _('Preference')
    AVAILABILITY = 'availability', _('Availability')


class SubstitutionOption(models.Model):
    """
    An alternative to a prescribed meal item, approved by whoever writes the plan
    """

    class Meta:
        ordering = ['order']

    id = models.UUIDField(default=uuid7, primary_key=True)

    meal_item = models.ForeignKey(
        MealItem,
        on_delete=models.CASCADE,
        related_name='substitutions',
    )

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='+')

    weight_unit = models.ForeignKey(
        IngredientWeightUnit,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='+',
    )

    amount = models.DecimalField(
        decimal_places=2,
        max_digits=6,
        validators=[MinValueValidator(Decimal(1)), MaxValueValidator(Decimal(1000))],
    )

    criterion = models.CharField(
        max_length=15,
        choices=SubstitutionCriterion.choices,
        default=SubstitutionCriterion.MANUAL,
    )

    note = models.CharField(max_length=200, blank=True)

    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.amount} of ingredient {self.ingredient_id}'

    def get_owner_object(self):
        return self.meal_item.meal.plan

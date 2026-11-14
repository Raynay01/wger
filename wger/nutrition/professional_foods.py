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

"""
Foods professionals add to the shared food database
"""

# Standard Library
from decimal import Decimal

# Django
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache

# wger
from wger.care.prescription import PrescriptionStatus
from wger.core.models import Language
from wger.nutrition.dataclasses import IngredientData
from wger.nutrition.models import (
    Ingredient,
    IngredientWeightUnit,
    LogItem,
    MealItem,
    ProfessionalFood,
    Source,
    SubstitutionOption,
)
from wger.utils.cache import cache_mapper
from wger.utils.constants import CC_BY_SA_4_LICENSE_ID


VALUE_FIELDS = ('energy', 'protein', 'carbohydrates', 'fat', 'fiber', 'sodium')


def in_use(ingredient: Ingredient) -> bool:
    """
    Whether changing the food would change history: a diary entry or a
    prescription that is not a draft anymore (self-managed plans count too)
    """
    return (
        LogItem.objects.filter(ingredient=ingredient).exists()
        or MealItem.objects.filter(ingredient=ingredient)
        .exclude(meal__plan__status=PrescriptionStatus.DRAFT)
        .exists()
        or SubstitutionOption.objects.filter(ingredient=ingredient)
        .exclude(meal_item__meal__plan__status=PrescriptionStatus.DRAFT)
        .exists()
    )


def referenced(ingredient: Ingredient) -> bool:
    """Whether any plan, draft or not, or diary uses the food"""
    return (
        LogItem.objects.filter(ingredient=ingredient).exists()
        or MealItem.objects.filter(ingredient=ingredient).exists()
        or SubstitutionOption.objects.filter(ingredient=ingredient).exists()
    )


def checked_values(name: str, values: dict) -> dict:
    """
    The values after the checks the importers use, energy plausibility included
    since these are typed in. Raises ValueError with the reason.
    """

    def number(field):
        value = values.get(field)
        return None if value is None else float(value)

    data = IngredientData(
        name=name,
        remote_id='',
        language_id=0,
        energy=number('energy'),
        protein=number('protein'),
        carbohydrates=number('carbohydrates'),
        carbohydrates_sugar=None,
        fat=number('fat'),
        fat_saturated=None,
        fiber=number('fiber'),
        sodium=number('sodium'),
        code=None,
        source_name='',
        source_url='',
        common_name=name,
        brand='',
        license_id=0,
        license_author='',
        license_title=name,
        license_object_url='',
    )
    data.sanity_checks(check_energy=True)
    return {
        field: None if values.get(field) is None else Decimal(str(values[field]))
        for field in VALUE_FIELDS
    }


def create_food(
    *,
    organization,
    author: User,
    name: str,
    brand: str,
    values: dict,
    based_on: Ingredient | None,
) -> ProfessionalFood:
    """Creates the shared ingredient and its record; a correction keeps the base untouched"""
    if based_on is not None:
        for field in VALUE_FIELDS:
            if values.get(field) is None:
                values[field] = getattr(based_on, field)
    for field in ('energy', 'protein', 'carbohydrates', 'fat'):
        if values.get(field) is None:
            raise ValueError(f'Value for {field} is missing')
    values = checked_values(name, values)

    ingredient = Ingredient.objects.create(
        name=name,
        common_name=name,
        brand=brand,
        language=Language.objects.get(short_name='pt'),
        energy=int(Decimal(values['energy'])),
        protein=values['protein'],
        carbohydrates=values['carbohydrates'],
        fat=values['fat'],
        fiber=values['fiber'],
        sodium=values['sodium'],
        category=based_on.category if based_on else None,
        source_name=Source.PROFESSIONAL.value,
        source_url=settings.WEB_APP_URL,
        license_id=CC_BY_SA_4_LICENSE_ID,
        license_author=organization.name,
        license_title=name,
        license_derivative_source_url=based_on.source_url if based_on else '',
    )
    if based_on is not None:
        for unit in based_on.ingredientweightunit_set.all():
            IngredientWeightUnit.objects.create(
                ingredient=ingredient, name=unit.name, gram=unit.gram
            )

    return ProfessionalFood.objects.create(
        ingredient=ingredient,
        organization=organization,
        author=author,
        based_on=based_on,
    )


def update_food(food: ProfessionalFood, name: str | None, brand: str | None, values: dict):
    ingredient = food.ingredient
    current = {field: getattr(ingredient, field) for field in VALUE_FIELDS}
    current.update({k: v for k, v in values.items() if k in VALUE_FIELDS})
    name = name or ingredient.name
    current = checked_values(name, current)
    for field, value in current.items():
        setattr(ingredient, field, int(Decimal(value)) if field == 'energy' else value)
    ingredient.name = name
    ingredient.common_name = name
    ingredient.license_title = name
    if brand is not None:
        ingredient.brand = brand
    ingredient.save()
    food.save()

    # Drafts using the food show the new values
    plans = MealItem.objects.filter(ingredient=ingredient).values_list('meal__plan_id', flat=True)
    for plan_id in set(plans):
        cache.delete(cache_mapper.get_nutrition_cache_by_key(plan_id))

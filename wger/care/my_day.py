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
The "Meu Dia" overview: the patient's training and food for one calendar day
"""

# Standard Library
import datetime

# Django
from django.contrib.auth.models import User
from django.db.models import Q, Sum

# wger
from wger.care import policy
from wger.care.disciplines import Discipline
from wger.care.prescription import PrescriptionStatus


def day_bounds(user: User, day: datetime.date) -> tuple[datetime.datetime, datetime.datetime]:
    """Start and end of a calendar day in the user's timezone"""
    zone = user.userprofile.zone_info
    start = datetime.datetime.combine(day, datetime.time.min, tzinfo=zone)
    return start, start + datetime.timedelta(days=1)


def _current(queryset, day: datetime.date):
    """The active, most recent prescription of a queryset for a day"""
    return (
        queryset.filter(start__lte=day)
        .filter(Q(end__isnull=True) | Q(end__gte=day))
        .filter(status=PrescriptionStatus.PUBLISHED)
        .order_by('-start')
        .first()
    )


def _values(values) -> dict | None:
    if values is None:
        return None
    return {
        'energy': values.energy,
        'protein': values.protein,
        'carbohydrates': values.carbohydrates,
        'fat': values.fat,
        'fiber': values.fiber,
    }


def training_section(user: User, day: datetime.date) -> dict | None:
    # wger
    from wger.manager.api.serializers import WorkoutDayDataDisplayModeSerializer
    from wger.manager.models import (
        Routine,
        WorkoutSession,
    )

    routine = _current(Routine.objects.filter(user=user, is_template=False), day)
    if routine is None:
        return {'routine': None, 'day': None, 'session_done': False}

    entry = next((d for d in routine.date_sequence if d.date == day), None)
    start, end = day_bounds(user, day)
    return {
        'routine': {'id': routine.pk, 'name': routine.name, 'author': routine.author_id},
        'day': WorkoutDayDataDisplayModeSerializer(entry).data if entry else None,
        'session_done': WorkoutSession.objects.filter(
            user=user,
            routine=routine,
            datetime_start__gte=start,
            datetime_start__lt=end,
        ).exists(),
    }


def nutrition_section(user: User, day: datetime.date) -> dict:
    # wger
    from wger.nutrition.models import (
        LogItem,
        MealAdherence,
        NutritionPlan,
        WaterLog,
    )

    start, end = day_bounds(user, day)
    plan = _current(NutritionPlan.objects.filter(user=user), day)

    logged = None
    for item in LogItem.objects.filter(
        plan__user=user,
        datetime__gte=start,
        datetime__lt=end,
    ).select_related('ingredient', 'weight_unit'):
        values = item.get_nutritional_values()
        logged = values if logged is None else logged + values

    water = (
        WaterLog.objects.filter(user=user, datetime__gte=start, datetime__lt=end).aggregate(
            total=Sum('amount_ml')
        )['total']
        or 0
    )

    out = {
        'plan': None,
        'goals': None,
        'meals': [],
        'logged': _values(logged),
        'remaining': None,
        'water': {'total_ml': water, 'goal_ml': None},
    }
    if plan is None:
        return out

    adherence = dict(
        MealAdherence.objects.filter(user=user, date=day, meal__plan=plan).values_list(
            'meal_id',
            'status',
        )
    )
    goals = {
        'energy': plan.goal_energy,
        'protein': plan.goal_protein,
        'carbohydrates': plan.goal_carbohydrates,
        'fat': plan.goal_fat,
        'fiber': plan.goal_fiber,
    }
    logged_values = out['logged'] or {}
    out.update(
        {
            'plan': {'id': plan.pk, 'description': plan.description, 'author': plan.author_id},
            'goals': goals,
            'remaining': {
                key: goal - (logged_values.get(key) or 0)
                for key, goal in goals.items()
                if goal is not None
            },
            'meals': [
                {
                    'id': meal.pk,
                    'name': meal.name,
                    'time': meal.time,
                    'instructions': meal.instructions,
                    'planned': _values(meal.get_nutritional_values()),
                    'items': [
                        {
                            'ingredient': item.ingredient_id,
                            'name': item.ingredient.name,
                            'amount': item.amount,
                            'weight_unit': item.weight_unit_id,
                            'unit_name': item.weight_unit.name if item.weight_unit else None,
                            'grams': item.amount * item.weight_unit.gram
                            if item.weight_unit
                            else item.amount,
                            'instructions': item.instructions,
                            'substitutions': item.substitutions.count(),
                        }
                        for item in meal.mealitem_set.select_related('ingredient', 'weight_unit')
                    ],
                    'adherence': adherence.get(meal.pk),
                }
                for meal in plan.meal_set.all()
            ],
        }
    )
    out['water']['goal_ml'] = plan.goal_water_ml
    return out


def physio_section(user: User, day: datetime.date) -> dict:
    try:
        # wger
        from wger.physio.my_day import physio_day
    except ImportError:
        return {}
    return physio_day(user, day)


def my_day(user: User, day: datetime.date) -> dict:
    """
    The sections of the modules the user has, never an empty one they don't have
    """
    modules = policy.patient_modules(user)
    out = {'date': day, **modules}
    builders = {
        Discipline.TRAINING: training_section,
        Discipline.NUTRITION: nutrition_section,
        Discipline.PHYSIO: physio_section,
    }
    for discipline, builder in builders.items():
        out[discipline.value] = builder(user, day) if discipline in modules['modules'] else None
    return out

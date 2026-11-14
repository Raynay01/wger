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
Consistency calendar of a patient: what was recorded each day, per area

Only records count, never amounts: no day is better for eating less or for
weighing less. A prescribed rest day without records does not break the
streak, and neither does today while it lasts.
"""

# Standard Library
import datetime
from collections import defaultdict

# Django
from django.contrib.auth.models import User
from django.utils import timezone

# wger
from wger.care import policy
from wger.care.agenda import (
    _active,
    _covers,
)
from wger.care.disciplines import Discipline
from wger.care.my_day import day_bounds


MAX_WEEKS = 26


class TrainingStatus:
    DONE = 'done'
    MISSED = 'missed'
    PLANNED = 'planned'
    REST = 'rest'


def local_today(user: User) -> datetime.date:
    return timezone.localdate(timezone=user.userprofile.zone_info)


def _local_days(user: User, moments) -> set:
    zone = user.userprofile.zone_info
    return {moment.astimezone(zone).date() for moment in moments}


def _training(user: User, start: datetime.date, end: datetime.date) -> tuple[dict, set]:
    """Prescribed training or rest per day, and the days with training recorded"""
    # wger
    from wger.manager.models import (
        Routine,
        WorkoutLog,
        WorkoutSession,
    )

    planned = {}
    for routine in _active(Routine.objects.filter(user=user, is_template=False), start, end):
        for entry in routine.date_sequence:
            if start <= entry.date <= end and entry.day is not None:
                planned[entry.date] = entry.day.is_rest

    range_start, _ = day_bounds(user, start)
    _, range_end = day_bounds(user, end)
    done = _local_days(
        user,
        WorkoutSession.objects.filter(
            user=user,
            datetime_start__gte=range_start,
            datetime_start__lt=range_end,
        ).values_list('datetime_start', flat=True),
    ) | _local_days(
        user,
        WorkoutLog.objects.filter(
            user=user,
            date__gte=range_start,
            date__lt=range_end,
        ).values_list('date', flat=True),
    )
    return planned, done


def _nutrition(user: User, start: datetime.date, end: datetime.date) -> tuple[list, set, dict]:
    """Active plans, days with food recorded and water per day"""
    # wger
    from wger.nutrition.models import (
        LogItem,
        MealAdherence,
        NutritionPlan,
        WaterLog,
    )

    plans = list(_active(NutritionPlan.objects.filter(user=user), start, end))
    range_start, _ = day_bounds(user, start)
    _, range_end = day_bounds(user, end)
    logged = _local_days(
        user,
        LogItem.objects.filter(
            plan__user=user,
            datetime__gte=range_start,
            datetime__lt=range_end,
        ).values_list('datetime', flat=True),
    ) | set(
        MealAdherence.objects.filter(user=user, date__gte=start, date__lte=end).values_list(
            'date', flat=True
        )
    )
    zone = user.userprofile.zone_info
    water = defaultdict(int)
    for moment, amount in WaterLog.objects.filter(
        user=user,
        datetime__gte=range_start,
        datetime__lt=range_end,
    ).values_list('datetime', 'amount_ml'):
        water[moment.astimezone(zone).date()] += amount
    return plans, logged, water


def _physio(user: User, start: datetime.date, end: datetime.date) -> tuple[list, set]:
    # wger
    from wger.physio.models import (
        ExerciseRecord,
        PhysioProtocol,
    )

    protocols = list(_active(PhysioProtocol.objects.filter(user=user), start, end))
    range_start, _ = day_bounds(user, start)
    _, range_end = day_bounds(user, end)
    done = _local_days(
        user,
        ExerciseRecord.objects.filter(
            user=user,
            datetime__gte=range_start,
            datetime__lt=range_end,
        ).values_list('datetime', flat=True),
    )
    return protocols, done


def _training_status(day, today, planned: dict, done: set) -> str | None:
    if day in done:
        return TrainingStatus.DONE
    if day not in planned:
        return None
    if planned[day]:
        return TrainingStatus.REST
    return TrainingStatus.PLANNED if day >= today else TrainingStatus.MISSED


def _streak(days: list, today: datetime.date) -> int:
    """Consecutive days with a record up to today; rest days and today bridge"""
    streak = 0
    for item in reversed(days):
        if item['date'] > today:
            continue
        if item['recorded']:
            streak += 1
        elif item['date'] == today or item['training'] == TrainingStatus.REST:
            continue
        else:
            break
    return streak


def consistency(user: User, end: datetime.date, weeks: int) -> dict:
    """
    Records per day and per week (Monday to Sunday) for the weeks up to the one
    of end; the streak only looks at these weeks
    """
    modules = policy.patient_modules(user)['modules']
    today = local_today(user)
    last = end + datetime.timedelta(days=6 - end.weekday())
    start = last - datetime.timedelta(weeks=weeks) + datetime.timedelta(days=1)

    planned, trained = (
        _training(user, start, last) if Discipline.TRAINING in modules else ({}, set())
    )
    plans, ate, water = (
        _nutrition(user, start, last) if Discipline.NUTRITION in modules else ([], set(), {})
    )
    protocols, rehab = _physio(user, start, last) if Discipline.PHYSIO in modules else ([], set())

    days = []
    day = start
    while day <= last:
        plan = next((p for p in reversed(plans) if _covers(p, day)), None)
        goal = plan.goal_water_ml if plan else None
        item = {
            'date': day,
            'training': _training_status(day, today, planned, trained),
            'meals': (day in ate) if plan else None,
            'water_ml': water.get(day, 0) if plan else None,
            'water_goal': (water.get(day, 0) >= goal) if goal else None,
            'physio': (day in rehab) if any(_covers(p, day) for p in protocols) else None,
        }
        item['recorded'] = bool(
            item['training'] == TrainingStatus.DONE
            or item['meals']
            or item['water_ml']
            or item['physio']
        )
        days.append(item)
        day += datetime.timedelta(days=1)

    summaries = []
    for index in range(weeks):
        week = days[index * 7 : index * 7 + 7]
        summaries.append(
            {
                'start': week[0]['date'],
                'end': week[-1]['date'],
                'training_done': sum(d['training'] == TrainingStatus.DONE for d in week),
                'training_planned': sum(planned.get(d['date']) is False for d in week),
                'meals_days': sum(bool(d['meals']) for d in week),
                'water_goal_days': sum(bool(d['water_goal']) for d in week),
                'physio_days': sum(bool(d['physio']) for d in week),
                'recorded_days': sum(d['recorded'] for d in week),
            }
        )

    return {
        'modules': modules,
        'today': today,
        'streak': _streak(days, today),
        'weeks': summaries,
        'days': days,
    }

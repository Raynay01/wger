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
Planned versus done training per week of a periodization

Planned comes from the routine of each block as prescribed (without the
patient's history), done from all training logs of the patient in that week,
whichever routine they belong to.
"""

# Standard Library
import datetime
from collections import defaultdict
from decimal import Decimal

# wger
from wger.care.my_day import day_bounds
from wger.manager.consts import (
    REP_UNIT_REPETITIONS,
    WEIGHT_UNIT_KG,
    WEIGHT_UNIT_LB,
)
from wger.manager.models import (
    TrainingPlan,
    WorkoutLog,
    WorkoutSession,
)


LB_IN_KG = Decimal('0.45359237')


def _load(repetitions, repetitions_unit, weight, weight_unit) -> Decimal:
    """Repetitions times weight in kg; zero for time, distance or other units"""
    if repetitions is None or weight is None or repetitions_unit != REP_UNIT_REPETITIONS:
        return Decimal(0)
    if weight_unit == WEIGHT_UNIT_KG:
        return Decimal(repetitions) * Decimal(weight)
    if weight_unit == WEIGHT_UNIT_LB:
        return Decimal(repetitions) * Decimal(weight) * LB_IN_KG
    return Decimal(0)


def _planned(routine, start: datetime.date, end: datetime.date) -> dict:
    """Sessions, sets and load per day of the routine as prescribed"""
    out = {}
    if routine is None:
        return out
    for entry in routine.get_date_sequence(with_history=False):
        if not start <= entry.date <= end or entry.day is None or entry.day.is_rest:
            continue
        sets = 0
        load = Decimal(0)
        for slot in entry.slots_display_mode:
            for config in slot.sets:
                count = config.sets or 0
                sets += count
                load += count * _load(
                    config.repetitions,
                    config.repetitions_unit,
                    config.weight,
                    config.weight_unit,
                )
        out[entry.date] = (sets, load)
    return out


def _done(user, start: datetime.date, end: datetime.date) -> dict:
    """Sets, load, RIR and RPE per calendar day of the patient"""
    zone = user.userprofile.zone_info
    range_start, _ = day_bounds(user, start)
    _, range_end = day_bounds(user, end)
    days = defaultdict(lambda: {'sets': 0, 'load': Decimal(0), 'rir': [], 'rpe': []})
    logs = WorkoutLog.objects.filter(user=user, date__gte=range_start, date__lt=range_end)
    for log in logs.only(
        'date', 'repetitions', 'repetitions_unit', 'weight', 'weight_unit', 'rir', 'rpe'
    ):
        day = days[log.date.astimezone(zone).date()]
        day['sets'] += 1
        day['load'] += _load(
            log.repetitions, log.repetitions_unit_id, log.weight, log.weight_unit_id
        )
        if log.rir is not None:
            day['rir'].append(log.rir)
        if log.rpe is not None:
            day['rpe'].append(log.rpe)
    # A session without logs (e.g. only the impression) still counts as trained
    sessions = WorkoutSession.objects.filter(
        user=user,
        datetime_start__gte=range_start,
        datetime_start__lt=range_end,
    )
    for moment in sessions.values_list('datetime_start', flat=True):
        days[moment.astimezone(zone).date()]
    return days


def _average(values: list) -> Decimal | None:
    if not values:
        return None
    return (sum(values) / len(values)).quantize(Decimal('0.1'))


def _summary(start, end, planned: dict, done: dict) -> dict:
    planned_days = [v for d, v in planned.items() if start <= d <= end]
    done_days = [v for d, v in done.items() if start <= d <= end]
    rir = [x for v in done_days for x in v['rir']]
    rpe = [x for v in done_days for x in v['rpe']]
    return {
        'start': start,
        'end': end,
        'planned_sessions': len(planned_days),
        'done_sessions': len(done_days),
        'planned_sets': sum(sets for sets, _ in planned_days),
        'done_sets': sum(v['sets'] for v in done_days),
        'planned_load': round(sum((load for _, load in planned_days), Decimal(0))),
        'done_load': round(sum((v['load'] for v in done_days), Decimal(0))),
        'average_rir': _average(rir),
        'average_rpe': _average(rpe),
    }


def plan_progress(plan: TrainingPlan) -> dict:
    """Planned and done per block and per week of the block; load in kg"""
    schedule = plan.schedule()
    if not schedule:
        return {'start': plan.start, 'end': None, 'blocks': []}
    done = _done(plan.user, schedule[0].start, schedule[-1].end)

    blocks = []
    for scheduled in schedule:
        block = scheduled.block
        planned = _planned(block.current_routine(), scheduled.start, scheduled.end)
        weeks = []
        for index in range(block.weeks):
            week_start = scheduled.start + datetime.timedelta(weeks=index)
            week_end = week_start + datetime.timedelta(days=6)
            weeks.append({'week': index + 1, **_summary(week_start, week_end, planned, done)})
        blocks.append(
            {
                'id': block.pk,
                'name': block.name,
                'focus': block.focus,
                'intensity': block.intensity,
                'volume': block.volume,
                **_summary(scheduled.start, scheduled.end, planned, done),
                'weeks': weeks,
            }
        )
    return {'start': schedule[0].start, 'end': schedule[-1].end, 'blocks': blocks}

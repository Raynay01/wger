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
Read-only summaries of a patient's data, one per sharing scope

Each builder returns facts only (counts, dates, goals), never the full record
of another professional.
"""

# Standard Library
import datetime
from collections import Counter

# Django
from django.contrib.auth.models import User
from django.db.models import Avg
from django.utils import timezone

# wger
from wger.care.models import (
    CareRelationship,
    MultidisciplinaryNote,
    SharingScope,
)
from wger.care.prescription import PrescriptionStatus


PERIOD_DAYS = 28


def _period_start() -> datetime.datetime:
    return timezone.now() - datetime.timedelta(days=PERIOD_DAYS)


def _current_routines(patient: User):
    # wger
    from wger.manager.models import Routine

    today = timezone.localdate(timezone=patient.userprofile.zone_info)
    return (
        Routine.objects.filter(user=patient, start__lte=today, end__gte=today, is_template=False)
        .exclude(author__isnull=False, status=PrescriptionStatus.DRAFT)
        .exclude(status__in=[PrescriptionStatus.SUPERSEDED, PrescriptionStatus.ARCHIVED])
    )


def training_schedule(patient: User, relationship: CareRelationship) -> dict:
    # wger
    from wger.manager.models import WorkoutSession

    zone = patient.userprofile.zone_info
    routines = []
    for routine in _current_routines(patient):
        days = list(routine.days.all())
        routines.append(
            {
                'name': routine.name,
                'start': routine.start,
                'end': routine.end,
                'training_days_per_cycle': len([d for d in days if not d.is_rest]),
                'cycle_length': len(days),
                'days': [{'name': d.name, 'is_rest': d.is_rest} for d in days],
            }
        )

    sessions = WorkoutSession.objects.filter(
        user=patient,
        datetime_start__gte=_period_start(),
    )
    hours = Counter(timezone.localtime(s.datetime_start, zone).hour for s in sessions)
    weekdays = Counter(timezone.localtime(s.datetime_start, zone).isoweekday() for s in sessions)
    return {
        'routines': routines,
        'usual_start_hours': [h for h, _ in hours.most_common(3)],
        'usual_weekdays': sorted(d for d, _ in weekdays.most_common(7)),
        'expected_duration_minutes': patient.userprofile.workout_duration,
    }


def training_adherence(patient: User, relationship: CareRelationship) -> dict:
    # wger
    from wger.manager.models import (
        WorkoutLog,
        WorkoutSession,
    )

    start = _period_start()
    sessions = WorkoutSession.objects.filter(user=patient, datetime_start__gte=start)
    logs = WorkoutLog.objects.filter(user=patient, date__gte=start)
    return {
        'period_days': PERIOD_DAYS,
        'sessions': sessions.count(),
        'sets_logged': logs.count(),
        'average_rir': logs.exclude(rir__isnull=True).aggregate(v=Avg('rir'))['v'],
    }


def _current_plan(patient: User):
    # wger
    from wger.nutrition.models import NutritionPlan

    return (
        NutritionPlan.objects.filter(user=patient, status=PrescriptionStatus.PUBLISHED)
        .order_by('-start')
        .first()
    )


def nutrition_goals(patient: User, relationship: CareRelationship) -> dict:
    plan = _current_plan(patient)
    if plan is None:
        return {'plan': None}
    return {
        'plan': plan.description,
        'goal_energy': plan.goal_energy,
        'goal_protein': plan.goal_protein,
        'goal_carbohydrates': plan.goal_carbohydrates,
        'goal_fat': plan.goal_fat,
        'goal_fiber': plan.goal_fiber,
        'goal_water_ml': getattr(plan, 'goal_water_ml', None),
        'meals': [{'name': m.name, 'time': m.time} for m in plan.meal_set.all()],
    }


def nutrition_adherence(patient: User, relationship: CareRelationship) -> dict:
    # wger
    from wger.nutrition.models import LogItem

    zone = patient.userprofile.zone_info
    items = LogItem.objects.filter(plan__user=patient, datetime__gte=_period_start())
    days = {timezone.localtime(i.datetime, zone).date() for i in items}
    out = {'period_days': PERIOD_DAYS, 'days_with_records': len(days)}

    try:
        # wger
        from wger.nutrition.models import MealAdherence

        adherence = Counter(
            MealAdherence.objects.filter(
                user=patient,
                date__gte=timezone.localdate(_period_start(), timezone=zone),
            ).values_list('status', flat=True)
        )
        out['meals'] = dict(adherence)
    except ImportError:
        pass
    return out


def body_measurements(patient: User, relationship: CareRelationship) -> dict:
    # wger
    from wger.measurements.models import Measurement
    from wger.measurements.models.category import MetricType

    entries = Measurement.objects.filter(
        category__user=patient,
        category__metric_type=MetricType.BODY_WEIGHT,
    ).order_by('-date')[:10]
    return {
        'body_weight': [{'date': e.date, 'value': e.value} for e in entries],
    }


def physio_pain(patient: User, relationship: CareRelationship) -> dict:
    try:
        # wger
        from wger.physio.models import PainRecord
    except ImportError:
        return {}

    records = PainRecord.objects.filter(user=patient, datetime__gte=_period_start())
    return {
        'period_days': PERIOD_DAYS,
        'records': records.count(),
        'average': records.aggregate(v=Avg('value'))['v'],
        'latest': [{'datetime': r.datetime, 'value': r.value} for r in records[:5]],
    }


def notes(patient: User, relationship: CareRelationship) -> list:
    entries = (
        MultidisciplinaryNote.objects.filter(relationship__patient=patient)
        .exclude(relationship=relationship)
        .select_related('relationship__professional')
    )
    return [
        {
            'author': n.relationship.professional.get_full_name()
            or n.relationship.professional.username,
            'discipline': n.relationship.discipline,
            'category': n.category,
            'text': n.text,
            'created': n.created,
        }
        for n in entries
    ]


BUILDERS = {
    SharingScope.TRAINING_SCHEDULE: training_schedule,
    SharingScope.TRAINING_ADHERENCE: training_adherence,
    SharingScope.NUTRITION_GOALS: nutrition_goals,
    SharingScope.NUTRITION_ADHERENCE: nutrition_adherence,
    SharingScope.PHYSIO_PAIN: physio_pain,
    SharingScope.BODY_MEASUREMENTS: body_measurements,
    SharingScope.NOTES: notes,
}

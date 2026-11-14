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
The integrated calendar of a patient: training, food, physio and appointments per day
"""

# Standard Library
import datetime

# Django
from django.contrib.auth.models import User
from django.db.models import Q

# wger
from wger.care import policy
from wger.care.disciplines import Discipline
from wger.care.models import (
    Appointment,
    AppointmentStatus,
)
from wger.care.my_day import day_bounds
from wger.care.prescription import PrescriptionStatus


MAX_DAYS = 62


def _active(queryset, start: datetime.date, end: datetime.date):
    """Published prescriptions overlapping the range"""
    return (
        queryset.filter(status=PrescriptionStatus.PUBLISHED, start__lte=end)
        .filter(Q(end__isnull=True) | Q(end__gte=start))
        .order_by('start')
    )


def _covers(prescription, day: datetime.date) -> bool:
    return prescription.start <= day and (prescription.end is None or prescription.end >= day)


def appointment_data(appointment: Appointment) -> dict:
    relationship = appointment.relationship
    professional = relationship.professional
    patient = relationship.patient
    return {
        'id': appointment.pk,
        'kind': appointment.kind,
        'status': appointment.status,
        'start': appointment.start,
        'duration_minutes': appointment.duration_minutes,
        'location': appointment.location,
        'notes': appointment.notes,
        'discipline': relationship.discipline,
        'relationship': relationship.pk,
        'professional': professional.get_full_name() or professional.username,
        'patient': (patient.get_full_name() or patient.username) if patient else None,
    }


def patient_calendar(user: User, start: datetime.date, end: datetime.date) -> dict:
    # wger
    from wger.manager.models import (
        Routine,
        TrainingPlan,
    )
    from wger.nutrition.models import NutritionPlan
    from wger.physio.models import PhysioProtocol

    modules = policy.patient_modules(user)['modules']
    zone = user.userprofile.zone_info

    training = {}
    if Discipline.TRAINING in modules:
        for routine in _active(Routine.objects.filter(user=user, is_template=False), start, end):
            for entry in routine.date_sequence:
                if start <= entry.date <= end and entry.day is not None:
                    training[entry.date] = {
                        'routine': routine.name,
                        'day': entry.day.name,
                        'is_rest': entry.day.is_rest,
                    }

    phases = {}
    if Discipline.TRAINING in modules:
        periodizations = TrainingPlan.objects.filter(
            user=user,
            status=PrescriptionStatus.PUBLISHED,
            start__lte=end,
        ).prefetch_related('blocks')
        for periodization in periodizations.order_by('start'):
            for scheduled in periodization.schedule():
                day = max(scheduled.start, start)
                while day <= min(scheduled.end, end):
                    phases[day] = {
                        'plan': periodization.name,
                        'block': scheduled.block.name,
                        'focus': scheduled.block.focus,
                        'week': (day - scheduled.start).days // 7 + 1,
                        'weeks': scheduled.block.weeks,
                    }
                    day += datetime.timedelta(days=1)

    plans = (
        list(_active(NutritionPlan.objects.filter(user=user), start, end))
        if Discipline.NUTRITION in modules
        else []
    )
    protocols = (
        list(_active(PhysioProtocol.objects.filter(user=user), start, end))
        if Discipline.PHYSIO in modules
        else []
    )

    range_start, _ = day_bounds(user, start)
    _, range_end = day_bounds(user, end)
    appointments = (
        Appointment.objects.filter(
            relationship__patient=user,
            start__gte=range_start,
            start__lt=range_end,
        )
        .exclude(status=AppointmentStatus.CANCELLED)
        .select_related('relationship__professional', 'relationship__patient')
    )
    by_day = {}
    for appointment in appointments:
        day = appointment.start.astimezone(zone).date()
        by_day.setdefault(day, []).append(appointment_data(appointment))

    meal_counts = {plan.pk: plan.meal_set.count() for plan in plans}

    days = []
    day = start
    while day <= end:
        plan = next((p for p in reversed(plans) if _covers(p, day)), None)
        days.append(
            {
                'date': day,
                'training': training.get(day),
                'phase': phases.get(day),
                'nutrition': {'plan': plan.description, 'meals': meal_counts[plan.pk]}
                if plan
                else None,
                'physio': [p.name for p in protocols if _covers(p, day)],
                'appointments': by_day.get(day, []),
            }
        )
        day += datetime.timedelta(days=1)

    return {'modules': modules, 'start': start, 'end': end, 'days': days}

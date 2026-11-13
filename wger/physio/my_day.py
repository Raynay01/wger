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
from django.contrib.auth.models import User
from django.db.models import Q

# wger
from wger.care.my_day import day_bounds
from wger.care.prescription import PrescriptionStatus
from wger.physio.models import (
    ExerciseRecord,
    PainRecord,
    PhysioProtocol,
)


def physio_day(user: User, day: datetime.date) -> dict:
    """The physio part of Meu Dia: current protocols and what was recorded"""
    start, end = day_bounds(user, day)
    protocols = (
        PhysioProtocol.objects.filter(user=user, status=PrescriptionStatus.PUBLISHED)
        .filter(start__lte=day)
        .filter(Q(end__isnull=True) | Q(end__gte=day))
        .prefetch_related('exercises')
    )
    done = set(
        ExerciseRecord.objects.filter(
            user=user,
            datetime__gte=start,
            datetime__lt=end,
        ).values_list('protocol_exercise_id', flat=True)
    )
    pain = PainRecord.objects.filter(user=user, datetime__gte=start, datetime__lt=end)
    return {
        'protocols': [
            {
                'id': p.pk,
                'name': p.name,
                'pain_moments': p.pain_moments,
                'exercises': [
                    {
                        'id': e.pk,
                        'name': e.name,
                        'exercise': e.exercise_id,
                        'sets': e.sets,
                        'repetitions': e.repetitions,
                        'duration_seconds': e.duration_seconds,
                        'load': e.load,
                        'location': e.location,
                        'video_url': e.video_url,
                        'instructions': e.instructions,
                        'done': e.pk in done,
                    }
                    for e in p.exercises.all()
                ],
            }
            for p in protocols
        ],
        'pain': [
            {
                'moment': r.moment,
                'value': r.value,
                'datetime': r.datetime,
                'protocol': r.protocol_id,
            }
            for r in pain
        ],
    }

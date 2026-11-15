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
The last day each patient of a professional recorded something in the
professional's own area: training, food diary or physio exercises
"""

# Standard Library
import datetime
from collections import defaultdict

# Django
from django.contrib.auth.models import User
from django.db.models import Max

# wger
from wger.care.disciplines import Discipline
from wger.care.models import (
    OPEN_STATUSES,
    CareRelationship,
)


def _sources(discipline: str) -> list[tuple]:
    """Model, field of the patient, field of the moment, per kind of record"""
    # wger
    from wger.manager.models import (
        WorkoutLog,
        WorkoutSession,
    )
    from wger.nutrition.models import (
        LogItem,
        MealAdherence,
        WaterLog,
    )
    from wger.physio.models import (
        ExerciseRecord,
        PainRecord,
    )

    return {
        Discipline.TRAINING: [
            (WorkoutSession, 'user', 'datetime_start'),
            (WorkoutLog, 'user', 'date'),
        ],
        Discipline.NUTRITION: [
            (LogItem, 'plan__user', 'datetime'),
            (MealAdherence, 'user', 'date'),
            (WaterLog, 'user', 'datetime'),
        ],
        Discipline.PHYSIO: [
            (ExerciseRecord, 'user', 'datetime'),
            (PainRecord, 'user', 'datetime'),
        ],
    }[discipline]


def _last_days(discipline: str, patients: dict[int, User]) -> dict[int, datetime.date]:
    """The last day with a record per patient, in the patient's time zone"""
    last = defaultdict(lambda: datetime.date.min)
    for model, user_field, moment_field in _sources(discipline):
        rows = (
            model.objects.filter(**{f'{user_field}__in': list(patients)})
            .values(user_field)
            .annotate(last=Max(moment_field))
        )
        for row in rows:
            patient_id, moment = row[user_field], row['last']
            if isinstance(moment, datetime.datetime):
                moment = moment.astimezone(patients[patient_id].userprofile.zone_info).date()
            last[patient_id] = max(last[patient_id], moment)
    return dict(last)


def activity(professional: User) -> list[dict]:
    """Per open follow-up of the professional: the last day with a record and the days since"""
    # wger
    from wger.care.consistency import local_today

    relationships = list(
        CareRelationship.objects.filter(
            professional=professional,
            status__in=OPEN_STATUSES,
            patient__isnull=False,
        ).select_related('patient__userprofile')
    )
    by_discipline = defaultdict(dict)
    for relationship in relationships:
        by_discipline[relationship.discipline][relationship.patient_id] = relationship.patient
    last_days = {
        discipline: _last_days(discipline, patients)
        for discipline, patients in by_discipline.items()
    }

    out = []
    for relationship in relationships:
        last_day = last_days[relationship.discipline].get(relationship.patient_id)
        days_since = None
        if last_day is not None:
            days_since = max((local_today(relationship.patient) - last_day).days, 0)
        out.append(
            {
                'relationship': relationship.id,
                'discipline': relationship.discipline,
                'last_day': last_day,
                'days_since': days_since,
            }
        )
    return out

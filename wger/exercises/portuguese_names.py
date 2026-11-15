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
Brazilian Portuguese names for exercises of the public library without a
Portuguese translation

They are stored as Portuguese translations marked by their author, so the
API, the search and the clients use them like any other translation. A
Portuguese translation from the wger.de sync always replaces them.
"""

# Standard Library
import json
import pathlib
from dataclasses import dataclass

# Django
from django.db import transaction

# wger
from wger.core.models import Language
from wger.exercises.models import (
    Exercise,
    Translation,
)


AUTHOR = 'ALMOVA (nome em português do Brasil)'
"""Marks the translations created here, so they are updated or replaced, never upstream ones"""

DATA_FILE = pathlib.Path(__file__).with_name('portuguese_names.json')

PORTUGUESE = 'pt'


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    kept_upstream: int = 0
    unknown: int = 0


def load_names() -> dict[str, str]:
    """Exercise UUID to name"""
    return json.loads(DATA_FILE.read_text(encoding='utf-8'))


@transaction.atomic
def import_names(names: dict[str, str]) -> ImportResult:
    result = ImportResult()
    language = Language.objects.get(short_name=PORTUGUESE)
    exercises = {
        str(uuid): exercise
        for uuid, exercise in Exercise.objects.in_bulk(list(names), field_name='uuid').items()
    }
    existing = {
        t.exercise_id: t
        for t in Translation.objects.filter(language=language, exercise__uuid__in=list(names))
    }
    for exercise_uuid, name in names.items():
        exercise = exercises.get(exercise_uuid)
        if exercise is None:
            result.unknown += 1
            continue
        translation = existing.get(exercise.id)
        if translation is None:
            Translation.objects.create(
                exercise=exercise,
                language=language,
                name=name,
                license_author=AUTHOR,
            )
            result.created += 1
        elif translation.license_author != AUTHOR:
            result.kept_upstream += 1
        elif translation.name != name:
            translation.name = name
            translation.save()
            result.updated += 1
        else:
            result.unchanged += 1
    return result


def remove_local_translation(exercise: Exercise, language_id: int) -> bool:
    """
    Deletes the name created here when wger.de brings a translation in the same
    language, which the unique constraint per exercise and language would refuse
    """
    deleted, _ = Translation.objects.filter(
        exercise=exercise,
        language_id=language_id,
        license_author=AUTHOR,
    ).delete()
    return deleted > 0

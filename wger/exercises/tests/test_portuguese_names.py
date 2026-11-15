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
import io
import json
import pathlib
import tempfile
import uuid
from unittest.mock import patch

# Django
from django.core.management import call_command

# wger
from wger.core.models import Language
from wger.core.tests.base_testcase import WgerTestCase
from wger.exercises.models import (
    Exercise,
    Translation,
)
from wger.exercises.portuguese_names import (
    AUTHOR,
    import_names,
    load_names,
    remove_local_translation,
)
from wger.exercises.sync import sync_exercises
from wger.exercises.tests.test_sync import MockExerciseResponse


class PortugueseNamesTestCase(WgerTestCase):
    """
    Brazilian Portuguese names for exercises without a Portuguese translation
    """

    def setUp(self):
        super().setUp()
        self.portuguese, _ = Language.objects.get_or_create(
            short_name='pt',
            defaults={'full_name': 'Português', 'full_name_en': 'Portuguese'},
        )
        self.first = Exercise.objects.get(uuid='acad3949-36fb-4481-9a72-be2ddae2bc05')
        self.second = Exercise.objects.get(uuid='ae3328ba-9a35-4731-bc23-5da50720c5aa')
        self.upstream = Translation.objects.create(
            exercise=self.second,
            language=self.portuguese,
            name='Exercício de Portugal',
            license_author='wger.de',
        )

    def names(self, **changes) -> dict[str, str]:
        return {
            str(self.first.uuid): 'Supino reto',
            str(self.second.uuid): 'Supino inclinado',
            str(uuid.uuid4()): 'Exercício de outra instalação',
            **changes,
        }

    def test_import(self):
        """Only exercises without a Portuguese translation get a name, marked by its author"""
        result = import_names(self.names())
        self.assertEqual(
            (result.created, result.kept_upstream, result.unknown),
            (1, 1, 1),
        )
        name = self.first.get_translation('pt')
        self.assertEqual(name.name, 'Supino reto')
        self.assertEqual(name.license_author, AUTHOR)
        self.assertEqual(self.second.get_translation('pt').name, 'Exercício de Portugal')

    def test_import_again(self):
        """Running it again updates the names it created and leaves the rest"""
        import_names(self.names())
        result = import_names(self.names(**{str(self.first.uuid): 'Supino reto com barra'}))
        self.assertEqual((result.created, result.updated, result.unchanged), (0, 1, 0))
        self.assertEqual(self.first.get_translation('pt').name, 'Supino reto com barra')
        self.assertEqual(import_names(self.names()).updated, 1)
        self.assertEqual(import_names(self.names()).unchanged, 1)
        self.assertEqual(
            Translation.objects.filter(exercise=self.first, language=self.portuguese).count(),
            1,
        )

    def test_command(self):
        with tempfile.TemporaryDirectory() as folder:
            data = pathlib.Path(folder) / 'names.json'
            data.write_text(json.dumps(self.names()), encoding='utf-8')
            with patch('wger.exercises.portuguese_names.DATA_FILE', data):
                call_command('import-exercise-names-pt', stdout=io.StringIO())
        self.assertEqual(self.first.get_translation('pt').name, 'Supino reto')

    def test_data_file(self):
        """Every entry has an exercise UUID and a name that fits the field"""
        names = load_names()
        self.assertGreater(len(names), 800)
        for exercise_uuid, name in names.items():
            self.assertEqual(str(uuid.UUID(exercise_uuid)), exercise_uuid)
            self.assertTrue(0 < len(name) <= 200, exercise_uuid)

    @patch('requests.get', return_value=MockExerciseResponse())
    def test_sync_replaces_the_local_name(self, mock_request):
        """A translation from wger.de replaces the local name in its language, not in others"""
        local = Translation.objects.create(
            exercise=self.second,
            language_id=3,
            name='Nome local',
            license_author=AUTHOR,
        )
        italian, _ = Language.objects.get_or_create(
            short_name='it',
            defaults={'full_name': 'Italiano', 'full_name_en': 'Italian'},
        )
        other_language = Translation.objects.create(
            exercise=self.second,
            language=italian,
            name='Nombre local',
            license_author=AUTHOR,
        )

        sync_exercises(lambda x: x)

        self.assertFalse(Translation.objects.filter(pk=local.pk).exists())
        replaced = self.second.translations.get(language_id=3)
        self.assertEqual(str(replaced.uuid), '581338a1-8e52-405b-99eb-f0724c528bc8')
        self.assertTrue(Translation.objects.filter(pk=other_language.pk).exists())

    def test_sync_keeps_other_local_translations(self):
        """Only the names created here make room for wger.de, not translations of users"""
        self.assertFalse(remove_local_translation(self.second, self.portuguese.id))
        self.assertTrue(Translation.objects.filter(pk=self.upstream.pk).exists())

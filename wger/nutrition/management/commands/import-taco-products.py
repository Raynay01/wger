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
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

# Django
from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction

# Third Party
import requests

# wger
from wger.core.models import (
    Language,
    License,
)
from wger.nutrition.extract_info.taco import (
    TACO_URL,
    extract_info_from_taco,
    household_measures,
    remote_id,
)
from wger.nutrition.models import (
    Ingredient,
    IngredientCategory,
    IngredientWeightUnit,
    Source,
)
from wger.utils.requests import wger_headers


DATA_COMMIT = 'b800c910dfc9d2e8e6bab45dd42e5b8f5167b466'
DATA_URL = (
    f'https://raw.githubusercontent.com/brolesi/taco/{DATA_COMMIT}'
    '/data/processed/taco/taco_composicao.csv'
)
DATA_SHA256 = '7dee98c4562c4faecc713712d5ae9f909a2a43a8fa4f10c81d3d52fc5cad6058'

POF_URL = (
    f'https://raw.githubusercontent.com/brolesi/taco/{DATA_COMMIT}'
    '/data/processed/pof/pof_medidas_caseiras.csv'
)
POF_SHA256 = 'baf300288eb153d94592ff3818e87641feeb996da23b3b8ed99fd5e5e2e65ff8'

HOUSEHOLD_MAP = Path(__file__).resolve().parents[2] / 'extract_info' / 'taco_household_map.json'


class Command(BaseCommand):
    """
    Imports the foods of the TACO (Brazilian food composition table) as ingredients
    """

    help = (
        'Imports the TACO, Tabela Brasileira de Composição de Alimentos (NEPA/UNICAMP). '
        'Running it again updates the foods instead of duplicating them.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            dest='file',
            default='',
            help='Local copy of taco_composicao.csv instead of downloading the pinned version',
        )
        parser.add_argument(
            '--pof-file',
            dest='pof_file',
            default='',
            help='Local copy of pof_medidas_caseiras.csv (household measures of the POF/IBGE)',
        )

    def read_csv(self, path: str, url: str, sha256: str) -> str:
        if path:
            with open(path, encoding='utf-8') as handle:
                return handle.read()

        self.stdout.write(f'Downloading {url}')
        response = requests.get(url, headers=wger_headers(), timeout=120)
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != sha256:
            raise CommandError('The downloaded file does not match the expected checksum')
        return response.content.decode('utf-8')

    def import_measures(self, pof_content: str, ingredients: dict[str, Ingredient]) -> Counter:
        """Household measures (colher de sopa, concha, ...) of the imported foods"""
        with open(HOUSEHOLD_MAP, encoding='utf-8') as handle:
            entries = json.load(handle)['entries']
        measures, left_out = household_measures(
            entries,
            list(csv.DictReader(io.StringIO(pof_content))),
        )

        counter = Counter(measures_left_out=left_out)
        for taco_id, units in measures.items():
            ingredient = ingredients.get(remote_id({'numero_alimento': taco_id}))
            if ingredient is None:
                continue
            for name, gram in units:
                _, created = IngredientWeightUnit.objects.update_or_create(
                    ingredient=ingredient,
                    name=name,
                    defaults={'gram': gram},
                )
                counter['measures_new' if created else 'measures_updated'] += 1
        return counter

    @transaction.atomic
    def handle(self, **options):
        content = self.read_csv(options['file'], DATA_URL, DATA_SHA256)
        pof_content = self.read_csv(options['pof_file'], POF_URL, POF_SHA256)
        language = Language.objects.get(short_name='pt')
        license_obj, _ = License.objects.get_or_create(
            short_name='TACO',
            defaults={
                'full_name': 'TACO: reprodução permitida desde que citada a fonte',
                'url': TACO_URL,
            },
        )

        counter = Counter()
        ingredients = {}
        for row in csv.DictReader(io.StringIO(content)):
            try:
                data = extract_info_from_taco(row, language.pk, license_obj.pk)
            except (KeyError, ValueError) as error:
                self.stdout.write(f'Skipped: {error}')
                counter['skipped'] += 1
                continue

            category = None
            if row.get('categoria'):
                category, _ = IngredientCategory.objects.get_or_create(
                    name=row['categoria'].strip()
                )

            data.clean_name()
            ingredient, created = Ingredient.objects.update_or_create(
                source_name=Source.TACO.value,
                remote_id=data.remote_id,
                defaults={**data.dict(), 'category': category},
            )
            ingredients[data.remote_id] = ingredient
            counter['new' if created else 'updated'] += 1

        counter.update(self.import_measures(pof_content, ingredients))

        self.stdout.write(self.style.SUCCESS(f'TACO imported: {dict(counter)}'))

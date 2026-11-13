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
import tempfile
from decimal import Decimal

# Django
from django.core.management import call_command

# wger
from wger.core.models import (
    Language,
    License,
)
from wger.core.tests.base_testcase import WgerTestCase
from wger.nutrition.extract_info.taco import extract_info_from_taco
from wger.nutrition.models import (
    Ingredient,
    Source,
)


COLUMNS = [
    'numero_alimento',
    'descricao',
    'energia_kcal',
    'proteina_g',
    'lipideos_g',
    'carboidrato_g',
    'fibra_g',
    'sodio_mg',
    'categoria',
]

RICE = {
    'numero_alimento': '1',
    'descricao': 'Arroz, integral, cozido',
    'energia_kcal': '123.53489250000001',
    'proteina_g': '2.58825',
    'lipideos_g': '1.0003333333333333',
    'carboidrato_g': '25.80975',
    'fibra_g': '2.749333333333334',
    'sodio_mg': '1.2446666666666666',
    'categoria': 'Cereais e derivados',
}
OLIVE_OIL = {
    'numero_alimento': '260',
    'descricao': 'Azeite, de oliva, extra virgem',
    'energia_kcal': '884.0',
    'proteina_g': '',
    'lipideos_g': '100.0',
    'carboidrato_g': '',
    'fibra_g': '',
    'sodio_mg': '',
    'categoria': 'Gorduras e óleos',
}
MILK = {
    'numero_alimento': '458',
    'descricao': 'Leite, de vaca, integral',
    'energia_kcal': '',
    'proteina_g': '',
    'lipideos_g': '',
    'carboidrato_g': '',
    'fibra_g': '',
    'sodio_mg': '',
    'categoria': 'Leite e derivados',
}
LIVER = {
    'numero_alimento': '400',
    'descricao': 'Frango, fígado, cru',
    'energia_kcal': '106.4',
    'proteina_g': '17.59',
    'lipideos_g': '3.49',
    'carboidrato_g': '-0.02333333333333809',
    'fibra_g': '',
    'sodio_mg': '82.0',
    'categoria': 'Carnes e derivados',
}
LIME = {
    'numero_alimento': '220',
    'descricao': 'Limão, tahiti, cru',
    'energia_kcal': '31.818153430163903',
    'proteina_g': '0.9395833333333332',
    'lipideos_g': '0.14',
    'carboidrato_g': '11.084416666666677',
    'fibra_g': '1.1816666666666666',
    'sodio_mg': '1.2483333333333333',
    'categoria': 'Frutas e derivados',
}
SPIRIT = {
    'numero_alimento': '472',
    'descricao': 'Cana, aguardente 1',
    'energia_kcal': '215.6',
    'proteina_g': '',
    'lipideos_g': '',
    'carboidrato_g': '',
    'fibra_g': '',
    'sodio_mg': '',
    'categoria': 'Bebidas (alcoólicas e não alcoólicas)',
}


class TacoExtractTestCase(WgerTestCase):
    """
    Values of TACO rows, rounded as printed, never guessed
    """

    def test_rounding_and_units(self):
        data = extract_info_from_taco(RICE, 1, 1)
        self.assertEqual(data.energy, 124)
        self.assertEqual(data.protein, Decimal('2.6'))
        self.assertEqual(data.fat, Decimal('1.0'))
        self.assertEqual(data.carbohydrates, Decimal('25.8'))
        self.assertEqual(data.fiber, Decimal('2.7'))
        self.assertEqual(data.sodium, Decimal('0.001'))
        self.assertEqual(data.remote_id, 'TACO-1')
        self.assertEqual(data.source_name, Source.TACO.value)

    def test_pure_fat_has_no_protein_or_carbohydrates(self):
        data = extract_info_from_taco(OLIVE_OIL, 1, 1)
        self.assertEqual((data.protein, data.carbohydrates), (Decimal(0), Decimal(0)))
        self.assertIsNone(data.fiber)
        self.assertIsNone(data.sodium)

    def test_missing_values_are_not_guessed(self):
        for row in (MILK, SPIRIT):
            with self.assertRaises(KeyError):
                extract_info_from_taco(row, 1, 1)

    def test_official_energy_is_kept(self):
        """Carbohydrates include the fiber here, the generic energy check would refuse the lime"""
        data = extract_info_from_taco(LIME, 1, 1)
        self.assertEqual(data.energy, 32)
        self.assertEqual(data.carbohydrates, Decimal('11.1'))

    def test_negative_carbohydrate_mean_is_zero(self):
        self.assertEqual(extract_info_from_taco(LIVER, 1, 1).carbohydrates, Decimal('0.0'))


class TacoImportTestCase(WgerTestCase):
    """
    The import command creates the foods once and updates them on later runs
    """

    def setUp(self):
        super().setUp()
        Language.objects.get_or_create(short_name='pt', defaults={'full_name': 'Português'})
        self.file = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, encoding='utf-8')
        writer = csv.DictWriter(self.file, fieldnames=COLUMNS)
        writer.writeheader()
        for row in (RICE, OLIVE_OIL, MILK, LIVER, SPIRIT):
            writer.writerow(row)
        self.file.close()

    def run_import(self):
        call_command('import-taco-products', file=self.file.name, stdout=open('/dev/null', 'w'))

    def test_import_is_idempotent(self):
        self.run_import()
        self.run_import()
        foods = Ingredient.objects.filter(source_name=Source.TACO.value)
        self.assertEqual(foods.count(), 3)
        self.assertEqual(
            set(foods.values_list('remote_id', flat=True)),
            {'TACO-1', 'TACO-260', 'TACO-400'},
        )
        self.assertEqual(License.objects.filter(short_name='TACO').count(), 1)

        rice = foods.get(remote_id='TACO-1')
        self.assertEqual(rice.name, 'Arroz, integral, cozido')
        self.assertEqual(rice.language.short_name, 'pt')
        self.assertEqual(rice.category.name, 'Cereais e derivados')
        self.assertEqual(rice.license.short_name, 'TACO')
        self.assertIn('NEPA/UNICAMP', rice.license_author)

    def test_update_keeps_the_ingredient(self):
        self.run_import()
        rice = Ingredient.objects.get(remote_id='TACO-1')
        Ingredient.objects.filter(pk=rice.pk).update(energy=1)
        self.run_import()
        rice.refresh_from_db()
        self.assertEqual(rice.energy, 124)

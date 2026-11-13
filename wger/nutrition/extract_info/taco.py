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
TACO, Tabela Brasileira de Composição de Alimentos (4th edition, NEPA/UNICAMP)

Rows come from the processed CSV ``taco_composicao.csv`` of the brolesi/taco
project: means per 100 g of edible portion, empty cells for values the table
does not give, 1e-05 for traces ("Tr").
"""

# Standard Library
from decimal import (
    ROUND_HALF_UP,
    Decimal,
)

# wger
from wger.nutrition.dataclasses import IngredientData
from wger.nutrition.models import Source


TACO_URL = 'https://www.nepa.unicamp.br/taco/'
TACO_AUTHOR = (
    'NEPA/UNICAMP. Tabela Brasileira de Composição de Alimentos (TACO), '
    '4ª edição revisada e ampliada. Campinas, 2011.'
)

PURE_FAT_GRAMS = Decimal('99.5')
"""From this much fat per 100 g there is no room for protein or carbohydrates"""


def _value(row: dict, column: str, places: str) -> Decimal | None:
    """The value rounded to the precision printed in the TACO, None if not given"""
    raw = (row.get(column) or '').strip()
    if raw == '':
        return None
    value = Decimal(raw).quantize(Decimal(places), rounding=ROUND_HALF_UP)
    # Carbohydrates are calculated by difference, a few means end up a hair below zero
    return max(value, Decimal(0))


def remote_id(row: dict) -> str:
    return f'TACO-{int(row["numero_alimento"])}'


def extract_info_from_taco(row: dict, language_id: int, license_id: int) -> IngredientData:
    """
    The ingredient of a TACO row. Raises KeyError for foods without the basic
    values, which are skipped instead of guessed.
    """
    energy = _value(row, 'energia_kcal', '1')
    protein = _value(row, 'proteina_g', '0.1')
    fat = _value(row, 'lipideos_g', '0.1')
    carbohydrates = _value(row, 'carboidrato_g', '0.1')

    # Oils: the table leaves protein and carbohydrates empty, the fat takes up all the mass
    if energy is not None and fat is not None and fat >= PURE_FAT_GRAMS:
        protein = Decimal(0) if protein is None else protein
        carbohydrates = Decimal(0) if carbohydrates is None else carbohydrates

    basic = {'energy': energy, 'protein': protein, 'fat': fat, 'carbohydrates': carbohydrates}
    missing = [name for name, value in basic.items() if value is None]
    if missing:
        raise KeyError(f'TACO {row.get("numero_alimento")} has no {", ".join(missing)}')

    sodium_mg = _value(row, 'sodio_mg', '1')
    name = row['descricao'].strip()

    data = IngredientData(
        code=None,
        remote_id=remote_id(row),
        name=name,
        common_name=name,
        language_id=language_id,
        energy=int(energy),
        protein=protein,
        carbohydrates=carbohydrates,
        carbohydrates_sugar=None,
        fat=fat,
        fat_saturated=None,
        fiber=_value(row, 'fibra_g', '0.1'),
        sodium=None if sodium_mg is None else (sodium_mg / 1000).quantize(Decimal('0.001')),
        source_name=Source.TACO.value,
        source_url=TACO_URL,
        brand='',
        license_id=license_id,
        license_author=TACO_AUTHOR,
        license_title=name,
        license_object_url=TACO_URL,
    )
    # No energy plausibility check: the TACO's carbohydrates include the fiber and its
    # energy comes from food-specific factors (and alcohol), the check assumes neither
    data.sanity_checks(check_energy=False)
    return data

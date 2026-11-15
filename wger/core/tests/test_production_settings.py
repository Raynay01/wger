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
import json
import os
import pathlib
import subprocess
import sys

# Django
from django.test import SimpleTestCase


ROOT = pathlib.Path(__file__).resolve().parents[3]

BASE_ENVIRONMENT = {
    'DJANGO_DB_ENGINE': 'django.db.backends.postgresql',
    'DJANGO_DB_DATABASE': 'wger',
}

NAMES = [
    'ALLOWED_HOSTS',
    'CORS_ALLOWED_ORIGINS',
    'CORS_ALLOW_ALL_ORIGINS',
    'CORS_ORIGIN_ALLOW_ALL',
]


def allows_all_origins(values: dict) -> bool:
    """django-cors-headers reads the new name first and falls back to the old one"""
    if values['CORS_ALLOW_ALL_ORIGINS'] is not None:
        return values['CORS_ALLOW_ALL_ORIGINS']
    return bool(values['CORS_ORIGIN_ALLOW_ALL'])


def production_settings(names: list[str] = NAMES, **environment: str) -> dict:
    """Values of settings/main.py loaded in a fresh process with the given environment"""
    code = (
        'import json, warnings\n'
        'warnings.simplefilter("ignore")\n'
        'import settings.main as s\n'
        f'print(json.dumps({{n: getattr(s, n, None) for n in {names!r}}}, default=str))\n'
    )
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('DJANGO_', 'CORS_'))}
    result = subprocess.run(
        [sys.executable, '-c', code],
        cwd=ROOT,
        env={**clean, **BASE_ENVIRONMENT, **environment},
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


class AllowedOriginsTestCase(SimpleTestCase):
    """
    In production, the API answers browsers only from the listed origins and
    the site only to the listed host names
    """

    def test_no_cross_origin_by_default(self):
        values = production_settings()
        self.assertEqual(values['CORS_ALLOWED_ORIGINS'], [])
        self.assertFalse(allows_all_origins(values))

    def test_listed_origins(self):
        values = production_settings(
            CORS_ALLOWED_ORIGINS='https://app.almova.com.br,https://almova.com.br',
        )
        self.assertEqual(
            values['CORS_ALLOWED_ORIGINS'],
            ['https://app.almova.com.br', 'https://almova.com.br'],
        )
        self.assertFalse(allows_all_origins(values))

    def test_allowed_hosts(self):
        self.assertEqual(production_settings()['ALLOWED_HOSTS'], ['*'])
        self.assertEqual(
            production_settings(DJANGO_ALLOWED_HOSTS='api.almova.com.br,localhost')[
                'ALLOWED_HOSTS'
            ],
            ['api.almova.com.br', 'localhost'],
        )

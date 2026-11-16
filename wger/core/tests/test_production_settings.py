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


class SecurityHeadersTestCase(SimpleTestCase):
    """
    In production, Django sends the security headers: HSTS when configured and
    the content security policy, with inline scripts only by nonce
    """

    names = [
        'MIDDLEWARE',
        'SECURE_HSTS_SECONDS',
        'SECURE_HSTS_INCLUDE_SUBDOMAINS',
        'SECURE_CSP',
        'SECURE_CSP_REPORT_ONLY',
    ]

    def test_middleware_and_policies(self):
        values = production_settings(self.names)
        middleware = values['MIDDLEWARE']
        self.assertIn('django.middleware.security.SecurityMiddleware', middleware)
        self.assertIn('django.middleware.csp.ContentSecurityPolicyMiddleware', middleware)
        self.assertLess(
            middleware.index('django.middleware.security.SecurityMiddleware'),
            middleware.index('django.middleware.common.CommonMiddleware'),
        )
        policy = values['SECURE_CSP']
        self.assertEqual(policy['frame-ancestors'], ["'none'"])
        self.assertEqual(policy['object-src'], ["'none'"])
        self.assertEqual(policy['default-src'], ["'self'"])
        self.assertEqual(policy['script-src'], ["'self'", '<CSP_NONCE_SENTINEL>'])
        self.assertEqual(policy['frame-src'], ["'self'"])
        self.assertFalse(values['SECURE_CSP_REPORT_ONLY'])
        self.assertEqual(values['SECURE_HSTS_SECONDS'], 0)

    def test_hsts_from_the_environment(self):
        values = production_settings(
            self.names,
            SECURE_HSTS_SECONDS='63072000',
            SECURE_HSTS_INCLUDE_SUBDOMAINS='True',
        )
        self.assertEqual(values['SECURE_HSTS_SECONDS'], 63072000)
        self.assertTrue(values['SECURE_HSTS_INCLUDE_SUBDOMAINS'])

    def test_media_host_in_the_policy(self):
        values = production_settings(['SECURE_CSP'], MEDIA_URL='https://cdn.almova.com.br/m/')
        self.assertIn('cdn.almova.com.br', values['SECURE_CSP']['img-src'])
        self.assertIn('cdn.almova.com.br', values['SECURE_CSP']['script-src'])

    def test_captcha_hosts(self):
        for environment, host in (
            ({'CAPTCHA_PROVIDER': 'turnstile'}, 'https://challenges.cloudflare.com'),
            ({'CAPTCHA_PROVIDER': 'recaptcha'}, 'https://www.google.com'),
            ({'USE_RECAPTCHA': 'True'}, 'https://www.google.com'),
        ):
            with self.subTest(environment):
                policy = production_settings(['SECURE_CSP'], **environment)['SECURE_CSP']
                self.assertIn(host, policy['script-src'])
                self.assertIn(host, policy['frame-src'])

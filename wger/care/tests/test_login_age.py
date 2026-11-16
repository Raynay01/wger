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
import time
from unittest import mock

# Django
from django.contrib.sessions.backends.db import SessionStore
from django.test import (
    Client,
    override_settings,
)
from django.urls import reverse

# Third Party
from allauth.account.authentication import AUTHENTICATION_METHODS_SESSION_KEY
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.login_age import login_started
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase


DAY = 24 * 3600


def days_later(days: float):
    """The clock of the login age check, the given number of days from now"""
    clock = mock.patch('wger.care.login_age.time')
    fake = clock.start()
    fake.time.return_value = time.time() + days * DAY
    return clock


@override_settings(CARE_PROFESSIONAL_LOGIN_DAYS=30)
class ProfessionalLoginAgeTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    A professional logs in again 30 days after the login, however often the
    token was refreshed in between; patients keep their long login
    """

    def setUp(self):
        super().setUp()
        self.build_team()

    def login(self, user) -> dict:
        user.set_password('senha-teste-123')
        user.save()
        response = Client().post(
            reverse('headless:app:account:login'),
            data=json.dumps({'username': user.username, 'password': 'senha-teste-123'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        return response.json()['meta']

    def refresh(self, refresh_token: str):
        return Client().post(
            reverse('headless:app:tokens:refresh'),
            data=json.dumps({'refresh_token': refresh_token}),
            content_type='application/json',
        )

    def api(self, access_token: str):
        return Client().get(
            reverse('care-relationship-list'),
            HTTP_AUTHORIZATION=f'Bearer {access_token}',
        )

    def test_professional_until_the_limit(self):
        tokens = self.login(self.trainer)
        clock = days_later(29)
        response = self.refresh(tokens['refresh_token'])
        clock.stop()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertEqual(self.api(data['access_token']).status_code, status.HTTP_200_OK)

        # The refresh on day 29 did not restart the count
        clock = days_later(31)
        response = self.refresh(data['refresh_token'])
        clock.stop()
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        # The login is gone: the first token does not work later either
        clock = days_later(1)
        response = self.refresh(tokens['refresh_token'])
        clock.stop()
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

    def test_patient_keeps_the_login(self):
        tokens = self.login(self.patient)
        clock = days_later(31)
        response = self.refresh(tokens['refresh_token'])
        clock.stop()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(CARE_PROFESSIONAL_LOGIN_DAYS=0)
    def test_switched_off(self):
        tokens = self.login(self.trainer)
        clock = days_later(31)
        response = self.refresh(tokens['refresh_token'])
        clock.stop()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_browser_session(self):
        """A session without allauth's records counts from the first request"""
        self.client.force_login(self.trainer)
        url = reverse('care-relationship-list')

        def patients() -> int:
            return self.client.get(url).json()['count']

        self.assertGreater(patients(), 0)
        clock = days_later(29)
        self.assertGreater(patients(), 0)
        clock.stop()
        clock = days_later(31)
        self.assertIn(
            self.client.get(url).status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
        clock.stop()
        self.assertNotEqual(self.client.session.get('_auth_user_id'), str(self.trainer.pk))

    def test_counted_from_the_login(self):
        """A later step in the same session, such as confirming the password, does not count"""
        session = SessionStore()
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {'method': 'password', 'at': 1000.0},
            {'method': 'password', 'at': 5000.0, 'reauthenticated': True},
        ]
        self.assertEqual(login_started(session), 1000.0)

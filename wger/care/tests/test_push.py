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
import tempfile
from unittest import mock

# Django
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

# Third Party
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care import push
from wger.care.models import (
    NotificationLog,
    NotificationPreference,
    PushDevice,
)
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase


class FakeResponse:
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class PushTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Devices are registered by the app and get the notices through Firebase,
    signed with the service account, with the same text as the emails
    """

    def setUp(self):
        super().setUp()
        self.build_team()
        cache.delete(push.ACCESS_TOKEN_CACHE_KEY)
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        folder = tempfile.mkdtemp()
        self.account_file = os.path.join(folder, 'firebase.json')
        with open(self.account_file, 'w') as handle:
            json.dump(
                {
                    'client_email': 'almova@projeto.iam.gserviceaccount.com',
                    'private_key': self.key.private_bytes(
                        serialization.Encoding.PEM,
                        serialization.PrivateFormat.PKCS8,
                        serialization.NoEncryption(),
                    ).decode(),
                    'token_uri': push.TOKEN_URL,
                },
                handle,
            )
        settings = override_settings(
            FCM_PROJECT_ID='almova-teste',
            FCM_SERVICE_ACCOUNT_FILE=self.account_file,
            WEB_APP_URL='https://app.almova.com.br',
        )
        settings.enable()
        self.addCleanup(settings.disable)
        self.requests = []

    def google(self, fcm_status: int = 200, fcm_data: dict | None = None):
        def post(url, **kwargs):
            self.requests.append((url, kwargs))
            if url == push.TOKEN_URL:
                return FakeResponse(200, {'access_token': 'acesso-123', 'expires_in': 3600})
            return FakeResponse(fcm_status, fcm_data or {})

        return mock.patch('wger.care.push.requests.post', side_effect=post)

    def register(self, user, token='token-celular-1', platform='android'):
        self.client.force_authenticate(user)
        return self.client.post(
            reverse('care-push-devices'),
            {'token': token, 'platform': platform},
            format='json',
        )

    def test_register_and_remove(self):
        self.assertEqual(self.register(self.patient).status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.get(reverse('care-push-devices')).data, {'devices': 1})
        # The same phone, now logged in by someone else: the token moves
        self.register(self.trainer)
        self.assertEqual(PushDevice.objects.get().user, self.trainer)
        # Only the owner removes it
        self.client.force_authenticate(self.patient)
        response = self.client.post(
            reverse('care-push-devices-remove'), {'token': 'token-celular-1'}, format='json'
        )
        self.assertFalse(response.data['removed'])
        self.client.force_authenticate(self.trainer)
        response = self.client.post(
            reverse('care-push-devices-remove'), {'token': 'token-celular-1'}, format='json'
        )
        self.assertTrue(response.data['removed'])
        self.assertFalse(PushDevice.objects.exists())

    def test_register_needs_a_platform(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post(reverse('care-push-devices'), {'token': 'abc'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_signed_by_the_service_account(self):
        self.register(self.patient)
        with self.google():
            delivered = push.send(self.patient, 'ALMOVA: Plano novo', 'Um texto', '/app')
        self.assertEqual(delivered, 1)
        (token_url, token_call), (fcm_url, fcm_call) = self.requests
        claims = jwt.decode(
            token_call['data']['assertion'],
            self.key.public_key(),
            algorithms=['RS256'],
            audience=push.TOKEN_URL,
        )
        self.assertEqual(claims['iss'], 'almova@projeto.iam.gserviceaccount.com')
        self.assertEqual(claims['scope'], push.SCOPE)
        self.assertEqual(
            fcm_url, 'https://fcm.googleapis.com/v1/projects/almova-teste/messages:send'
        )
        self.assertEqual(fcm_call['headers'], {'Authorization': 'Bearer acesso-123'})
        message = fcm_call['json']['message']
        self.assertEqual(message['token'], 'token-celular-1')
        self.assertEqual(
            message['notification'], {'title': 'ALMOVA: Plano novo', 'body': 'Um texto'}
        )
        self.assertEqual(message['data'], {'path': '/app'})

    def test_access_token_reused(self):
        self.register(self.patient)
        with self.google():
            push.send(self.patient, 't', 'b', '/app')
            push.send(self.patient, 't', 'b', '/app')
        self.assertEqual([url for url, _ in self.requests].count(push.TOKEN_URL), 1)

    def test_uninstalled_app_removes_the_device(self):
        self.register(self.patient)
        unregistered = {'error': {'details': [{'errorCode': 'UNREGISTERED'}]}}
        with self.google(fcm_status=400, fcm_data=unregistered):
            self.assertEqual(push.send(self.patient, 't', 'b', '/app'), 0)
        self.assertFalse(PushDevice.objects.exists())

    def test_other_errors_keep_the_device(self):
        self.register(self.patient)
        with self.google(fcm_status=503):
            self.assertEqual(push.send(self.patient, 't', 'b', '/app'), 0)
        self.assertTrue(PushDevice.objects.exists())

    @override_settings(FCM_PROJECT_ID='')
    def test_off_without_configuration(self):
        self.register(self.patient)
        with self.google():
            self.assertEqual(push.send(self.patient, 't', 'b', '/app'), 0)
        self.assertEqual(self.requests, [])

    def schedule(self):
        self.client.force_authenticate(self.physio)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse('appointment-list'),
                {
                    'relationship': str(self.physio_rel.pk),
                    'kind': 'session',
                    'start': '2026-03-10T14:00:00-03:00',
                    'duration_minutes': 50,
                },
            )

    def test_notice_by_email_and_push(self):
        self.register(self.patient)
        with self.google():
            self.schedule()
        self.assertEqual(len(mail.outbox), 1)
        message = self.requests[-1][1]['json']['message']
        self.assertEqual(message['data'], {'path': '/app/agenda'})
        self.assertEqual(mail.outbox[0].body.count(message['notification']['body']), 1)
        self.assertEqual(
            set(NotificationLog.objects.values_list('channel', flat=True)),
            {'email', 'push'},
        )

    def test_push_turned_off(self):
        self.register(self.patient)
        NotificationPreference.objects.create(user=self.patient, push_appointments=False)
        with self.google():
            self.schedule()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.requests, [])
        self.assertEqual(list(NotificationLog.objects.values_list('channel', flat=True)), ['email'])

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

# Django
from django.test import override_settings
from django.urls import reverse

# Third Party
from allauth.mfa.totp.internal.auth import (
    TOTP,
    generate_totp_secret,
)
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

# wger
from wger.care.models import Membership
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.utils.api_token import create_token


@override_settings(CARE_PROFESSIONAL_MFA=True)
class ProfessionalMfaTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Professional accounts need two-step verification before the API answers
    them; the steps to set it up stay open
    """

    def setUp(self):
        super().setUp()
        self.build_team()

    def get(self, user, name: str, **kwargs):
        self.client.force_authenticate(user)
        return self.client.get(reverse(name, kwargs=kwargs or None))

    def turn_on(self, user):
        TOTP.activate(user, generate_totp_secret())

    def test_professional_without_second_step(self):
        response = self.get(self.trainer, 'care-relationship-list')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['code'], 'mfa_required')
        self.assertEqual(
            self.get(self.trainer, 'care-mfa').data,
            {'professional': True, 'enabled': False, 'required': True},
        )

    def test_setup_stays_open(self):
        """Status, QR code, organization and council registration"""
        for name in ('care-mfa', 'organization-list', 'professional-registration-list'):
            self.assertEqual(self.get(self.trainer, name).status_code, status.HTTP_200_OK, name)
        response = self.client.post(
            reverse('care-mfa-qr'),
            {'url': 'otpauth://totp/ALMOVA:bruno?secret=JBSWY3DPEHPK3PXP&issuer=ALMOVA'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['svg'].startswith('<svg'))

    def test_qr_only_for_setup_links(self):
        self.client.force_authenticate(self.trainer)
        response = self.client.post(
            reverse('care-mfa-qr'),
            {'url': 'https://example.com/'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_professional_with_second_step(self):
        self.turn_on(self.trainer)
        self.assertEqual(
            self.get(self.trainer, 'care-relationship-list').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.get(self.trainer, 'care-mfa').data,
            {'professional': True, 'enabled': True, 'required': False},
        )

    def test_patients_are_not_affected(self):
        self.assertEqual(
            self.get(self.patient, 'care-relationship-list').status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(self.get(self.patient, 'care-mfa').data['required'])

    def test_ended_membership(self):
        Membership.objects.filter(user=self.trainer).update(is_active=False)
        self.assertEqual(
            self.get(self.trainer, 'care-relationship-list').status_code,
            status.HTTP_200_OK,
        )

    def test_api_key_is_refused_too(self):
        """Every authentication counts, not only the login of the web app"""
        token = create_token(self.trainer)
        response = self.client.get(
            reverse('care-relationship-list'),
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['code'], 'mfa_required')

    def test_tokens_are_refused_too(self):
        """The web app's token from the login and a plain JWT"""
        self.trainer.set_password('trainer-pass-123')
        self.trainer.save()
        login = self.client.post(
            '/allauth/app/v1/auth/login',
            {'username': self.trainer.username, 'password': 'trainer-pass-123'},
            format='json',
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        for token in (
            login.json()['meta']['access_token'],
            str(AccessToken.for_user(self.trainer)),
        ):
            response = self.client.get(
                reverse('care-relationship-list'),
                HTTP_AUTHORIZATION=f'Bearer {token}',
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(response.json()['code'], 'mfa_required')

    @override_settings(CARE_PROFESSIONAL_MFA=False)
    def test_switched_off(self):
        self.assertEqual(
            self.get(self.trainer, 'care-relationship-list').status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(self.get(self.trainer, 'care-mfa').data['required'])

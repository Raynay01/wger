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
import datetime

# Django
from django.urls import reverse
from django.utils import timezone

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.physio.models import (
    PainRecord,
    PhysioProtocol,
)
from wger.trophies.services.trophy import TrophyService


class GamificationTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Achievements and streaks: switched off by the patient or a professional,
    suspended after pain at the alert threshold
    """

    def setUp(self):
        super().setUp()
        self.build_team()
        self.protocol = PhysioProtocol(name='Joelho')
        start_prescription(self.protocol, self.physio_rel, self.physio)
        self.protocol.pain_alert_threshold = 6
        self.protocol.save()
        self.protocol.publish()

    def status(self) -> dict:
        self.client.force_authenticate(self.patient)
        response = self.client.get(reverse('care-gamification'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def switch(self, user, relationship, enabled: bool):
        self.client.force_authenticate(user)
        return self.client.post(
            reverse('care-relationship-gamification', kwargs={'pk': relationship.pk}),
            {'enabled': enabled},
            format='json',
        )

    def pain(self, value: int, days_ago: int):
        PainRecord.objects.create(
            user=self.patient,
            protocol=self.protocol,
            moment='after',
            value=value,
            datetime=timezone.now() - datetime.timedelta(days=days_ago),
        )

    def test_on_by_default(self):
        self.assertEqual(
            self.status(),
            {'enabled': True, 'reason': None, 'disabled_by': [], 'pain_until': None},
        )
        self.assertFalse(TrophyService.should_skip_user(self.patient))

    def test_off_by_the_patient(self):
        self.patient.userprofile.trophies_enabled = False
        self.patient.userprofile.save()
        data = self.status()
        self.assertFalse(data['enabled'])
        self.assertEqual(data['reason'], 'patient')

    def test_off_by_a_professional(self):
        """Any professional of an open follow-up turns them off, for every area"""
        response = self.switch(self.trainer, self.training_rel, False)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['gamification_enabled'])

        data = self.status()
        self.assertFalse(data['enabled'])
        self.assertEqual(data['reason'], 'professional')
        self.assertEqual(
            data['disabled_by'],
            [self.trainer.get_full_name() or self.trainer.username],
        )
        self.assertTrue(TrophyService.should_skip_user(self.patient))

        # Back on
        self.switch(self.trainer, self.training_rel, True)
        self.assertTrue(self.status()['enabled'])

    def test_ended_follow_up_no_longer_counts(self):
        self.switch(self.trainer, self.training_rel, False)
        self.training_rel.refresh_from_db()
        self.assertFalse(self.training_rel.gamification_enabled)
        self.training_rel.status = 'ended'
        self.training_rel.save()
        self.assertTrue(self.status()['enabled'])
        response = self.switch(self.trainer, self.training_rel, True)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_the_professional_switches(self):
        response = self.switch(self.patient, self.training_rel, False)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.switch(self.nutritionist, self.training_rel, False)
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )
        self.assertTrue(self.status()['enabled'])

    def test_switch_needs_a_value(self):
        self.client.force_authenticate(self.trainer)
        response = self.client.post(
            reverse('care-relationship-gamification', kwargs={'pk': self.training_rel.pk}),
            {},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suspended_after_pain_at_the_threshold(self):
        """Pain at the protocol's threshold in the last 14 days suspends them"""
        self.pain(5, days_ago=1)
        self.assertTrue(self.status()['enabled'])

        self.pain(6, days_ago=15)
        self.assertTrue(self.status()['enabled'])

        self.pain(6, days_ago=3)
        data = self.status()
        self.assertFalse(data['enabled'])
        self.assertEqual(data['reason'], 'pain')
        record = PainRecord.objects.get(
            value=6, datetime__gte=timezone.now() - datetime.timedelta(days=4)
        )
        self.assertEqual(
            datetime.datetime.fromisoformat(data['pain_until'].replace('Z', '+00:00')),
            record.datetime + datetime.timedelta(days=14),
        )
        self.assertTrue(TrophyService.should_skip_user(self.patient))

    def test_relationship_shows_the_switch(self):
        self.client.force_authenticate(self.patient)
        response = self.client.get(
            reverse('care-relationship-detail', kwargs={'pk': self.training_rel.pk})
        )
        self.assertTrue(response.data['gamification_enabled'])

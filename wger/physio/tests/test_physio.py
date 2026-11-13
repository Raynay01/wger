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
import zoneinfo

# Django
from django.urls import reverse
from django.utils import timezone

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.models import SharingScope
from wger.care.prescription import (
    PrescriptionStatus,
    start_prescription,
)
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.physio.models import (
    PainRecord,
    PhysioProtocol,
    ProtocolExercise,
)


class PhysioTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Test 3: protocols, videos, pain records and functional progress
    """

    def setUp(self):
        super().setUp()
        self.build_team()

    def create_protocol(self):
        self.client.force_authenticate(self.physio)
        response = self.client.post(
            reverse('physio-protocol-list'),
            {
                'name': 'Knee rehab',
                'care_relationship': str(self.physio_rel.pk),
                'pain_during': True,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        protocol_id = response.data['id']
        response = self.client.post(
            reverse('protocol-exercise-list'),
            {
                'protocol': protocol_id,
                'name': 'Quadriceps isometrics',
                'sets': 3,
                'duration_seconds': 30,
                'video_url': 'https://videos.example.com/quad.mp4',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return PhysioProtocol.objects.get(pk=protocol_id)

    def publish(self, protocol):
        self.client.force_authenticate(self.physio)
        response = self.client.post(reverse('physio-protocol-publish', kwargs={'pk': protocol.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        protocol.refresh_from_db()

    def test_patient_sees_published_protocol_with_video(self):
        protocol = self.create_protocol()
        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.get(reverse('physio-protocol-list')).data['count'], 0)

        self.publish(protocol)
        self.client.force_authenticate(self.patient)
        response = self.client.get(reverse('physio-protocol-list'))
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            response.data['results'][0]['pain_moments'],
            ['before', 'during', 'after'],
        )
        exercises = self.client.get(reverse('protocol-exercise-list')).data['results']
        self.assertEqual(exercises[0]['video_url'], 'https://videos.example.com/quad.mp4')

        day = self.client.get(reverse('care-my-day')).data
        self.assertEqual(day['physio']['protocols'][0]['name'], 'Knee rehab')

    def test_only_physio_writes_protocol(self):
        """The trainer and the patient cannot change the physio prescription"""
        protocol = self.create_protocol()
        self.publish(protocol)
        exercise = protocol.exercises.first()
        url = reverse('protocol-exercise-detail', kwargs={'pk': exercise.pk})

        self.client.force_authenticate(self.patient)
        self.assertEqual(
            self.client.patch(url, {'sets': 10}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(self.trainer)
        self.assertEqual(
            self.client.patch(url, {'sets': 10}).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        response = self.client.post(
            reverse('physio-protocol-list'),
            {'name': 'x', 'care_relationship': str(self.training_rel.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_version_copies_exercises(self):
        protocol = self.create_protocol()
        self.publish(protocol)
        response = self.client.post(
            reverse('physio-protocol-new-version', kwargs={'pk': protocol.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        clone = PhysioProtocol.objects.get(pk=response.data['id'])
        self.assertEqual(clone.exercises.get().name, 'Quadriceps isometrics')
        self.assertEqual(protocol.snapshot['exercises'][0]['sets'], 3)

    def test_pain_records_and_alerts(self):
        """The patient records pain, the physiotherapist sees it and gets alerts"""
        protocol = self.create_protocol()
        self.publish(protocol)
        self.client.force_authenticate(self.patient)
        url = reverse('pain-record-list')
        # A fixed time of day, so both records always fall on the same calendar day
        yesterday = timezone.localdate() - datetime.timedelta(days=1)
        now = datetime.datetime.combine(
            yesterday,
            datetime.time(10, 0),
            tzinfo=self.patient.userprofile.zone_info,
        )
        for moment, value, minutes in (('before', 2, 0), ('after', 6, 30)):
            response = self.client.post(
                url,
                {
                    'protocol': str(protocol.pk),
                    'moment': moment,
                    'value': value,
                    'datetime': (now + datetime.timedelta(minutes=minutes)).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response = self.client.post(url, {'moment': 'other', 'value': 11})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(self.physio)
        self.assertEqual(self.client.get(url).data['count'], 2)
        alerts = self.client.get(reverse('pain-record-alerts')).data
        self.assertEqual([a['reason'] for a in alerts], ['increase'])

        self.client.force_authenticate(self.trainer)
        self.assertEqual(self.client.get(url).data['count'], 0)
        self.assertEqual(self.client.get(reverse('pain-record-alerts')).data, [])

    def test_alert_threshold(self):
        protocol = self.create_protocol()
        PainRecord.objects.create(user=self.patient, protocol=protocol, moment='during', value=7)
        PainRecord.objects.create(user=self.patient, protocol=protocol, moment='during', value=6)
        self.client.force_authenticate(self.physio)
        alerts = self.client.get(reverse('pain-record-alerts')).data
        self.assertEqual([(a['value'], a['reason']) for a in alerts], [(7, 'threshold')])

    def test_increase_compares_same_local_day(self):
        """Before and after on different calendar days of the patient are not compared"""
        self.patient.userprofile.time_zone = 'America/Sao_Paulo'
        self.patient.userprofile.save()
        zone = zoneinfo.ZoneInfo('America/Sao_Paulo')
        protocol = self.create_protocol()
        day = timezone.localdate() - datetime.timedelta(days=2)
        PainRecord.objects.create(
            user=self.patient,
            protocol=protocol,
            moment='before',
            value=1,
            datetime=datetime.datetime.combine(day, datetime.time(23, 50), tzinfo=zone),
        )
        PainRecord.objects.create(
            user=self.patient,
            protocol=protocol,
            moment='after',
            value=5,
            datetime=datetime.datetime.combine(
                day + datetime.timedelta(days=1), datetime.time(0, 10), tzinfo=zone
            ),
        )
        self.client.force_authenticate(self.physio)
        self.assertEqual(self.client.get(reverse('pain-record-alerts')).data, [])

    def test_patient_cannot_change_others_records(self):
        record = PainRecord.objects.create(user=self.patient, moment='other', value=3)
        self.client.force_authenticate(self.physio)
        response = self.client.patch(
            reverse('pain-record-detail', kwargs={'pk': record.pk}),
            {'value': 0},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_functional_assessments(self):
        """Assessments by the physiotherapist form the functional progress"""
        self.client.force_authenticate(self.physio)
        url = reverse('functional-assessment-list')
        for date, value in (('2026-01-10', 90), ('2026-02-10', 115)):
            response = self.client.post(
                url,
                {
                    'relationship': str(self.physio_rel.pk),
                    'kind': 'rom',
                    'name': 'Knee flexion',
                    'side': 'right',
                    'value': value,
                    'unit': '°',
                    'date': date,
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.client.force_authenticate(self.patient)
        response = self.client.get(url, {'name': 'Knee flexion'})
        self.assertEqual([r['value'] for r in response.data['results']], ['115.00', '90.00'])
        detail = reverse(
            'functional-assessment-detail', kwargs={'pk': response.data['results'][0]['id']}
        )
        self.assertEqual(
            self.client.patch(detail, {'value': 140}).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(self.trainer)
        self.assertEqual(self.client.get(url).data['count'], 0)
        response = self.client.post(
            url,
            {'relationship': str(self.training_rel.pk), 'kind': 'rom', 'name': 'x'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pain_shared_with_trainer(self):
        """With the patient's permission the trainer sees the pain summary"""
        PainRecord.objects.create(user=self.patient, moment='after', value=4)
        self.grant(self.training_rel, SharingScope.PHYSIO_PAIN)
        self.client.force_authenticate(self.trainer)
        response = self.client.get(
            reverse('care-relationship-shared', kwargs={'pk': self.training_rel.pk})
        )
        self.assertEqual(response.data['data'][SharingScope.PHYSIO_PAIN]['records'], 1)

    def test_self_protocol_is_writable(self):
        protocol = PhysioProtocol.objects.create(user=self.patient, name='Mine')
        self.assertEqual(protocol.status, PrescriptionStatus.PUBLISHED)
        self.assertTrue(protocol.can_be_written_by(self.patient.pk))
        draft = PhysioProtocol(name='Draft')
        start_prescription(draft, self.physio_rel, self.physio)
        draft.save()
        ProtocolExercise.objects.create(protocol=draft, name='Bridge')
        self.assertFalse(draft.can_be_written_by(self.patient.pk))
        self.assertTrue(draft.can_be_written_by(self.physio.pk))

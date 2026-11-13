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
from django.contrib.auth.models import User
from django.urls import reverse

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.deletion import execute_deletion
from wger.care.models import (
    AccessLog,
    CareRelationship,
    DataRequest,
    DataRequestKind,
    DataRequestStatus,
    RelationshipStatus,
    SharingScope,
)
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.nutrition.models import (
    NutritionPlan,
    WaterLog,
)
from wger.physio.models import (
    FunctionalAssessment,
    PainRecord,
)


class ExportTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    The export holds the user's own data and nothing of other patients
    """

    def setUp(self):
        super().setUp()
        self.build_team()
        self.url = reverse('care-my-data')
        plan = NutritionPlan(description='Prescribed for the patient')
        start_prescription(plan, self.nutrition_rel, self.nutritionist)
        plan.save()
        WaterLog.objects.create(user=self.patient, amount_ml=300)
        PainRecord.objects.create(user=self.patient, moment='after', value=4)
        AccessLog.objects.create(
            actor=self.trainer,
            patient=self.patient,
            relationship=self.training_rel,
            resource=SharingScope.PHYSIO_PAIN,
        )

    def test_patient_export(self):
        self.client.force_authenticate(self.patient)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('attachment; filename="dados-rp_patient-', response['Content-Disposition'])
        data = response.data
        self.assertEqual(data['account']['email'], 'rp_patient@example.com')
        self.assertEqual(
            [p['description'] for p in data['nutrition']['NutritionPlan']],
            ['Prescribed for the patient'],
        )
        self.assertEqual(data['nutrition']['WaterLog'][0]['amount_ml'], 300)
        self.assertEqual(data['physio']['PainRecord'][0]['value'], 4)
        self.assertEqual(len(data['care']['professionals']), 3)
        self.assertEqual(
            data['care']['reads_of_your_shared_data'][0]['actor__username'],
            'rp_trainer',
        )
        self.assertTrue(
            DataRequest.objects.filter(
                user=self.patient,
                kind=DataRequestKind.EXPORT,
                status=DataRequestStatus.DONE,
            ).exists()
        )

    def test_professional_export_has_no_patient_data(self):
        """The plan a nutritionist wrote belongs to the patient, not to the nutritionist's export"""
        self.client.force_authenticate(self.nutritionist)
        data = self.client.get(self.url).data
        self.assertEqual(data['nutrition']['NutritionPlan'], [])
        self.assertEqual(data['physio']['PainRecord'], [])
        self.assertEqual(data['care']['professionals'], [])
        self.assertEqual(data['as_professional']['registrations'][0]['council'], 'CRN')


class DeletionTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Deletion requests end the follow-ups and are executed by the platform team
    """

    def setUp(self):
        super().setUp()
        self.build_team()
        self.grant(self.nutrition_rel, SharingScope.TRAINING_SCHEDULE)
        self.url = reverse('data-request-list')

    def request(self, confirm=True):
        self.client.force_authenticate(self.patient)
        return self.client.post(self.url, {'confirm': confirm})

    def test_needs_confirmation(self):
        self.assertEqual(self.request(confirm=False).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(DataRequest.objects.exists())

    def test_request_ends_follow_ups(self):
        response = self.request()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['kind'], DataRequestKind.DELETION)
        self.assertEqual(response.data['status'], DataRequestStatus.PENDING)
        self.assertFalse(
            CareRelationship.objects.filter(patient=self.patient)
            .exclude(status=RelationshipStatus.ENDED)
            .exists()
        )
        self.assertFalse(self.nutrition_rel.grants.filter(revoked_at__isnull=True).exists())

        self.client.force_authenticate(self.nutritionist)
        shared = reverse('care-relationship-shared', kwargs={'pk': self.nutrition_rel.pk})
        self.assertEqual(self.client.get(shared).status_code, status.HTTP_403_FORBIDDEN)

    def test_second_request_returns_the_pending_one(self):
        first = self.request().data['id']
        self.assertEqual(self.request().data['id'], first)
        self.assertEqual(DataRequest.objects.count(), 1)

    def test_cancel(self):
        pk = self.request().data['id']
        url = reverse('data-request-cancel', kwargs={'pk': pk})
        other = self.make_user('rp_other')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_200_OK)
        self.assertEqual(DataRequest.objects.get(pk=pk).status, DataRequestStatus.CANCELLED)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_400_BAD_REQUEST)

    def test_execute_deletes_account_and_keeps_evidence(self):
        pk = self.request().data['id']
        done, reason = execute_deletion(DataRequest.objects.get(pk=pk))
        self.assertTrue(done, reason)
        self.assertFalse(User.objects.filter(username='rp_patient').exists())
        evidence = DataRequest.objects.get(pk=pk)
        self.assertIsNone(evidence.user)
        self.assertEqual(evidence.user_reference, 'rp_patient')
        self.assertEqual(evidence.status, DataRequestStatus.DONE)

    def test_execute_refuses_with_clinical_records(self):
        """Clinical records of professionals block the deletion until clarified"""
        FunctionalAssessment.objects.create(
            relationship=self.physio_rel,
            kind='rom',
            name='Knee flexion',
            value=90,
        )
        pk = self.request().data['id']
        done, reason = execute_deletion(DataRequest.objects.get(pk=pk))
        self.assertFalse(done)
        self.assertIn('functional_assessments', reason)
        self.assertTrue(User.objects.filter(username='rp_patient').exists())
        self.assertEqual(DataRequest.objects.get(pk=pk).status, DataRequestStatus.PENDING)

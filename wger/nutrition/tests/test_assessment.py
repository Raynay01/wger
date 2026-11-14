#  This file is part of wger Workout Manager <https://github.com/wger-project>.
#
#  wger Workout Manager is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  wger Workout Manager is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Django
from django.urls import reverse

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.deletion import (
    execute_deletion,
    request_deletion,
)
from wger.care.export import export_user_data
from wger.care.models import RelationshipStatus
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase


class NutritionalAssessmentTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Anamnesis and anthropometric assessments written by the nutritionist
    """

    payload = {
        'date': '2026-11-10',
        'sex': 'female',
        'age': 30,
        'weight': '65',
        'height': '165',
        'waist': '70',
        'hip': '98',
        'activity_level': 'light',
        'energy_adjustment': -400,
    }

    def setUp(self):
        super().setUp()
        self.build_team()

    def create(self, user=None, **data):
        self.client.force_authenticate(user or self.nutritionist)
        return self.client.post(
            reverse('nutritional-assessment-list'),
            {'relationship': str(self.nutrition_rel.pk), **self.payload, **data},
        )

    def test_energy_needs(self):
        """Mifflin-St Jeor times the activity factor, plus the adjustment, and BMI and WHR"""
        response = self.create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.data
        # 10 * 65 + 6.25 * 165 - 5 * 30 - 161 = 1370.25
        self.assertEqual(data['basal_energy'], 1370)
        # 1370.25 * 1.375 = 1884.1
        self.assertEqual(data['total_energy'], 1884)
        self.assertEqual(data['target_energy'], 1484)
        self.assertEqual(data['bmi'], '23.9')
        self.assertEqual(data['waist_hip_ratio'], '0.71')
        self.assertIsNone(data['lean_mass'])
        self.assertEqual(data['patient'], self.patient.pk)

    def test_male_and_other_equations(self):
        """Harris-Benedict and Katch-McArdle, and the male variant of Mifflin"""
        response = self.create(sex='male')
        # 10 * 65 + 6.25 * 165 - 5 * 30 + 5 = 1536.25
        self.assertEqual(response.data['basal_energy'], 1536)

        response = self.create(equation='harris_benedict')
        # 447.593 + 9.247 * 65 + 3.098 * 165 - 4.330 * 30 = 1429.9
        self.assertEqual(response.data['basal_energy'], 1430)

        response = self.create(equation='katch_mcardle', body_fat='25', waist='', hip='')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # 370 + 21.6 * 48.75 = 1423
        self.assertEqual(response.data['basal_energy'], 1423)
        self.assertEqual(response.data['lean_mass'], '48.8')
        self.assertIsNone(response.data['waist_hip_ratio'])

    def test_katch_mcardle_needs_body_fat(self):
        """Without the body fat the lean mass equation is refused"""
        response = self.create(equation='katch_mcardle')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('body_fat', response.data)

    def test_only_the_nutritionist_writes(self):
        """Other professionals cannot write; the patient reads, others don't see it"""
        response = self.create(user=self.trainer)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('relationship', response.data)

        pk = self.create().data['id']
        url = reverse('nutritional-assessment-detail', kwargs={'pk': pk})

        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.get(url).data['target_energy'], 1484)
        self.assertEqual(
            self.client.patch(url, {'weight': '60'}).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(self.trainer)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.nutritionist)
        response = self.client.patch(url, {'weight': '60'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['basal_energy'], 1320)

    def test_ended_follow_up(self):
        """After the follow-up ends the nutritionist no longer sees it, the patient does"""
        pk = self.create().data['id']
        self.nutrition_rel.status = RelationshipStatus.ENDED
        self.nutrition_rel.save()
        url = reverse('nutritional-assessment-detail', kwargs={'pk': pk})

        self.client.force_authenticate(self.nutritionist)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    def test_anamnesis(self):
        """The anamnesis is written by the nutritionist and read by the patient"""
        self.client.force_authenticate(self.nutritionist)
        response = self.client.post(
            reverse('nutritional-anamnesis-list'),
            {
                'relationship': str(self.nutrition_rel.pk),
                'goal': 'Perder 5 kg',
                'allergies': 'Lactose',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.client.force_authenticate(self.patient)
        results = self.client.get(reverse('nutritional-anamnesis-list')).data['results']
        self.assertEqual([r['allergies'] for r in results], ['Lactose'])

        self.client.force_authenticate(self.physio)
        response = self.client.post(
            reverse('nutritional-anamnesis-list'),
            {'relationship': str(self.physio_rel.pk), 'goal': 'x'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_export_and_deletion(self):
        """The records are exported and block the account deletion"""
        self.create()
        exported = export_user_data(self.patient)['nutrition']
        self.assertEqual([str(a['weight']) for a in exported['NutritionalAssessment']], ['65.00'])

        done, reason = execute_deletion(request_deletion(self.patient))
        self.assertFalse(done)
        self.assertIn('nutritional_assessments', reason)

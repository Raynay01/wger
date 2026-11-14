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
from wger.care.models import (
    RelationshipStatus,
    SharingScope,
)
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
            format='json',
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

        response = self.create(equation='katch_mcardle', body_fat='25', waist=None, hip=None)
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

    def test_skinfolds(self):
        """Jackson-Pollock 3 and 7 and Durnin-Womersley set the body fat by Siri's equation"""
        response = self.create(
            skinfold_protocol='jp3',
            skinfolds={'triceps': 18, 'suprailiac': 15, 'thigh': 25.0, 'chest': 9},
            body_fat='40',
            equation='katch_mcardle',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # Sum 58 mm, density 1.04547, 495 / density - 450 = 23.47
        self.assertEqual(response.data['skinfold_sum'], '58.0')
        self.assertEqual(response.data['body_fat'], '23.5')
        # 370 + 21.6 * 65 * 0.765
        self.assertEqual(response.data['basal_energy'], 1444)

        response = self.create(
            sex='male',
            age=42,
            skinfold_protocol='jp7',
            skinfolds={
                'chest': 10,
                'midaxillary': 12,
                'triceps': 9,
                'subscapular': 14,
                'abdomen': 20,
                'suprailiac': 13,
                'thigh': 15,
            },
        )
        self.assertEqual(response.data['body_fat'], '15.1')

        response = self.create(
            age=35,
            skinfold_protocol='durnin',
            skinfolds={'biceps': 6, 'triceps': 12, 'subscapular': 14, 'suprailiac': 15},
        )
        # Women 30 to 39: density 1.1423 - 0.0632 * log10(47)
        self.assertEqual(response.data['body_fat'], '27.5')

    def test_skinfolds_validation(self):
        """Every site of the protocol is needed; unknown sites and values are refused"""
        response = self.create(skinfold_protocol='jp3', skinfolds={'triceps': 18})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('suprailiac', str(response.data['skinfolds']))

        response = self.create(skinfolds={'nose': 3})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.create(skinfolds={'triceps': 120})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_macros(self):
        """Protein by g/kg, fat by its share of the target, carbohydrates the rest"""
        response = self.create(protein_per_kg='1.6', fat_percent=30)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # 65 * 1.6 = 104 g; 1484 * 0.3 / 9 = 49 g; (1484 - 416 - 441) / 4 = 157 g
        self.assertEqual(
            response.data['macros'],
            {'protein': 104, 'carbohydrates': 157, 'fat': 49},
        )
        self.assertIsNone(self.create().data['macros'])

    def test_shared_with_the_trainer(self):
        """With the body measurements scope the trainer sees the anthropometry, not the rest"""
        self.create(notes='Paciente relata compulsão à noite', body_fat='24')
        url = reverse('care-relationship-shared', kwargs={'pk': self.training_rel.pk})

        self.client.force_authenticate(self.trainer)
        self.assertNotIn(SharingScope.BODY_MEASUREMENTS, self.client.get(url).data['scopes'])

        self.grant(self.training_rel, SharingScope.BODY_MEASUREMENTS)
        data = self.client.get(url).data['data'][SharingScope.BODY_MEASUREMENTS]
        [entry] = data['anthropometry']
        self.assertEqual(str(entry['weight']), '65.00')
        self.assertEqual(str(entry['bmi']), '23.9')
        self.assertEqual(str(entry['body_fat']), '24.0')
        self.assertNotIn('notes', entry)
        self.assertNotIn('target_energy', entry)

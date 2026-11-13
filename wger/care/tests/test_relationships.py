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
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.disciplines import Discipline
from wger.care.models import (
    AccessGrant,
    CareRelationship,
    ConsentKind,
    ConsentRecord,
    Membership,
    MembershipRole,
    RelationshipStatus,
    SharingScope,
)
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase


class InvitationTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Inviting patients and accepting, declining and ending relationships
    """

    def setUp(self):
        super().setUp()
        self.nutritionist = self.make_professional('rp_nutri', Discipline.NUTRITION)
        self.organization = self.nutritionist.care_memberships.first().organization
        self.patient = self.make_user('rp_patient')
        self.url = reverse('care-relationship-list')

    def invite(self, discipline=Discipline.NUTRITION, email='rp_patient@example.com'):
        self.client.force_authenticate(self.nutritionist)
        return self.client.post(
            self.url,
            {
                'organization': str(self.organization.pk),
                'discipline': discipline,
                'invited_email': email,
            },
        )

    def test_invite_and_accept(self):
        """The patient accepts with consent, which is recorded, and the relationship is active"""
        response = self.invite()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], RelationshipStatus.INVITED)
        self.assertIsNotNone(response.data['invitation_token'])
        pk = response.data['id']

        self.client.force_authenticate(self.patient)
        listing = self.client.get(self.url)
        self.assertEqual([r['id'] for r in listing.data['results']], [pk])
        self.assertIsNone(listing.data['results'][0]['invitation_token'])

        url = reverse('care-relationship-accept', kwargs={'pk': pk})
        self.assertEqual(
            self.client.post(url, {'accept_terms': False}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        response = self.client.post(url, {'accept_terms': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        relationship = CareRelationship.objects.get(pk=pk)
        self.assertEqual(relationship.status, RelationshipStatus.ACTIVE)
        self.assertEqual(relationship.patient, self.patient)
        self.assertTrue(
            ConsentRecord.objects.filter(
                user=self.patient,
                kind=ConsentKind.CARE_RELATIONSHIP,
                reference=pk,
            ).exists()
        )

    def test_other_user_cannot_accept(self):
        """An invitation for another email address cannot be accepted"""
        pk = self.invite().data['id']
        other = self.make_user('rp_other')
        self.client.force_authenticate(other)
        response = self.client.post(
            reverse('care-relationship-accept', kwargs={'pk': pk}),
            {'accept_terms': True},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_accept_with_token(self):
        """The token of the invitation link lets a user with another email accept"""
        response = self.invite()
        pk, token = response.data['id'], response.data['invitation_token']
        other = self.make_user('rp_other')
        self.client.force_authenticate(other)
        url = reverse('care-relationship-accept', kwargs={'pk': pk})

        wrong = '00000000-0000-0000-0000-000000000000'
        response = self.client.post(url, {'accept_terms': True, 'token': wrong})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.post(url, {'accept_terms': True, 'token': token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CareRelationship.objects.get(pk=pk).patient, other)

    def test_needs_registration(self):
        """A nutritionist cannot follow patients in training without a CREF registration"""
        response = self.invite(discipline=Discipline.TRAINING)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('discipline', response.data)

    def test_needs_membership(self):
        """Professionals only invite in organizations where they follow patients"""
        Membership.objects.filter(user=self.nutritionist).update(role=MembershipRole.RECEPTION)
        response = self.invite()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('organization', response.data)

    def test_no_duplicate_invitation(self):
        """A second invitation to the same patient and discipline is refused"""
        self.assertEqual(self.invite().status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.invite().status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(self.patient)
        relationship = CareRelationship.objects.get()
        relationship.patient = self.patient
        relationship.status = RelationshipStatus.ACTIVE
        relationship.save()
        self.assertEqual(
            self.invite(email='RP_PATIENT@example.com').status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_decline(self):
        pk = self.invite().data['id']
        self.client.force_authenticate(self.patient)
        response = self.client.post(reverse('care-relationship-decline', kwargs={'pk': pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CareRelationship.objects.get(pk=pk).status, RelationshipStatus.ENDED)

    def test_end_revokes_grants(self):
        """Ending a relationship stops the sharing at once"""
        relationship = self.follow(self.nutritionist, self.patient, Discipline.NUTRITION)
        grant = self.grant(relationship, SharingScope.TRAINING_SCHEDULE)

        self.client.force_authenticate(self.patient)
        response = self.client.post(
            reverse('care-relationship-end', kwargs={'pk': relationship.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        grant.refresh_from_db()
        self.assertIsNotNone(grant.revoked_at)

    def test_only_professional_pauses(self):
        relationship = self.follow(self.nutritionist, self.patient, Discipline.NUTRITION)
        url = reverse('care-relationship-pause', kwargs={'pk': relationship.pk})
        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.nutritionist)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_200_OK)
        relationship.refresh_from_db()
        self.assertEqual(relationship.status, RelationshipStatus.PAUSED)


@override_settings(WEB_APP_URL='https://app.example.com/', WEB_APP_NAME='Kinutri')
class InvitationEmailTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    The invitation email goes out only when the professional sends it
    """

    def setUp(self):
        super().setUp()
        self.nutritionist = self.make_professional('rp_nutri', Discipline.NUTRITION)
        self.organization = self.nutritionist.care_memberships.first().organization
        self.client.force_authenticate(self.nutritionist)
        response = self.client.post(
            reverse('care-relationship-list'),
            {
                'organization': str(self.organization.pk),
                'discipline': Discipline.NUTRITION,
                'invited_email': 'new.patient@example.com',
            },
        )
        self.relationship = CareRelationship.objects.get(pk=response.data['id'])
        self.send_url = reverse('care-relationship-send-email', kwargs={'pk': self.relationship.pk})

    def test_creating_sends_nothing(self):
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(self.relationship.invitation_sent_at)

    def test_send_contains_link_with_token(self):
        response = self.client.post(self.send_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['invitation_sent_at'])
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['new.patient@example.com'])
        self.assertIn('Kinutri', message.subject)
        self.assertIn(
            f'https://app.example.com/convite/{self.relationship.pk}'
            f'?token={self.relationship.invitation_token}',
            message.body,
        )

    def test_resend_waits(self):
        """A second email right away is refused, after ten minutes it goes out"""
        self.assertEqual(self.client.post(self.send_url).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post(self.send_url).status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        CareRelationship.objects.filter(pk=self.relationship.pk).update(
            invitation_sent_at=timezone.now() - datetime.timedelta(minutes=10)
        )
        self.assertEqual(self.client.post(self.send_url).status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 2)

    def test_only_the_professional_sends(self):
        other = self.make_professional('rp_other_nutri', Discipline.NUTRITION)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(self.send_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(len(mail.outbox), 0)

    def test_not_for_closed_invitations(self):
        self.relationship.status = RelationshipStatus.ENDED
        self.relationship.save()
        self.assertEqual(self.client.post(self.send_url).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(WEB_APP_URL='')
    def test_without_web_app_no_link(self):
        self.assertEqual(self.client.post(self.send_url).status_code, status.HTTP_200_OK)
        self.assertNotIn('token=', mail.outbox[0].body)
        self.assertIn('new.patient@example.com', mail.outbox[0].body)


class OrganizationTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    Organizations and their members
    """

    def setUp(self):
        super().setUp()
        self.owner = self.make_user('rp_owner')
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse('organization-list'), {'name': 'Clinic', 'kind': 'clinic'}
        )
        self.organization_id = response.data['id']

    def test_creator_is_owner(self):
        response = self.client.get(reverse('organization-list'))
        self.assertEqual(response.data['results'][0]['my_role'], MembershipRole.OWNER)

    def test_add_member_and_keep_owner(self):
        """Owners add members by email, and the last owner cannot be removed"""
        colleague = self.make_user('rp_colleague')
        response = self.client.post(
            reverse('membership-list'),
            {
                'organization': self.organization_id,
                'email': colleague.email,
                'role': MembershipRole.PROFESSIONAL,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        own = Membership.objects.get(user=self.owner)
        response = self.client.delete(reverse('membership-detail', kwargs={'pk': own.pk}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_professional_cannot_manage(self):
        colleague = self.make_user('rp_colleague')
        Membership.objects.create(
            organization_id=self.organization_id,
            user=colleague,
            role=MembershipRole.PROFESSIONAL,
        )
        self.client.force_authenticate(colleague)
        response = self.client.patch(
            reverse('organization-detail', kwargs={'pk': self.organization_id}),
            {'name': 'Mine now'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_outsider_sees_nothing(self):
        self.client.force_authenticate(self.make_user('rp_outsider'))
        self.assertEqual(self.client.get(reverse('organization-list')).data['count'], 0)
        self.assertEqual(self.client.get(reverse('membership-list')).data['count'], 0)


class RegistrationTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    def test_council_follows_discipline(self):
        """The council is derived from the discipline and a change resets the verification"""
        user = self.make_user('rp_pro')
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse('professional-registration-list'),
            {'discipline': Discipline.PHYSIO, 'number': '999', 'region': 'rj'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['council'], 'CREFITO')
        self.assertEqual(response.data['region'], 'RJ')
        self.assertEqual(response.data['status'], 'pending')


class GrantTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    def setUp(self):
        super().setUp()
        self.build_team()

    def test_patient_grants_and_revokes(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post(
            reverse('access-grant-list'),
            {'relationship': str(self.nutrition_rel.pk), 'scope': SharingScope.TRAINING_SCHEDULE},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        grant_id = response.data['id']

        response = self.client.delete(reverse('access-grant-detail', kwargs={'pk': grant_id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNotNone(AccessGrant.objects.get(pk=grant_id).revoked_at)

    def test_professional_cannot_grant_himself(self):
        self.client.force_authenticate(self.nutritionist)
        response = self.client.post(
            reverse('access-grant-list'),
            {'relationship': str(self.nutrition_rel.pk), 'scope': SharingScope.TRAINING_SCHEDULE},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

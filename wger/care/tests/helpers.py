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
from django.utils import timezone

# wger
from wger.care.disciplines import (
    COUNCIL_BY_DISCIPLINE,
    Discipline,
)
from wger.care.models import (
    AccessGrant,
    CareRelationship,
    Membership,
    MembershipRole,
    Organization,
    ProfessionalRegistration,
    RelationshipStatus,
)


class CareScenarioMixin:
    """
    Builds professionals and patients with accepted care relationships
    """

    def make_user(self, username: str) -> User:
        return User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password=f'{username}{username}',
        )

    def make_professional(self, username: str, *disciplines: str) -> User:
        user = self.make_user(username)
        organization = Organization.objects.create(name=f'{username} org')
        Membership.objects.create(organization=organization, user=user, role=MembershipRole.OWNER)
        for discipline in disciplines:
            ProfessionalRegistration.objects.create(
                user=user,
                discipline=discipline,
                council=COUNCIL_BY_DISCIPLINE[discipline],
                number='12345',
                region='SP',
            )
        return user

    def follow(self, professional: User, patient: User, discipline: str) -> CareRelationship:
        return CareRelationship.objects.create(
            organization=professional.care_memberships.first().organization,
            professional=professional,
            patient=patient,
            discipline=discipline,
            status=RelationshipStatus.ACTIVE,
            invited_email=patient.email,
            started=timezone.now(),
        )

    def grant(self, relationship: CareRelationship, scope: str) -> AccessGrant:
        return AccessGrant.objects.create(relationship=relationship, scope=scope)

    def build_team(self):
        """A patient followed in all three disciplines"""
        self.trainer = self.make_professional('rp_trainer', Discipline.TRAINING)
        self.physio = self.make_professional('rp_physio', Discipline.PHYSIO)
        self.nutritionist = self.make_professional('rp_nutritionist', Discipline.NUTRITION)
        self.patient = self.make_user('rp_patient')
        self.training_rel = self.follow(self.trainer, self.patient, Discipline.TRAINING)
        self.physio_rel = self.follow(self.physio, self.patient, Discipline.PHYSIO)
        self.nutrition_rel = self.follow(self.nutritionist, self.patient, Discipline.NUTRITION)

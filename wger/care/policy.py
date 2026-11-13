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

"""
Single place for the access rules between professionals and patients
"""

# Django
from django.contrib.auth.models import User

# wger
from wger.care.disciplines import Discipline
from wger.care.models import (
    CARING_ROLES,
    MANAGING_ROLES,
    OPEN_STATUSES,
    AccessLog,
    CareRelationship,
    Membership,
    Organization,
    ProfessionalRegistration,
    SharingScope,
    VerificationStatus,
)


SELF_MANAGED_MODULES = [Discipline.TRAINING.value, Discipline.NUTRITION.value]
"""Modules of a user who is not followed by any professional"""


def is_caring_member(user: User, organization: Organization) -> bool:
    """Whether the user can follow patients in the organization"""
    return Membership.objects.filter(
        organization=organization,
        user=user,
        is_active=True,
        role__in=CARING_ROLES,
        organization__is_active=True,
    ).exists()


def is_managing_member(user: User, organization: Organization) -> bool:
    """Whether the user can change the organization and its members"""
    return Membership.objects.filter(
        organization=organization,
        user=user,
        is_active=True,
        role__in=MANAGING_ROLES,
    ).exists()


def has_registration(user: User, discipline: str) -> bool:
    """Whether the user has a council registration for the discipline that was not rejected"""
    return (
        ProfessionalRegistration.objects.filter(user=user, discipline=discipline)
        .exclude(status=VerificationStatus.REJECTED)
        .exists()
    )


def open_relationships(patient: User):
    return CareRelationship.objects.filter(patient=patient, status__in=OPEN_STATUSES)


def patient_modules(patient: User) -> dict:
    """
    The modules a patient sees

    Followed patients see the modules of their professionals only, so a
    nutrition-only patient never gets a training area. Users without
    professionals keep the self-managed training and nutrition modules.
    """
    disciplines = set(open_relationships(patient).values_list('discipline', flat=True))
    if disciplines:
        modules = [d.value for d in Discipline if d.value in disciplines]
        mode = 'guided'
    else:
        modules = list(SELF_MANAGED_MODULES)
        mode = 'self'

    return {
        'mode': mode,
        'modules': modules,
        'combined_view': Discipline.TRAINING in modules and Discipline.NUTRITION in modules,
    }


def active_scopes(relationship: CareRelationship) -> set[str]:
    """The scopes the patient currently shares with the professional of a relationship"""
    if not relationship.is_open:
        return set()
    return set(relationship.grants.filter(revoked_at__isnull=True).values_list('scope', flat=True))


def professional_relationship(
    professional: User,
    patient: User,
    discipline: str | None = None,
) -> CareRelationship | None:
    """An open relationship of the professional with the patient"""
    qs = CareRelationship.objects.filter(
        professional=professional,
        patient=patient,
        status__in=OPEN_STATUSES,
    )
    if discipline:
        qs = qs.filter(discipline=discipline)
    return qs.first()


def can_read_notes(user: User, relationship: CareRelationship) -> bool:
    """Whether the professional of a relationship may read the notes of the other ones"""
    return SharingScope.NOTES in active_scopes(relationship)


def log_access(actor: User, relationship: CareRelationship, resource: str) -> None:
    AccessLog.objects.create(
        actor=actor,
        patient_id=relationship.patient_id,
        relationship=relationship,
        resource=resource,
    )

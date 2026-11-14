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
Account deletion on request of the data subject (LGPD art. 18)

The request ends the follow-ups at once, so no professional reads the data
anymore. The platform admin then deletes the account, unless professionals
keep clinical records about the person, whose retention has to be clarified
with them first.
"""

# Django
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

# wger
from wger.care.models import (
    PENDING_STATUSES,
    AccessGrant,
    CareRelationship,
    DataRequest,
    DataRequestKind,
    DataRequestStatus,
    MultidisciplinaryNote,
    RelationshipStatus,
)


@transaction.atomic
def request_deletion(user: User) -> DataRequest:
    """Records the request and ends the user's follow-ups as a patient"""
    pending = DataRequest.objects.filter(
        user=user,
        kind=DataRequestKind.DELETION,
        status=DataRequestStatus.PENDING,
    ).first()
    if pending is not None:
        return pending

    now = timezone.now()
    relationships = CareRelationship.objects.filter(patient=user, status__in=PENDING_STATUSES)
    AccessGrant.objects.filter(relationship__in=relationships, revoked_at__isnull=True).update(
        revoked_at=now
    )
    relationships.update(status=RelationshipStatus.ENDED, ended=now)

    return DataRequest.objects.create(
        user=user,
        user_reference=user.username,
        kind=DataRequestKind.DELETION,
    )


def clinical_records(user: User) -> dict[str, int]:
    """Records professionals wrote about the user, which may have to be kept"""
    # wger
    from wger.nutrition.models import (
        NutritionalAnamnesis,
        NutritionalAssessment,
    )
    from wger.physio.models import FunctionalAssessment

    counts = {
        'functional_assessments': FunctionalAssessment.objects.filter(
            relationship__patient=user
        ).count(),
        'nutritional_anamneses': NutritionalAnamnesis.objects.filter(
            relationship__patient=user
        ).count(),
        'nutritional_assessments': NutritionalAssessment.objects.filter(
            relationship__patient=user
        ).count(),
        'notes': MultidisciplinaryNote.objects.filter(relationship__patient=user).count(),
    }
    return {key: value for key, value in counts.items() if value}


@transaction.atomic
def execute_deletion(data_request: DataRequest) -> tuple[bool, str]:
    """
    Deletes the account of a pending deletion request. Refuses while
    professionals hold clinical records about the person.
    """
    if (
        data_request.kind != DataRequestKind.DELETION
        or data_request.status != DataRequestStatus.PENDING
    ):
        return False, 'Not a pending deletion request'

    user = data_request.user
    if user is not None:
        records = clinical_records(user)
        if records:
            summary = ', '.join(f'{count} {name}' for name, count in records.items())
            return False, f'Clinical records of professionals exist ({summary})'
        user.delete()

    data_request.refresh_from_db()
    data_request.status = DataRequestStatus.DONE
    data_request.completed_at = timezone.now()
    data_request.save()
    return True, ''

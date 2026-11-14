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
Whether a patient gets achievements and streaks

The patient turns them off in the profile, any professional of an open
follow-up for the patient, and training achievements are suspended while
there is recent pain at or above the alert threshold of a physio protocol.
"""

# Standard Library
import datetime

# Django
from django.contrib.auth.models import User
from django.db.models import F
from django.utils import timezone

# wger
from wger.care.models import (
    OPEN_STATUSES,
    CareRelationship,
)


PAIN_DAYS = 14


class Reason:
    PATIENT = 'patient'
    PROFESSIONAL = 'professional'
    PAIN = 'pain'


def _disabled_by(user: User) -> list[str]:
    relationships = CareRelationship.objects.filter(
        patient=user,
        status__in=OPEN_STATUSES,
        gamification_enabled=False,
    ).select_related('professional')
    return [r.professional.get_full_name() or r.professional.username for r in relationships]


def _pain_since(user: User) -> datetime.datetime | None:
    """The latest pain record of the last days at the alert threshold of its protocol"""
    # wger
    from wger.physio.models import PainRecord

    record = (
        PainRecord.objects.filter(
            user=user,
            protocol__isnull=False,
            datetime__gte=timezone.now() - datetime.timedelta(days=PAIN_DAYS),
            value__gte=F('protocol__pain_alert_threshold'),
        )
        .order_by('-datetime')
        .first()
    )
    return record.datetime if record else None


def gamification_status(user: User) -> dict:
    """On or off, and why it is off"""
    out = {'enabled': True, 'reason': None, 'disabled_by': [], 'pain_until': None}
    if not user.userprofile.trophies_enabled:
        return {**out, 'enabled': False, 'reason': Reason.PATIENT}
    disabled_by = _disabled_by(user)
    if disabled_by:
        return {**out, 'enabled': False, 'reason': Reason.PROFESSIONAL, 'disabled_by': disabled_by}
    pain = _pain_since(user)
    if pain:
        return {
            **out,
            'enabled': False,
            'reason': Reason.PAIN,
            'pain_until': pain + datetime.timedelta(days=PAIN_DAYS),
        }
    return out


def trophies_blocked(user: User) -> bool:
    """Whether trophy evaluation is off for a reason outside the trophies app"""
    return not gamification_status(user)['enabled']

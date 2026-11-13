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
Pain alerts for the physiotherapist
"""

# Standard Library
import datetime

# Django
from django.contrib.auth.models import User
from django.utils import timezone

# wger
from wger.care.disciplines import Discipline
from wger.care.models import (
    OPEN_STATUSES,
    CareRelationship,
)
from wger.physio.models import (
    PainMoment,
    PainRecord,
)


ALERT_DAYS = 14


def pain_alerts(professional: User) -> list[dict]:
    """
    Recent pain records of followed patients that reach the threshold of their
    protocol, or that rose by the protocol's increase from before to after the
    exercises on the same day
    """
    patients = CareRelationship.objects.filter(
        professional=professional,
        discipline=Discipline.PHYSIO,
        status__in=OPEN_STATUSES,
    ).values('patient')
    records = (
        PainRecord.objects.filter(
            user__in=patients,
            protocol__isnull=False,
            datetime__gte=timezone.now() - datetime.timedelta(days=ALERT_DAYS),
        )
        .select_related('protocol', 'user__userprofile')
        .order_by('datetime')
    )

    alerts = []
    before = {}
    for record in records:
        zone = record.user.userprofile.zone_info
        key = (record.user_id, record.protocol_id, timezone.localtime(record.datetime, zone).date())
        if record.moment == PainMoment.BEFORE:
            before[key] = record.value

        reason = None
        if record.value >= record.protocol.pain_alert_threshold:
            reason = 'threshold'
        elif (
            record.moment == PainMoment.AFTER
            and key in before
            and record.value - before[key] >= record.protocol.pain_alert_increase
        ):
            reason = 'increase'

        if reason:
            alerts.append(
                {
                    'patient': record.user_id,
                    'record': record.pk,
                    'datetime': record.datetime,
                    'value': record.value,
                    'reason': reason,
                }
            )
    alerts.reverse()
    return alerts

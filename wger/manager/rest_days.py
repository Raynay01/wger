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
from django.contrib.auth.models import User

# wger
from wger.care.prescription import PrescriptionStatus
from wger.manager.models import Routine


def prescribed_rest_days(user: User, start: datetime.date, end: datetime.date) -> set:
    """Rest days of the user's published routines between start and end"""
    out = set()
    if end < start:
        return out
    routines = Routine.objects.filter(
        user=user,
        is_template=False,
        status=PrescriptionStatus.PUBLISHED,
        start__lte=end,
        end__gte=start,
    )
    for routine in routines:
        for entry in routine.date_sequence:
            if start <= entry.date <= end and entry.day is not None and entry.day.is_rest:
                out.add(entry.date)
    return out


def only_rest_between(rest_days: set, first: datetime.date, last: datetime.date) -> bool:
    """Whether every day strictly between first and last is a rest day"""
    day = first + datetime.timedelta(days=1)
    while day < last:
        if day not in rest_days:
            return False
        day += datetime.timedelta(days=1)
    return True

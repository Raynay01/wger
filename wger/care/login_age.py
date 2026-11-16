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
Maximum login age of professionals (CARE_PROFESSIONAL_LOGIN_DAYS)

Counted from the login recorded by allauth in the session, which also backs
the tokens of the app client, so refreshing the token does not extend it.
"""

# Standard Library
import time

# Django
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.backends.base import SessionBase

# Third Party
from allauth.account.authentication import AUTHENTICATION_METHODS_SESSION_KEY

# wger
from wger.care.mfa import is_professional


# Start of the count for sessions from before this check, without records
FIRST_SEEN = 'care_login_first_seen'


def login_started(session: SessionBase) -> float:
    records = session.get(AUTHENTICATION_METHODS_SESSION_KEY)
    times = [
        record['at']
        for record in records or []
        if isinstance(record, dict) and isinstance(record.get('at'), (int, float))
    ]
    if times:
        return min(times)
    return session.setdefault(FIRST_SEEN, time.time())


def login_expired(user: User, session: SessionBase) -> bool:
    days = settings.CARE_PROFESSIONAL_LOGIN_DAYS
    if not days or not user.is_authenticated or not is_professional(user):
        return False
    return time.time() - login_started(session) > days * 24 * 3600

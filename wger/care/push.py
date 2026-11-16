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
Push notices through Firebase Cloud Messaging (HTTP v1 API)

Off while FCM_PROJECT_ID or FCM_SERVICE_ACCOUNT_FILE is empty. The service
account signs a JWT (RS256) that Google exchanges for an access token. The
notices pass through Google, so they carry the same text as the emails: no
health data. Device tokens are never logged.
"""

# Standard Library
import json
import logging
import time

# Django
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache

# Third Party
import jwt
import requests

# wger
from wger.care.models import PushDevice


logger = logging.getLogger(__name__)

TOKEN_URL = 'https://oauth2.googleapis.com/token'
SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
ACCESS_TOKEN_CACHE_KEY = 'care-fcm-access-token'
TIMEOUT = 15


def enabled() -> bool:
    return bool(settings.FCM_PROJECT_ID and settings.FCM_SERVICE_ACCOUNT_FILE)


def _access_token() -> str:
    token = cache.get(ACCESS_TOKEN_CACHE_KEY)
    if token:
        return token
    with open(settings.FCM_SERVICE_ACCOUNT_FILE, encoding='utf-8') as handle:
        account = json.load(handle)
    token_url = account.get('token_uri', TOKEN_URL)
    now = int(time.time())
    assertion = jwt.encode(
        {
            'iss': account['client_email'],
            'scope': SCOPE,
            'aud': token_url,
            'iat': now,
            'exp': now + 3600,
        },
        account['private_key'],
        algorithm='RS256',
    )
    response = requests.post(
        token_url,
        data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': assertion},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    cache.set(
        ACCESS_TOKEN_CACHE_KEY, data['access_token'], max(data.get('expires_in', 3600) - 300, 60)
    )
    return data['access_token']


def _unregistered(response: requests.Response) -> bool:
    """FCM's answer for a token of an uninstalled app or a malformed token"""
    if response.status_code == 404:
        return True
    try:
        details = response.json()['error'].get('details', [])
    except (ValueError, KeyError, AttributeError):
        return False
    return any(d.get('errorCode') in ('UNREGISTERED', 'INVALID_ARGUMENT') for d in details)


def send(user: User, title: str, body: str, path: str) -> int:
    """Sends a notice to every device of the user. Returns how many got it."""
    if not enabled():
        return 0
    devices = list(PushDevice.objects.filter(user=user))
    if not devices:
        return 0
    try:
        token = _access_token()
    except Exception as error:
        logger.warning('No access token for push notices: %s', type(error).__name__)
        return 0

    url = f'https://fcm.googleapis.com/v1/projects/{settings.FCM_PROJECT_ID}/messages:send'
    delivered = 0
    for device in devices:
        message = {
            'message': {
                'token': device.token,
                'notification': {'title': title, 'body': body},
                'data': {'path': path},
                'android': {'priority': 'high'},
                'apns': {'payload': {'aps': {'sound': 'default'}}},
            }
        }
        try:
            response = requests.post(
                url,
                json=message,
                headers={'Authorization': f'Bearer {token}'},
                timeout=TIMEOUT,
            )
        except requests.RequestException as error:
            logger.warning('Push notice to device %s failed: %s', device.pk, type(error).__name__)
            continue
        if response.status_code == 200:
            delivered += 1
        elif _unregistered(response):
            device.delete()
        else:
            logger.warning('Push notice to device %s refused: %s', device.pk, response.status_code)
    return delivered

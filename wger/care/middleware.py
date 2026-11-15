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
from django.conf import settings
from django.http import JsonResponse
from django.urls import resolve
from django.urls.exceptions import Resolver404
from django.utils.translation import gettext as _

# Third Party
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.settings import api_settings

# wger
from wger.care import mfa


# What a professional without a second step can still use: set it up, and
# the organization and council registration that make the account a professional one
OPEN_ROUTES = {
    'care-mfa',
    'care-mfa-qr',
    'organization-list',
    'organization-detail',
    'professional-registration-list',
    'professional-registration-detail',
}


class ProfessionalMFAMiddleware:
    """
    Refuses API requests of professional accounts without two-step
    verification (CARE_PROFESSIONAL_MFA), whatever the authentication: session,
    JWT, API key or OIDC token
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.CARE_PROFESSIONAL_MFA and request.path_info.startswith('/api/'):
            blocked = self._blocked(request)
            if blocked:
                return blocked
        return self.get_response(request)

    def _blocked(self, request):
        try:
            if resolve(request.path_info).url_name in OPEN_ROUTES:
                return None
        except Resolver404:
            return None
        drf_request = Request(
            request,
            authenticators=[cls() for cls in api_settings.DEFAULT_AUTHENTICATION_CLASSES],
        )
        try:
            user = drf_request.user
        except APIException:
            # The view answers invalid credentials itself
            return None
        if not mfa.mfa_required(user):
            return None
        return JsonResponse(
            {
                'detail': _('Turn on two-step verification to use the professional area.'),
                'code': 'mfa_required',
            },
            status=403,
        )

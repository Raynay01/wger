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
Two-step verification for professionals

With CARE_PROFESSIONAL_MFA, an account with an active membership in an
organization needs an authenticator app (or a security key) before the API
answers it, except for the steps to set one up.
"""

# Django
from django.conf import settings
from django.contrib.auth.models import User

# Third Party
import qrcode
import qrcode.image.svg
from allauth.mfa.models import Authenticator
from allauth.mfa.utils import is_mfa_enabled

# wger
from wger.care.models import Membership


def is_professional(user: User) -> bool:
    return Membership.objects.filter(user=user, is_active=True).exists()


def mfa_enabled(user: User) -> bool:
    return is_mfa_enabled(user, [Authenticator.Type.TOTP, Authenticator.Type.WEBAUTHN])


def mfa_required(user: User) -> bool:
    """Whether the account is a professional one still without a second step"""
    return (
        settings.CARE_PROFESSIONAL_MFA
        and user.is_authenticated
        and is_professional(user)
        and not mfa_enabled(user)
    )


def qr_svg(url: str) -> str:
    """The QR code of an otpauth:// URL as SVG, for the authenticator app"""
    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    return image.to_string(encoding='unicode')

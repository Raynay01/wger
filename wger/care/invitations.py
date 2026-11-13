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
Invitation emails for care relationships
"""

# Standard Library
import logging

# Django
from django.conf import settings
from django.core import mail
from django.template import loader
from django.utils import timezone
from django.utils.translation import (
    gettext as _,
    gettext_lazy,
)

# wger
from wger.care.models import (
    CareRelationship,
    RelationshipStatus,
)


logger = logging.getLogger(__name__)

PROFESSIONS = {
    'training': gettext_lazy('Personal trainer'),
    'physio': gettext_lazy('Physiotherapist'),
    'nutrition': gettext_lazy('Nutritionist'),
}

RESEND_AFTER_MINUTES = 10
"""Minimum time between two emails of the same invitation"""


def invitation_link(relationship: CareRelationship) -> str:
    """Link of the web app that accepts the invitation, empty without a web app"""
    base = settings.WEB_APP_URL.rstrip('/')
    if not base:
        return ''
    return f'{base}/convite/{relationship.pk}?token={relationship.invitation_token}'


def can_resend(relationship: CareRelationship) -> bool:
    if relationship.status != RelationshipStatus.INVITED or not relationship.invited_email:
        return False
    if relationship.invitation_sent_at is None:
        return True
    elapsed = timezone.now() - relationship.invitation_sent_at
    return elapsed.total_seconds() >= RESEND_AFTER_MINUTES * 60


def send_invitation(relationship: CareRelationship) -> bool:
    """
    Emails the invitation to the invited address. Returns whether it went out.
    """
    professional = relationship.professional
    context = {
        'professional': professional.get_full_name() or professional.username,
        'profession': PROFESSIONS.get(relationship.discipline, ''),
        'organization': relationship.organization.name,
        'discipline': relationship.get_discipline_display().lower(),
        'app': settings.WEB_APP_NAME,
        'link': invitation_link(relationship),
        'email': relationship.invited_email,
    }
    subject = _('%(professional)s invited you to %(app)s') % {
        'professional': context['professional'],
        'app': settings.WEB_APP_NAME,
    }
    body = loader.render_to_string('care/email_invitation.tpl', context)
    try:
        mail.send_mail(
            subject,
            body,
            settings.WGER_SETTINGS['EMAIL_FROM'],
            [relationship.invited_email],
        )
    except Exception as error:
        # Only the type: details could contain the address or the link with the token
        logger.warning(
            'Could not send the invitation email of relationship %s: %s',
            relationship.pk,
            type(error).__name__,
        )
        return False

    relationship.invitation_sent_at = timezone.now()
    relationship.save(update_fields=['invitation_sent_at'])
    return True

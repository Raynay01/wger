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
Notices by email outside the app: unread messages, published plans and
appointments

The emails carry no health data, not even the area of the follow-up: only that
there is something new, the time of an appointment and a link to the app.
"""

# Standard Library
import datetime
import logging

# Django
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.db.models import Max
from django.template import loader
from django.utils import (
    timezone,
    translation,
)
from django.utils.translation import gettext as _

# wger
from wger.care import push
from wger.care.models import (
    Appointment,
    CareRelationship,
    Message,
    NotificationKind,
    NotificationLog,
    NotificationPreference,
)


logger = logging.getLogger(__name__)

# An unread message waits this long, so a conversation going on in the app sends no email
MESSAGE_DELAY = datetime.timedelta(minutes=5)

# At most one email about new messages per conversation in this time
MESSAGE_INTERVAL = datetime.timedelta(hours=1)

PREFERENCE_SUFFIX = {
    NotificationKind.MESSAGES: 'messages',
    NotificationKind.PRESCRIPTION: 'prescriptions',
    NotificationKind.APPOINTMENT: 'appointments',
}


def preferences(user: User) -> NotificationPreference:
    """The user's choices, the defaults (all on) while they never changed them"""
    return NotificationPreference.objects.filter(user=user).first() or NotificationPreference(
        user=user
    )


def _channels(user: User, kind: str) -> list[str]:
    """The channels the user wants and can be reached on for this kind of notice"""
    choices = preferences(user)
    suffix = PREFERENCE_SUFFIX[kind]
    channels = []
    if user.email and getattr(choices, f'email_{suffix}'):
        channels.append('email')
    if getattr(choices, f'push_{suffix}') and push.enabled() and user.care_push_devices.exists():
        channels.append('push')
    return channels


def wants(user: User, kind: str) -> bool:
    return bool(_channels(user, kind))


def _link(path: str) -> str:
    return f'{settings.WEB_APP_URL.rstrip("/")}{path}' if settings.WEB_APP_URL else ''


def _email(user: User, kind: str, subject: str, text: str, path: str) -> bool:
    context = {'text': text, 'link': _link(path), 'app': settings.WEB_APP_NAME}
    body = loader.render_to_string('care/email_notice.tpl', context)
    try:
        mail.send_mail(
            f'{settings.WEB_APP_NAME}: {subject}',
            body,
            settings.WGER_SETTINGS['EMAIL_FROM'],
            [user.email],
        )
    except Exception as error:
        logger.warning(
            'Could not send a %s notice to user %s: %s', kind, user.pk, type(error).__name__
        )
        return False
    return True


def _send(
    user: User,
    kind: str,
    reference: str,
    subject: str,
    text: str,
    path: str,
    now: datetime.datetime | None = None,
) -> bool:
    """Sends a notice on each channel the user wants and records it. True if any went out."""
    sent = False
    for channel in _channels(user, kind):
        if channel == 'email':
            delivered = _email(user, kind, subject, text, path)
        else:
            delivered = push.send(user, f'{settings.WEB_APP_NAME}: {subject}', text, path) > 0
        if delivered:
            NotificationLog.objects.create(
                user=user,
                kind=kind,
                channel=channel,
                reference=reference,
                sent_at=now or timezone.now(),
            )
            sent = True
    return sent


def _area(relationship: CareRelationship, user: User) -> str:
    return 'app' if relationship.patient_id == user.id else 'pro'


def notify_unread_messages(now: datetime.datetime | None = None) -> int:
    """
    Emails each person with messages unread for MESSAGE_DELAY, once per
    conversation and MESSAGE_INTERVAL, and only about messages newer than the
    last email of that conversation. Returns the number of emails sent.
    """
    now = now or timezone.now()
    rows = (
        Message.objects.filter(read_at__isnull=True, created__lte=now - MESSAGE_DELAY)
        .values(
            'relationship',
            'sender',
            'relationship__professional',
            'relationship__patient',
        )
        .annotate(newest=Max('created'))
    )
    pending = {}
    for row in rows:
        professional, patient = row['relationship__professional'], row['relationship__patient']
        recipient = patient if row['sender'] == professional else professional
        if recipient is None:
            continue
        key = (recipient, row['relationship'])
        pending[key] = max(pending.get(key, row['newest']), row['newest'])

    sent = 0
    with translation.override(settings.WEB_APP_LANGUAGE):
        for (recipient_id, relationship_id), newest in pending.items():
            user = User.objects.filter(pk=recipient_id).first()
            if user is None or not wants(user, NotificationKind.MESSAGES):
                continue
            last = (
                NotificationLog.objects.filter(
                    user=user,
                    kind=NotificationKind.MESSAGES,
                    reference=str(relationship_id),
                )
                .values_list('sent_at', flat=True)
                .first()
            )
            if last and (now - last < MESSAGE_INTERVAL or newest <= last):
                continue
            relationship = CareRelationship.objects.get(pk=relationship_id)
            sent += _send(
                user,
                NotificationKind.MESSAGES,
                str(relationship_id),
                _('New messages'),
                _('You have new messages in a conversation. Open the app to read them.'),
                f'/{_area(relationship, user)}/mensagens/{relationship_id}',
                now,
            )
    return sent


def notify_prescription_published(prescription) -> bool:
    """Tells the patient that a professional published a plan for them"""
    patient = prescription.user
    if prescription.author_id is None or not wants(patient, NotificationKind.PRESCRIPTION):
        return False
    with translation.override(settings.WEB_APP_LANGUAGE):
        return _send(
            patient,
            NotificationKind.PRESCRIPTION,
            str(prescription.care_relationship_id or ''),
            _('New plan'),
            _('A professional published a new plan for you. Open the app to see it.'),
            '/app',
        )


def notify_appointment(appointment: Appointment, event: str, actor: User) -> bool:
    """Tells the other side that an appointment was scheduled, changed or cancelled"""
    relationship = appointment.relationship
    recipient = (
        relationship.patient
        if actor.id == relationship.professional_id
        else relationship.professional
    )
    if recipient is None or not wants(recipient, NotificationKind.APPOINTMENT):
        return False
    when = timezone.localtime(appointment.start, recipient.userprofile.zone_info)
    with translation.override(settings.WEB_APP_LANGUAGE):
        moment = when.strftime('%d/%m/%Y %H:%M')
        texts = {
            'scheduled': (
                _('Appointment scheduled'),
                _('An appointment was scheduled for %(moment)s.') % {'moment': moment},
            ),
            'changed': (
                _('Appointment changed'),
                _('An appointment was moved to %(moment)s.') % {'moment': moment},
            ),
            'cancelled': (
                _('Appointment cancelled'),
                _('The appointment of %(moment)s was cancelled.') % {'moment': moment},
            ),
        }
        subject, text = texts[event]
        return _send(
            recipient,
            NotificationKind.APPOINTMENT,
            str(appointment.pk),
            subject,
            text,
            f'/{_area(relationship, recipient)}/agenda',
        )

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
import uuid

# Django
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NotificationKind(models.TextChoices):
    MESSAGES = 'messages', _('New messages')
    PRESCRIPTION = 'prescription', _('Published plans')
    APPOINTMENT = 'appointment', _('Appointments')


class NotificationPreference(models.Model):
    """Which notices a user gets outside the app, by email and push; all on by default"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='care_notification_preference',
    )

    email_messages = models.BooleanField(default=True)

    email_prescriptions = models.BooleanField(default=True)

    email_appointments = models.BooleanField(default=True)

    push_messages = models.BooleanField(default=True)

    push_prescriptions = models.BooleanField(default=True)

    push_appointments = models.BooleanField(default=True)

    def __str__(self):
        return f'Notification preference of {self.user_id}'

    def get_owner_object(self):
        return self


class NotificationLog(models.Model):
    """
    A notice sent outside the app: what kind, to whom and when, never its
    content. Limits the emails about new messages and documents what was sent.
    """

    class Meta:
        ordering = ['-sent_at']
        indexes = [models.Index(fields=['user', 'kind', 'reference', 'sent_at'])]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='care_notifications',
    )

    kind = models.CharField(max_length=20, choices=NotificationKind.choices)

    channel = models.CharField(max_length=10, default='email')

    reference = models.CharField(max_length=64, blank=True)
    """The follow-up or appointment the notice is about"""

    sent_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.kind} to {self.user_id} at {self.sent_at}'

    def get_owner_object(self):
        return self


class PushPlatform(models.TextChoices):
    ANDROID = 'android', 'Android'
    IOS = 'ios', 'iOS'
    WEB = 'web', 'Web'


class PushDevice(models.Model):
    """A device that gets push notices (Firebase Cloud Messaging) for its user"""

    class Meta:
        ordering = ['-last_seen']

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='care_push_devices',
    )

    token = models.CharField(max_length=512, unique=True)
    """Registration token of Firebase Cloud Messaging"""

    platform = models.CharField(max_length=10, choices=PushPlatform.choices)

    created = models.DateTimeField(default=timezone.now)

    last_seen = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.platform} device of {self.user_id}'

    def get_owner_object(self):
        return self

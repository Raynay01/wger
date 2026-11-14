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
import pathlib
import uuid

# Django
from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# wger
from wger.care.models.relationship import CareRelationship
from wger.care.storage import private_storage


class AttachmentKind(models.TextChoices):
    IMAGE = 'image', _('Image')
    VIDEO = 'video', _('Video')


def message_upload_dir(instance, filename):
    """Random names, so neither the patient nor the original name show up on disk"""
    ext = pathlib.Path(filename).suffix.lower()
    return f'care/messages/{instance.relationship_id}/{uuid.uuid4()}{ext}'


class Message(models.Model):
    """
    A chat message between the patient and the professional of a relationship,
    optionally with a photo or video
    """

    class Meta:
        ordering = ['created']
        indexes = [models.Index(fields=['relationship', 'created'])]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    relationship = models.ForeignKey(
        CareRelationship,
        on_delete=models.CASCADE,
        related_name='messages',
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
    )

    text = models.TextField(blank=True, max_length=4000)

    attachment = models.FileField(
        blank=True,
        storage=private_storage,
        upload_to=message_upload_dir,
        max_length=200,
    )

    attachment_kind = models.CharField(max_length=5, choices=AttachmentKind.choices, blank=True)

    attachment_name = models.CharField(max_length=200, blank=True)
    """Original file name, shown to the other side"""

    created = models.DateTimeField(default=timezone.now)

    read_at = models.DateTimeField(null=True, blank=True)
    """When the recipient opened the conversation"""

    def __str__(self):
        return f'{self.sender_id} {self.created}'

    def get_owner_object(self):
        return None


@receiver(models.signals.post_delete, sender=Message)
def delete_attachment(sender, instance: Message, **kwargs):
    if instance.attachment:
        instance.attachment.delete(save=False)

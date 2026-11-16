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
from django.utils.translation import gettext_lazy as _

# wger
from wger.care.models.relationship import CareRelationship


class NoteCategory(models.TextChoices):
    GENERAL = 'general', _('General')
    GUIDANCE = 'guidance', _('Guidance')
    RESTRICTION = 'restriction', _('Restriction')
    ALERT = 'alert', _('Alert')


class MultidisciplinaryNote(models.Model):
    """
    A note a professional writes about a patient for the other professionals

    Other professionals read it only if the patient shares the notes scope with them.
    """

    class Meta:
        ordering = ['-created']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    relationship = models.ForeignKey(
        CareRelationship,
        on_delete=models.CASCADE,
        related_name='notes',
        help_text='The relationship of the author with the patient',
    )

    category = models.CharField(
        max_length=15,
        choices=NoteCategory.choices,
        default=NoteCategory.GENERAL,
    )

    text = models.TextField()

    visible_to_patient = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)

    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text[:40]

    def get_owner_object(self):
        return None


class AccessLog(models.Model):
    """
    A professional reading data of a patient: what other modules share, and
    once per day the records the patient writes in the professional's module
    """

    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['patient', '-timestamp'])]

    id = models.BigAutoField(primary_key=True)

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='care_access_logs',
    )

    resource = models.CharField(max_length=60)

    relationship = models.ForeignKey(
        CareRelationship,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.actor_id} read {self.resource} of {self.patient_id}'

    def get_owner_object(self):
        return None

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
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _

# wger
from wger.care.models.relationship import CareRelationship


class AppointmentKind(models.TextChoices):
    CONSULTATION = 'consultation', _('Consultation')
    SESSION = 'session', _('Session')
    ASSESSMENT = 'assessment', _('Assessment')
    FOLLOW_UP = 'follow_up', _('Follow-up')


class AppointmentStatus(models.TextChoices):
    SCHEDULED = 'scheduled', _('Scheduled')
    DONE = 'done', _('Done')
    CANCELLED = 'cancelled', _('Cancelled')


class Appointment(models.Model):
    """
    A consultation, session or assessment of a professional with a patient
    """

    class Meta:
        ordering = ['start']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    relationship = models.ForeignKey(
        CareRelationship,
        on_delete=models.CASCADE,
        related_name='appointments',
    )

    kind = models.CharField(
        max_length=15,
        choices=AppointmentKind.choices,
        default=AppointmentKind.CONSULTATION,
    )

    start = models.DateTimeField()

    duration_minutes = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(5), MaxValueValidator(600)],
    )

    location = models.CharField(
        max_length=200,
        blank=True,
        help_text='Address or link of an online consultation',
    )

    notes = models.TextField(blank=True, help_text='Visible to the patient')

    status = models.CharField(
        max_length=10,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.SCHEDULED,
    )

    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.kind} {self.start}'

    def get_owner_object(self):
        return None

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
from wger.care.disciplines import Discipline
from wger.care.models.organization import Organization


class RelationshipStatus(models.TextChoices):
    INVITED = 'invited', _('Invited')
    ACTIVE = 'active', _('Active')
    PAUSED = 'paused', _('Paused')
    ENDED = 'ended', _('Ended')


OPEN_STATUSES = (RelationshipStatus.ACTIVE, RelationshipStatus.PAUSED)
"""Statuses in which the professional follows the patient"""

PENDING_STATUSES = (RelationshipStatus.INVITED, *OPEN_STATUSES)
"""Statuses that block a second relationship for the same professional and discipline"""


class CareRelationship(models.Model):
    """
    A professional following a patient in one discipline

    The patient joins by accepting the invitation, which is also the consent
    for the professional to process their health data in that discipline.
    """

    class Meta:
        ordering = ['-created']
        constraints = [
            models.UniqueConstraint(
                fields=['professional', 'patient', 'discipline'],
                condition=models.Q(status__in=PENDING_STATUSES),
                name='unique_open_relationship',
            ),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='relationships',
    )

    professional = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='care_patients',
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='care_professionals',
        null=True,
        blank=True,
    )

    discipline = models.CharField(max_length=15, choices=Discipline.choices)

    status = models.CharField(
        max_length=10,
        choices=RelationshipStatus.choices,
        default=RelationshipStatus.INVITED,
    )

    invited_email = models.EmailField(blank=True)

    invitation_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    created = models.DateTimeField(auto_now_add=True)

    started = models.DateTimeField(null=True, blank=True)

    ended = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.professional} → {self.patient or self.invited_email} ({self.discipline})'

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES

    def get_owner_object(self):
        return None

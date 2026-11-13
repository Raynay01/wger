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


class VerificationStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    VERIFIED = 'verified', _('Verified')
    REJECTED = 'rejected', _('Rejected')


class ProfessionalRegistration(models.Model):
    """
    A professional's registration in the council of a discipline (CREF, CREFITO, CRN)

    Prescribing in a discipline needs a registration that was not rejected.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'discipline'],
                name='unique_registration_per_discipline',
            ),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='professional_registrations',
    )

    discipline = models.CharField(max_length=15, choices=Discipline.choices)

    council = models.CharField(verbose_name=_('Council'), max_length=10)

    number = models.CharField(verbose_name=_('Registration number'), max_length=30)

    region = models.CharField(
        verbose_name=_('State'),
        max_length=2,
        help_text=_('Two letter code of the state, e.g. SP'),
    )

    status = models.CharField(
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    verified_at = models.DateTimeField(null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.council} {self.number}/{self.region}'

    def get_owner_object(self):
        return self

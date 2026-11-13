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


class DataRequestKind(models.TextChoices):
    EXPORT = 'export', _('Data export')
    DELETION = 'deletion', _('Account deletion')


class DataRequestStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    DONE = 'done', _('Done')
    CANCELLED = 'cancelled', _('Cancelled')
    REJECTED = 'rejected', _('Rejected')


class DataRequest(models.Model):
    """
    A request of a data subject (LGPD art. 18), kept as evidence after the account is gone
    """

    class Meta:
        ordering = ['-created']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='data_requests',
    )

    user_reference = models.CharField(
        max_length=150,
        help_text='Username at the time of the request, kept after a deletion',
    )

    kind = models.CharField(max_length=10, choices=DataRequestKind.choices)

    status = models.CharField(
        max_length=10,
        choices=DataRequestStatus.choices,
        default=DataRequestStatus.PENDING,
    )

    created = models.DateTimeField(auto_now_add=True)

    completed_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, help_text='Reason of a rejection or other remarks')

    def __str__(self):
        return f'{self.kind} {self.user_reference} ({self.status})'

    def get_owner_object(self):
        return None

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


class OrganizationKind(models.TextChoices):
    SOLO = 'solo', _('Independent professional')
    CLINIC = 'clinic', _('Clinic')
    TEAM = 'team', _('Multidisciplinary team')


class Organization(models.Model):
    """
    A tenant: an independent professional, a clinic or a team
    """

    class Meta:
        ordering = ['name']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    name = models.CharField(verbose_name=_('Name'), max_length=120)

    kind = models.CharField(
        verbose_name=_('Kind'),
        max_length=10,
        choices=OrganizationKind.choices,
        default=OrganizationKind.SOLO,
    )

    document = models.CharField(
        verbose_name=_('CPF or CNPJ'),
        max_length=20,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_owner_object(self):
        return None


class MembershipRole(models.TextChoices):
    OWNER = 'owner', _('Owner')
    ADMIN = 'admin', _('Administrator')
    PROFESSIONAL = 'professional', _('Professional')
    RECEPTION = 'reception', _('Reception')


MANAGING_ROLES = (MembershipRole.OWNER, MembershipRole.ADMIN)
"""Roles that can change the organization and its members"""

CARING_ROLES = (MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.PROFESSIONAL)
"""Roles that can follow patients"""


class Membership(models.Model):
    """
    A user working in an organization
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'user'],
                name='unique_membership_per_organization',
            ),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships',
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='care_memberships')

    role = models.CharField(
        max_length=15,
        choices=MembershipRole.choices,
        default=MembershipRole.PROFESSIONAL,
    )

    is_active = models.BooleanField(default=True)

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} @ {self.organization} ({self.role})'

    def get_owner_object(self):
        return None

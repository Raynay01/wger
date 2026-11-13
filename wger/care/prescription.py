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
Authorship and versioning shared by the prescriptions of all modules

A prescription (nutrition plan, routine, physio protocol) is either self-managed
(no author, the owning user edits it freely, as in plain wger) or written by a
professional for a patient through a care relationship. A prescribed one is a
draft until published; a published version is frozen, changes go into a new
version of the same lineage, and the previous one becomes superseded.
"""

# Standard Library
import hashlib
import json
import uuid

# Django
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Third Party
from rest_framework.utils.encoders import JSONEncoder

# wger
from wger.care.models import (
    OPEN_STATUSES,
    CareRelationship,
)


class PrescriptionStatus(models.TextChoices):
    DRAFT = 'draft', _('Draft')
    PUBLISHED = 'published', _('Published')
    SUPERSEDED = 'superseded', _('Superseded')
    ARCHIVED = 'archived', _('Archived')


class PrescriptionMixin(models.Model):
    """
    Fields for authorship and versioning. Rows without author are self-managed.
    """

    class Meta:
        abstract = True

    discipline: str = ''
    """The discipline a professional needs to write this prescription"""

    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name='+',
    )

    organization = models.ForeignKey(
        'care.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name='+',
    )

    care_relationship = models.ForeignKey(
        'care.CareRelationship',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name='+',
    )

    status = models.CharField(
        max_length=12,
        choices=PrescriptionStatus.choices,
        default=PrescriptionStatus.PUBLISHED,
        editable=False,
    )

    version = models.PositiveIntegerField(default=1, editable=False)

    lineage_id = models.UUIDField(null=True, blank=True, editable=False, db_index=True)
    """Shared by all versions of a prescription, empty for self-managed ones"""

    previous_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name='+',
    )

    published_at = models.DateTimeField(null=True, blank=True, editable=False)

    snapshot = models.JSONField(null=True, blank=True, editable=False)
    """Content of the version at publication"""

    snapshot_hash = models.CharField(max_length=64, blank=True, editable=False)

    @property
    def is_prescribed(self) -> bool:
        return self.author_id is not None

    def can_be_written_by(self, user_id: int) -> bool:
        """
        Whether the user may change this prescription or its children

        Self-managed ones belong to their user. Prescribed ones only to their
        author, while the draft is not published and the relationship is open.
        """
        if self.author_id is None:
            return self.user_id == user_id

        return (
            self.author_id == user_id
            and self.status == PrescriptionStatus.DRAFT
            and self.care_relationship_id is not None
            and self.care_relationship.status in OPEN_STATUSES
        )

    def can_be_managed_by(self, user_id: int) -> bool:
        """Whether the user may publish or version this prescription"""
        return (
            self.author_id is not None
            and self.author_id == user_id
            and self.care_relationship_id is not None
            and self.care_relationship.status in OPEN_STATUSES
        )

    def build_snapshot(self) -> dict:
        """The content of this version, overridden by each prescription"""
        return {}

    def copy_content_to(self, target) -> None:
        """Copies the children (meals, days, ...) to a new version, overridden"""

    def publish(self) -> None:
        """
        Freezes this draft and supersedes the published version of the lineage
        """
        self.__class__.objects.filter(
            lineage_id=self.lineage_id,
            status=PrescriptionStatus.PUBLISHED,
        ).exclude(pk=self.pk).update(status=PrescriptionStatus.SUPERSEDED)

        data = json.loads(json.dumps(self.build_snapshot(), cls=JSONEncoder))
        self.snapshot = data
        self.snapshot_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        self.status = PrescriptionStatus.PUBLISHED
        self.published_at = timezone.now()
        self.save()

    def new_version(self):
        """
        Creates a draft copy of this version, to be edited and published
        """
        clone = self.__class__.objects.get(pk=self.pk)
        # A missing pk takes the field default (UUID) or the next auto value
        clone.pk = None
        clone._state.adding = True
        self.prepare_new_version(clone)
        clone.status = PrescriptionStatus.DRAFT
        clone.version = self.latest_version_number() + 1
        clone.previous_version = self
        clone.published_at = None
        clone.snapshot = None
        clone.snapshot_hash = ''
        clone.save()
        self.copy_content_to(clone)
        return clone

    def prepare_new_version(self, clone) -> None:
        """Resets fields of the clone that must not be copied, overridden"""

    def latest_version_number(self) -> int:
        return (
            self.__class__.objects.filter(lineage_id=self.lineage_id)
            .order_by('-version')
            .values_list('version', flat=True)
            .first()
            or self.version
        )


def start_prescription(instance: PrescriptionMixin, relationship: CareRelationship, author: User):
    """Fills the authorship fields of a new prescription for a patient"""
    instance.user = relationship.patient
    instance.author = author
    instance.organization = relationship.organization
    instance.care_relationship = relationship
    instance.status = PrescriptionStatus.DRAFT
    instance.version = 1
    instance.lineage_id = uuid.uuid4()


def visible_prescriptions_q(user: User, prefix: str = '') -> Q:
    """
    Prescriptions a user can read: their own ones without the drafts of their
    professionals, and the ones they wrote for a patient they still follow
    """
    p = prefix
    own = Q(**{f'{p}user': user}) & ~Q(
        **{f'{p}author__isnull': False, f'{p}status': PrescriptionStatus.DRAFT}
    )
    authored = Q(**{f'{p}author': user, f'{p}care_relationship__status__in': OPEN_STATUSES})
    return own | authored


def prescription_root(obj):
    """The prescription an object belongs to, or None"""
    owner = obj.get_owner_object() if hasattr(obj, 'get_owner_object') else None
    return owner if isinstance(owner, PrescriptionMixin) else None

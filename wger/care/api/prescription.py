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
API pieces shared by the prescription endpoints of all modules
"""

# Django
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Third Party
from drf_spectacular.utils import extend_schema
from rest_framework import (
    exceptions,
    serializers,
)
from rest_framework.decorators import action
from rest_framework.response import Response

# wger
from wger.care import notifications, policy
from wger.care.models import CareRelationship
from wger.care.prescription import (
    PrescriptionStatus,
    prescription_root,
    start_prescription,
)


PRESCRIPTION_FIELDS = (
    'care_relationship',
    'author',
    'organization',
    'status',
    'version',
    'lineage_id',
    'previous_version',
    'published_at',
    'snapshot_hash',
)

PRESCRIPTION_READ_ONLY_FIELDS = tuple(f for f in PRESCRIPTION_FIELDS if f != 'care_relationship')


class PrescriptionSerializerMixin(serializers.Serializer):
    """
    Adds the authorship fields. ``care_relationship`` is only accepted when a
    professional creates a prescription for a patient through the REST API.
    """

    care_relationship = serializers.PrimaryKeyRelatedField(
        queryset=CareRelationship.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate(self, data):
        data = super().validate(data)
        relationship = data.pop('care_relationship', None)
        if relationship is None:
            return data

        if self.instance is not None or not self.context.get('allow_prescription'):
            raise serializers.ValidationError(
                {'care_relationship': _('A prescription cannot be moved to another patient.')}
            )

        user = self.context['request'].user
        discipline = self.Meta.model.discipline
        if (
            relationship.professional_id != user.id
            or not relationship.is_open
            or relationship.discipline != discipline
        ):
            raise serializers.ValidationError(
                {'care_relationship': _('You do not follow this patient in this discipline.')}
            )
        if not policy.has_registration(user, discipline):
            raise serializers.ValidationError(
                {'care_relationship': _('You need a council registration for this discipline.')}
            )
        self._prescription_relationship = relationship
        return data

    def create(self, validated_data):
        relationship = getattr(self, '_prescription_relationship', None)
        if relationship is None:
            return super().create(validated_data)

        instance = self.Meta.model()
        start_prescription(instance, relationship, self.context['request'].user)
        # Without a start date the prescription starts on the patient's today, not the server's
        if 'start' not in self.initial_data and 'start' in self.fields:
            validated_data['start'] = timezone.localdate(
                timezone=relationship.patient.userprofile.zone_info
            )
        for field in (
            'user',
            'author',
            'organization',
            'care_relationship',
            'status',
            'version',
            'lineage_id',
        ):
            validated_data[field] = getattr(instance, field)
        return super().create(validated_data)


class PrescriptionWriteGuardMixin:
    """
    Refuses changes to prescriptions (and their children) the user cannot write
    """

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['allow_prescription'] = self.action == 'create'
        return context

    def _check_writable(self, instance):
        root = prescription_root(instance)
        if root is not None and not root.can_be_written_by(self.request.user.id):
            raise exceptions.PermissionDenied(_('You cannot change this prescription.'))

    def perform_update(self, serializer):
        self._check_writable(serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._check_writable(instance)
        super().perform_destroy(instance)


class PrescriptionViewSetMixin(PrescriptionWriteGuardMixin):
    """
    Publish, new-version and archive actions for the root of a prescription
    """

    def perform_destroy(self, instance):
        if instance.is_prescribed and instance.status != PrescriptionStatus.DRAFT:
            raise exceptions.PermissionDenied(_('Published versions are kept as history.'))
        super().perform_destroy(instance)

    def _managed_object(self):
        instance = self.get_object()
        if not instance.can_be_managed_by(self.request.user.id):
            raise exceptions.PermissionDenied()
        return instance

    @extend_schema(request=None)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def publish(self, request, pk):
        """Publish a draft. The previous published version becomes superseded."""
        instance = self._managed_object()
        if instance.status != PrescriptionStatus.DRAFT:
            raise exceptions.ValidationError(_('Only drafts can be published.'))
        instance.publish()
        transaction.on_commit(lambda: notifications.notify_prescription_published(instance))
        return Response(self.get_serializer(instance).data)

    @extend_schema(request=None)
    @action(detail=True, methods=['post'], url_path='new-version')
    @transaction.atomic
    def new_version(self, request, pk):
        """Create an editable draft from a published version"""
        instance = self._managed_object()
        if instance.status == PrescriptionStatus.DRAFT:
            raise exceptions.ValidationError(_('This version is still a draft.'))
        if (
            type(instance)
            .objects.filter(
                lineage_id=instance.lineage_id,
                status=PrescriptionStatus.DRAFT,
            )
            .exists()
        ):
            raise exceptions.ValidationError(_('There already is a draft for this prescription.'))
        clone = instance.new_version()
        return Response(self.get_serializer(clone).data, status=201)

    @extend_schema(request=None)
    @action(detail=True, methods=['post'])
    def archive(self, request, pk):
        """Archive a published version, e.g. at the end of the follow-up"""
        instance = self._managed_object()
        if instance.status != PrescriptionStatus.PUBLISHED:
            raise exceptions.ValidationError(_('Only published versions can be archived.'))
        instance.status = PrescriptionStatus.ARCHIVED
        instance.save()
        return Response(self.get_serializer(instance).data)

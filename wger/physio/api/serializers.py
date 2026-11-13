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

# Django
from django.utils.translation import gettext_lazy as _

# Third Party
from rest_framework import serializers

# wger
from wger.care.api.prescription import (
    PRESCRIPTION_FIELDS,
    PRESCRIPTION_READ_ONLY_FIELDS,
    PrescriptionSerializerMixin,
)
from wger.care.disciplines import Discipline
from wger.care.models import CareRelationship
from wger.physio.models import (
    ExerciseRecord,
    FunctionalAssessment,
    PainRecord,
    PhysioProtocol,
    ProtocolExercise,
)


class PhysioProtocolSerializer(PrescriptionSerializerMixin, serializers.ModelSerializer):
    pain_moments = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = PhysioProtocol
        fields = (
            'id',
            'name',
            'description',
            'start',
            'end',
            'pain_before',
            'pain_during',
            'pain_after',
            'pain_next_day',
            'pain_moments',
            'pain_alert_threshold',
            'pain_alert_increase',
            'created',
            *PRESCRIPTION_FIELDS,
        )
        read_only_fields = ('created', *PRESCRIPTION_READ_ONLY_FIELDS)

    def validate(self, data):
        data = super().validate(data)
        start = data.get('start') or getattr(self.instance, 'start', None)
        end = data.get('end') or getattr(self.instance, 'end', None)
        if start and end and start > end:
            raise serializers.ValidationError(
                {'end': _('The end date cannot be before the start date.')}
            )
        return data


class ProtocolExerciseSerializer(serializers.ModelSerializer):
    protocol = serializers.PrimaryKeyRelatedField(queryset=PhysioProtocol.objects.all())

    class Meta:
        model = ProtocolExercise
        fields = (
            'id',
            'protocol',
            'exercise',
            'name',
            'sets',
            'repetitions',
            'duration_seconds',
            'load',
            'frequency_per_week',
            'location',
            'instructions',
            'video_url',
            'order',
        )


class PainRecordSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PainRecord
        fields = (
            'id',
            'user',
            'protocol',
            'protocol_exercise',
            'datetime',
            'moment',
            'value',
            'body_region',
            'notes',
        )


class ExerciseRecordSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ExerciseRecord
        fields = (
            'id',
            'user',
            'protocol_exercise',
            'datetime',
            'sets',
            'repetitions',
            'duration_seconds',
            'notes',
        )


class FunctionalAssessmentSerializer(serializers.ModelSerializer):
    relationship = serializers.PrimaryKeyRelatedField(queryset=CareRelationship.objects.all())
    patient = serializers.IntegerField(source='relationship.patient_id', read_only=True)

    class Meta:
        model = FunctionalAssessment
        fields = (
            'id',
            'relationship',
            'patient',
            'kind',
            'name',
            'side',
            'value',
            'unit',
            'data',
            'date',
            'notes',
            'created',
        )
        read_only_fields = ('created',)

    def validate_relationship(self, value):
        if self.instance is not None and value != self.instance.relationship:
            raise serializers.ValidationError(_('The patient of an assessment cannot be changed.'))
        if (
            value.professional_id != self.context['request'].user.id
            or not value.is_open
            or value.discipline != Discipline.PHYSIO
        ):
            raise serializers.ValidationError(
                _('You do not follow this patient in this discipline.')
            )
        return value

    def validate_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(_('This must be an object.'))
        return value


class PainAlertSerializer(serializers.Serializer):
    patient = serializers.IntegerField()
    record = serializers.UUIDField()
    datetime = serializers.DateTimeField()
    value = serializers.IntegerField()
    reason = serializers.ChoiceField(choices=['threshold', 'increase'])

#  This file is part of wger Workout Manager <https://github.com/wger-project>.
#
#  wger Workout Manager is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  wger Workout Manager is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Nutritional anamnesis and assessments (anthropometry, energy needs)
"""

# Django
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

# Third Party
from rest_framework import (
    exceptions,
    serializers,
    viewsets,
)
from rest_framework.permissions import IsAuthenticated

# wger
from wger.care.disciplines import Discipline
from wger.care.models import (
    OPEN_STATUSES,
    CareRelationship,
)
from wger.nutrition.models import (
    EnergyEquation,
    NutritionalAnamnesis,
    NutritionalAssessment,
)
from wger.nutrition.models.assessment import (
    SKINFOLD_SITES,
    skinfold_sites,
)


class ClinicalRecordSerializerMixin(serializers.Serializer):
    """A record the nutritionist writes about a patient they follow"""

    relationship = serializers.PrimaryKeyRelatedField(queryset=CareRelationship.objects.all())
    patient = serializers.IntegerField(source='relationship.patient_id', read_only=True)

    def validate_relationship(self, value):
        if self.instance is not None and value != self.instance.relationship:
            raise serializers.ValidationError(_('The patient of an assessment cannot be changed.'))
        if (
            value.professional_id != self.context['request'].user.id
            or not value.is_open
            or value.discipline != Discipline.NUTRITION
        ):
            raise serializers.ValidationError(
                _('You do not follow this patient in this discipline.')
            )
        return value


class NutritionalAnamnesisSerializer(ClinicalRecordSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = NutritionalAnamnesis
        fields = (
            'id',
            'relationship',
            'patient',
            'date',
            'goal',
            'medical_history',
            'medications',
            'allergies',
            'preferences',
            'eating_habits',
            'bowel_habits',
            'sleep',
            'water',
            'alcohol_smoking',
            'physical_activity',
            'notes',
            'created',
        )
        read_only_fields = ('created',)


class MacrosSerializer(serializers.Serializer):
    protein = serializers.IntegerField(help_text='g')
    carbohydrates = serializers.IntegerField(help_text='g')
    fat = serializers.IntegerField(help_text='g')


class NutritionalAssessmentSerializer(
    ClinicalRecordSerializerMixin,
    serializers.ModelSerializer,
):
    bmi = serializers.DecimalField(max_digits=4, decimal_places=1, read_only=True)
    waist_hip_ratio = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        read_only=True,
        allow_null=True,
    )
    lean_mass = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        read_only=True,
        allow_null=True,
    )
    skinfold_sum = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        read_only=True,
        allow_null=True,
    )
    macros = MacrosSerializer(read_only=True, allow_null=True)
    basal_energy = serializers.IntegerField(read_only=True)
    total_energy = serializers.IntegerField(read_only=True)
    target_energy = serializers.IntegerField(read_only=True)

    class Meta:
        model = NutritionalAssessment
        fields = (
            'id',
            'relationship',
            'patient',
            'date',
            'sex',
            'age',
            'weight',
            'height',
            'waist',
            'hip',
            'body_fat',
            'skinfold_protocol',
            'skinfolds',
            'skinfold_sum',
            'activity_level',
            'equation',
            'energy_adjustment',
            'protein_per_kg',
            'fat_percent',
            'macros',
            'notes',
            'bmi',
            'waist_hip_ratio',
            'lean_mass',
            'basal_energy',
            'total_energy',
            'target_energy',
            'created',
        )
        read_only_fields = ('created',)

    def validate_skinfolds(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(_('This must be an object.'))
        for site, mm in value.items():
            if site not in SKINFOLD_SITES:
                raise serializers.ValidationError(_('Unknown skinfold site: %s') % site)
            if not isinstance(mm, (int, float)) or isinstance(mm, bool) or not 1 <= mm <= 80:
                raise serializers.ValidationError(
                    _('A skinfold must be between 1 and 80 mm (%s).') % site
                )
        return value

    def validate(self, data):
        data = super().validate(data)

        def current(key):
            return data.get(key, getattr(self.instance, key, None))

        protocol = current('skinfold_protocol')
        if protocol:
            skinfolds = current('skinfolds') or {}
            missing = [s for s in skinfold_sites(protocol, current('sex')) if s not in skinfolds]
            if missing:
                raise serializers.ValidationError(
                    {'skinfolds': _('Missing skinfolds: %s') % ', '.join(missing)}
                )

        has_body_fat = current('body_fat') is not None or bool(protocol)
        if current('equation') == EnergyEquation.KATCH_MCARDLE and not has_body_fat:
            raise serializers.ValidationError(
                {'body_fat': _('The Katch-McArdle equation needs the body fat.')}
            )
        return data


class ClinicalRecordViewSet(viewsets.ModelViewSet):
    """Written by the nutritionist, read by them and the patient"""

    permission_classes = [IsAuthenticated]
    model = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.model.objects.none()
        user = self.request.user
        return self.model.objects.filter(
            Q(relationship__professional=user, relationship__status__in=OPEN_STATUSES)
            | Q(relationship__patient=user)
        ).select_related('relationship')

    def _check_author(self, instance):
        if instance.relationship.professional_id != self.request.user.id:
            raise exceptions.PermissionDenied()

    def perform_update(self, serializer):
        self._check_author(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_author(instance)
        instance.delete()


class NutritionalAnamnesisViewSet(ClinicalRecordViewSet):
    """
    The nutritional anamnesis: history, habits and preferences of the patient
    """

    model = NutritionalAnamnesis
    serializer_class = NutritionalAnamnesisSerializer
    filterset_fields = ('relationship', 'date')


class NutritionalAssessmentViewSet(ClinicalRecordViewSet):
    """
    Anthropometric assessments with BMI, waist-hip ratio and the energy needs
    (basal rate by the chosen equation, times the activity factor, plus the
    adjustment for the goal)
    """

    model = NutritionalAssessment
    serializer_class = NutritionalAssessmentSerializer
    filterset_fields = ('relationship', 'date')
    ordering_fields = ('date',)

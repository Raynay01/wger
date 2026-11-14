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
Periodization: training plans (macrocycles) made of blocks (mesocycles)
"""

# Standard Library
import datetime

# Django
from django.utils.translation import gettext_lazy as _

# Third Party
from drf_spectacular.utils import extend_schema
from rest_framework import (
    serializers,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.response import Response

# wger
from wger.care.api.prescription import (
    PRESCRIPTION_FIELDS,
    PRESCRIPTION_READ_ONLY_FIELDS,
    PrescriptionSerializerMixin,
    PrescriptionViewSetMixin,
    PrescriptionWriteGuardMixin,
)
from wger.care.prescription import visible_prescriptions_q
from wger.exercises.models import Muscle
from wger.manager.models import (
    Routine,
    TrainingBlock,
    TrainingPlan,
)
from wger.manager.periodization_progress import plan_progress
from wger.utils.viewsets import WgerOwnerObjectModelViewSet


def _dates(block: TrainingBlock) -> tuple | None:
    for scheduled in block.plan.schedule():
        if scheduled.block.pk == block.pk:
            return scheduled.start, scheduled.end
    return None


class WeeklySetsSerializer(serializers.Serializer):
    muscle = serializers.IntegerField()
    sets = serializers.IntegerField(min_value=1, max_value=60)


class TrainingBlockSerializer(serializers.ModelSerializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=TrainingPlan.objects.all())
    routine = serializers.PrimaryKeyRelatedField(
        queryset=Routine.objects.all(),
        required=False,
        allow_null=True,
    )
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    current_routine = serializers.SerializerMethodField()
    current_routine_name = serializers.SerializerMethodField()
    weekly_sets = serializers.ListField(
        child=WeeklySetsSerializer(),
        required=False,
        max_length=30,
        help_text='Target sets per week per muscle (primary muscle of the exercise)',
    )

    class Meta:
        model = TrainingBlock
        fields = (
            'id',
            'plan',
            'order',
            'name',
            'focus',
            'weeks',
            'routine',
            'current_routine',
            'current_routine_name',
            'intensity',
            'volume',
            'weekly_sets',
            'notes',
            'start',
            'end',
        )

    def get_start(self, obj) -> datetime.date | None:
        dates = _dates(obj)
        return dates[0] if dates else None

    def get_end(self, obj) -> datetime.date | None:
        dates = _dates(obj)
        return dates[1] if dates else None

    def get_current_routine(self, obj) -> int | None:
        routine = obj.current_routine()
        return routine.pk if routine else None

    def get_current_routine_name(self, obj) -> str | None:
        routine = obj.current_routine()
        return routine.name if routine else None

    def validate_weekly_sets(self, value):
        muscles = [item['muscle'] for item in value]
        if len(set(muscles)) != len(muscles):
            raise serializers.ValidationError(_('Each muscle can only have one target.'))
        if Muscle.objects.filter(pk__in=muscles).count() != len(set(muscles)):
            raise serializers.ValidationError(_('Unknown muscle.'))
        return [{'muscle': item['muscle'], 'sets': item['sets']} for item in value]

    def validate(self, data):
        data = super().validate(data)
        plan = data.get('plan') or getattr(self.instance, 'plan', None)
        if self.instance is not None and 'plan' in data and data['plan'] != self.instance.plan:
            raise serializers.ValidationError(
                {'plan': _('A block cannot be moved to another plan.')}
            )
        routine = data.get('routine')
        if routine is not None and plan is not None and routine.user_id != plan.user_id:
            raise serializers.ValidationError(
                {'routine': _('The routine must belong to the patient of the plan.')}
            )
        return data


class TrainingPlanSerializer(PrescriptionSerializerMixin, serializers.ModelSerializer):
    end = serializers.DateField(read_only=True)
    blocks = serializers.SerializerMethodField()

    class Meta:
        model = TrainingPlan
        fields = (
            'id',
            'name',
            'goal',
            'start',
            'end',
            'description',
            'blocks',
            'created',
            *PRESCRIPTION_FIELDS,
        )
        read_only_fields = ('created', *PRESCRIPTION_READ_ONLY_FIELDS)

    def get_blocks(self, obj) -> list[dict]:
        out = []
        for scheduled in obj.schedule():
            block = scheduled.block
            routine = block.current_routine()
            out.append(
                {
                    'id': str(block.pk),
                    'order': block.order,
                    'name': block.name,
                    'focus': block.focus,
                    'weeks': block.weeks,
                    'routine': block.routine_id,
                    'current_routine': routine.pk if routine else None,
                    'current_routine_name': routine.name if routine else None,
                    'intensity': block.intensity,
                    'volume': block.volume,
                    'weekly_sets': block.weekly_sets,
                    'notes': block.notes,
                    'start': scheduled.start,
                    'end': scheduled.end,
                }
            )
        return out


class ProgressMuscleSerializer(serializers.Serializer):
    muscle = serializers.IntegerField()
    planned_sets = serializers.IntegerField()
    done_sets = serializers.IntegerField()


class ProgressBlockMuscleSerializer(ProgressMuscleSerializer):
    name = serializers.CharField()
    weekly_sets = serializers.IntegerField(help_text='Target sets per week')


class ProgressSummarySerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    planned_sessions = serializers.IntegerField()
    done_sessions = serializers.IntegerField()
    planned_sets = serializers.IntegerField()
    done_sets = serializers.IntegerField()
    planned_load = serializers.IntegerField(help_text='Repetitions times weight, in kg')
    done_load = serializers.IntegerField(help_text='Repetitions times weight, in kg')
    average_rir = serializers.DecimalField(max_digits=4, decimal_places=1, allow_null=True)
    average_rpe = serializers.DecimalField(max_digits=4, decimal_places=1, allow_null=True)


class ProgressWeekSerializer(ProgressSummarySerializer):
    week = serializers.IntegerField()
    muscles = ProgressMuscleSerializer(
        many=True,
        help_text='Sets of the muscles with a weekly target',
    )


class ProgressBlockSerializer(ProgressSummarySerializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    focus = serializers.CharField()
    intensity = serializers.CharField()
    volume = serializers.CharField()
    muscles = ProgressBlockMuscleSerializer(
        many=True,
        help_text='Sets over the whole block of the muscles with a weekly target',
    )
    weeks = ProgressWeekSerializer(many=True)


class PlanProgressSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField(allow_null=True)
    blocks = ProgressBlockSerializer(many=True)


class TrainingPlanViewSet(PrescriptionViewSetMixin, viewsets.ModelViewSet):
    """
    Periodizations (macrocycles) of a patient. A trainer creates one by passing
    ``care_relationship``; it stays a draft until published. The blocks follow
    each other from the start date, each lasting its number of weeks.
    """

    serializer_class = TrainingPlanSerializer
    is_private = True
    filterset_fields = ('status', 'care_relationship', 'lineage_id', 'goal')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TrainingPlan.objects.none()
        return TrainingPlan.objects.filter(
            visible_prescriptions_q(self.request.user)
        ).prefetch_related('blocks__routine')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(responses=PlanProgressSerializer)
    @action(detail=True, methods=['get'])
    def progress(self, request, pk):
        """
        Planned versus done per block and per week: sessions, sets and load
        (repetitions times kg). Planned comes from the block's routine as
        prescribed, done from all training logs of the patient in that week.
        """
        data = plan_progress(self.get_object())
        return Response(PlanProgressSerializer(data).data)

    @staticmethod
    def get_owner_objects():
        return []


class TrainingBlockViewSet(PrescriptionWriteGuardMixin, WgerOwnerObjectModelViewSet):
    """
    The blocks (mesocycles) of a training plan
    """

    serializer_class = TrainingBlockSerializer
    is_private = True
    prescription_children = True
    filterset_fields = ('plan', 'focus')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TrainingBlock.objects.none()
        return TrainingBlock.objects.filter(
            visible_prescriptions_q(self.request.user, 'plan__')
        ).select_related('plan', 'routine')

    @staticmethod
    def get_owner_objects():
        return [(TrainingPlan, 'plan')]

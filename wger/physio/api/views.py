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
from django.db.models import Q

# Third Party
from drf_spectacular.utils import extend_schema
from rest_framework import (
    exceptions,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# wger
from wger.care.api.prescription import (
    PrescriptionViewSetMixin,
    PrescriptionWriteGuardMixin,
)
from wger.care.disciplines import Discipline
from wger.care.models import (
    OPEN_STATUSES,
    CareRelationship,
)
from wger.care.policy import log_reads
from wger.care.prescription import visible_prescriptions_q
from wger.physio.alerts import pain_alerts
from wger.physio.api.serializers import (
    ExerciseRecordSerializer,
    FunctionalAssessmentSerializer,
    PainAlertSerializer,
    PainRecordSerializer,
    PhysioProtocolSerializer,
    ProtocolExerciseSerializer,
)
from wger.physio.models import (
    ExerciseRecord,
    FunctionalAssessment,
    PainRecord,
    PhysioProtocol,
    ProtocolExercise,
)
from wger.utils.viewsets import WgerOwnerObjectModelViewSet


def followed_physio_patients(user):
    return CareRelationship.objects.filter(
        professional=user,
        discipline=Discipline.PHYSIO,
        status__in=OPEN_STATUSES,
    ).values('patient')


class PhysioProtocolViewSet(PrescriptionViewSetMixin, viewsets.ModelViewSet):
    """
    Therapeutic exercise protocols. A physiotherapist creates one for a patient
    by passing ``care_relationship``; it stays a draft until published.
    """

    serializer_class = PhysioProtocolSerializer
    is_private = True
    filterset_fields = ('status', 'care_relationship', 'lineage_id', 'start', 'end')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PhysioProtocol.objects.none()
        return PhysioProtocol.objects.filter(visible_prescriptions_q(self.request.user))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @staticmethod
    def get_owner_objects():
        return []


class ProtocolExerciseViewSet(PrescriptionWriteGuardMixin, WgerOwnerObjectModelViewSet):
    """
    The exercises of a protocol with their dosage
    """

    serializer_class = ProtocolExerciseSerializer
    is_private = True
    prescription_children = True
    filterset_fields = ('protocol', 'exercise', 'location')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ProtocolExercise.objects.none()
        return ProtocolExercise.objects.filter(
            visible_prescriptions_q(self.request.user, 'protocol__')
        )

    @staticmethod
    def get_owner_objects():
        return [(PhysioProtocol, 'protocol')]


class PatientRecordViewSet(WgerOwnerObjectModelViewSet):
    """
    Records the patient writes and their physiotherapists read
    """

    is_private = True
    model = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.model.objects.none()
        user = self.request.user
        if self.request.method in ('GET', 'HEAD', 'OPTIONS') and self.action == 'list':
            q = Q(user=user) | Q(user__in=followed_physio_patients(user))
        else:
            q = Q(user=user)
        return self.model.objects.filter(q)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        rows = response.data['results'] if isinstance(response.data, dict) else response.data
        log_reads(request.user, {row['user'] for row in rows}, self.read_resource)
        return response


class PainRecordViewSet(PatientRecordViewSet):
    """
    Pain on the numeric rating scale (0 to 10). Physiotherapists list the
    records of the patients they follow and get alerts.
    """

    serializer_class = PainRecordSerializer
    model = PainRecord
    read_resource = 'pain_records'
    filterset_fields = {
        'user': ['exact'],
        'protocol': ['exact'],
        'moment': ['exact'],
        'datetime': ['gte', 'lte'],
    }

    @staticmethod
    def get_owner_objects():
        return [(PhysioProtocol, 'protocol'), (ProtocolExercise, 'protocol_exercise')]

    @extend_schema(responses=PainAlertSerializer(many=True))
    @action(detail=False, methods=['get'], pagination_class=None, filter_backends=[])
    def alerts(self, request):
        """Pain above the limits of the protocols of the patients you follow"""
        alerts = PainAlertSerializer(pain_alerts(request.user), many=True).data
        log_reads(request.user, {alert['patient'] for alert in alerts}, 'pain_records')
        return Response(alerts)


class ExerciseRecordViewSet(PatientRecordViewSet):
    """
    Protocol exercises the patient did
    """

    serializer_class = ExerciseRecordSerializer
    model = ExerciseRecord
    read_resource = 'exercise_records'
    filterset_fields = {
        'user': ['exact'],
        'protocol_exercise': ['exact'],
        'datetime': ['gte', 'lte'],
    }

    @staticmethod
    def get_owner_objects():
        return [(ProtocolExercise, 'protocol_exercise')]


class FunctionalAssessmentViewSet(viewsets.ModelViewSet):
    """
    Functional assessments (range of motion, strength, tests, questionnaires).
    Written by the physiotherapist, read by them and the patient.
    """

    serializer_class = FunctionalAssessmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ('relationship', 'kind', 'name', 'date')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return FunctionalAssessment.objects.none()
        user = self.request.user
        return FunctionalAssessment.objects.filter(
            Q(relationship__professional=user, relationship__status__in=OPEN_STATUSES)
            | Q(relationship__patient=user)
        )

    def _check_author(self, instance):
        if instance.relationship.professional_id != self.request.user.id:
            raise exceptions.PermissionDenied()

    def perform_update(self, serializer):
        self._check_author(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_author(instance)
        instance.delete()

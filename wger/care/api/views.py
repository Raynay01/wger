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
import datetime

# Django
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Third Party
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
)
from rest_framework import (
    exceptions,
    mixins,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# wger
from wger.care import (
    agenda,
    deletion,
    export,
    invitations,
    policy,
    sharing,
)
from wger.care.api.serializers import (
    AcceptInvitationSerializer,
    AccessGrantSerializer,
    AppointmentSerializer,
    CareRelationshipSerializer,
    ConsentRecordSerializer,
    DataRequestSerializer,
    MembershipSerializer,
    ModulesSerializer,
    MultidisciplinaryNoteSerializer,
    MyDaySerializer,
    OrganizationSerializer,
    ProfessionalRegistrationSerializer,
    SharedDataSerializer,
)
from wger.care.disciplines import Discipline
from wger.care.models import (
    OPEN_STATUSES,
    AccessGrant,
    Appointment,
    AppointmentStatus,
    CareRelationship,
    ConsentKind,
    ConsentRecord,
    DataRequest,
    DataRequestKind,
    DataRequestStatus,
    Membership,
    MembershipRole,
    MultidisciplinaryNote,
    Organization,
    ProfessionalRegistration,
    RelationshipStatus,
    SharingScope,
)
from wger.care.my_day import my_day


CONSENT_VERSION = '1'
"""Version of the consent texts shown in the clients"""


class OrganizationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Organizations the user works in. The creator becomes the owner.
    """

    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Organization.objects.none()
        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        ).distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        organization = serializer.save()
        Membership.objects.create(
            organization=organization,
            user=self.request.user,
            role=MembershipRole.OWNER,
        )

    def perform_update(self, serializer):
        if not policy.is_managing_member(self.request.user, serializer.instance):
            raise exceptions.PermissionDenied()
        serializer.save()


class MembershipViewSet(viewsets.ModelViewSet):
    """
    Members of the organizations of the user, managed by owners and admins
    """

    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ('organization', 'role', 'is_active')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Membership.objects.none()
        organizations = Membership.objects.filter(
            user=self.request.user,
            is_active=True,
        ).values('organization')
        return Membership.objects.filter(organization__in=organizations).select_related('user')

    def _check_manager(self, organization):
        if not policy.is_managing_member(self.request.user, organization):
            raise exceptions.PermissionDenied()

    def perform_create(self, serializer):
        self._check_manager(serializer.validated_data['organization'])
        serializer.save()

    def _check_last_owner(self, membership, new_role=None, active=True):
        if membership.role != MembershipRole.OWNER:
            return
        if new_role == MembershipRole.OWNER and active:
            return
        owners = Membership.objects.filter(
            organization=membership.organization,
            role=MembershipRole.OWNER,
            is_active=True,
        ).exclude(pk=membership.pk)
        if not owners.exists():
            raise exceptions.ValidationError(_('An organization needs at least one owner.'))

    def perform_update(self, serializer):
        membership = serializer.instance
        self._check_manager(membership.organization)
        new_role = serializer.validated_data.get('role', membership.role)
        if new_role == MembershipRole.OWNER and membership.role != MembershipRole.OWNER:
            if not Membership.objects.filter(
                organization=membership.organization,
                user=self.request.user,
                role=MembershipRole.OWNER,
                is_active=True,
            ).exists():
                raise exceptions.PermissionDenied()
        self._check_last_owner(
            membership,
            new_role,
            serializer.validated_data.get('is_active', membership.is_active),
        )
        serializer.save()

    def perform_destroy(self, instance):
        self._check_manager(instance.organization)
        self._check_last_owner(instance)
        instance.delete()


class ProfessionalRegistrationViewSet(viewsets.ModelViewSet):
    """
    The council registrations of the user (CREF, CREFITO, CRN)
    """

    serializer_class = ProfessionalRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ProfessionalRegistration.objects.none()
        return ProfessionalRegistration.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # A changed number has to be verified again
        serializer.save(status='pending', verified_at=None)


class CareRelationshipViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Professionals following patients. Professionals invite by email, patients
    accept or decline; both sides can end the relationship.

    Lists the relationships of the user on both sides and the invitations sent
    to their email address.
    """

    serializer_class = CareRelationshipSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ('discipline', 'status', 'organization', 'patient')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CareRelationship.objects.none()
        user = self.request.user
        q = Q(professional=user) | Q(patient=user)
        if user.email:
            q |= Q(
                patient__isnull=True,
                status=RelationshipStatus.INVITED,
                invited_email__iexact=user.email,
            )
        queryset = CareRelationship.objects.filter(q).select_related(
            'organization',
            'professional',
            'patient',
        )

        role = self.request.query_params.get('role')
        if role == 'professional':
            queryset = queryset.filter(professional=user)
        elif role == 'patient':
            queryset = queryset.exclude(professional=user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(professional=self.request.user)

    def _get_professional_relationship(self):
        relationship = self.get_object()
        if relationship.professional_id != self.request.user.id:
            raise exceptions.PermissionDenied()
        return relationship

    def _respond(self, relationship):
        return Response(self.get_serializer(relationship).data)

    @extend_schema(request=None, responses=CareRelationshipSerializer)
    @action(detail=True, methods=['post'], url_path='send-email')
    def send_email(self, request, pk):
        """
        Email the invitation to the invited address. Nothing is sent when the
        invitation is created, only when the professional asks for it.
        """
        relationship = self._get_professional_relationship()
        if relationship.status != RelationshipStatus.INVITED or not relationship.invited_email:
            raise exceptions.ValidationError(_('This invitation is not open anymore.'))
        if not invitations.can_resend(relationship):
            raise exceptions.Throttled(
                detail=_('The invitation was sent a few minutes ago, please wait a moment.')
            )
        if not invitations.send_invitation(relationship):
            raise exceptions.APIException(_('The email could not be sent, please try again later.'))
        return self._respond(relationship)

    @extend_schema(request=AcceptInvitationSerializer, responses=CareRelationshipSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def accept(self, request, pk):
        """
        Accept an invitation, giving consent to be followed. With the token of
        the invitation link it works for any email address of the patient.
        """
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data.get('token')
        if token is not None:
            relationship = CareRelationship.objects.filter(pk=pk, invitation_token=token).first()
            if relationship is None:
                raise exceptions.NotFound()
        else:
            relationship = self.get_object()

        email_matches = (
            request.user.email and relationship.invited_email.lower() == request.user.email.lower()
        )
        token_matches = serializer.validated_data.get('token') == relationship.invitation_token
        if relationship.professional_id == request.user.id or not (email_matches or token_matches):
            raise exceptions.PermissionDenied()
        if relationship.status != RelationshipStatus.INVITED:
            raise exceptions.ValidationError(_('This invitation is not open anymore.'))
        if CareRelationship.objects.filter(
            professional=relationship.professional,
            patient=request.user,
            discipline=relationship.discipline,
            status__in=OPEN_STATUSES,
        ).exists():
            raise exceptions.ValidationError(_('This professional already follows you.'))

        relationship.patient = request.user
        relationship.status = RelationshipStatus.ACTIVE
        relationship.started = timezone.now()
        relationship.save()
        ConsentRecord.objects.create(
            user=request.user,
            kind=ConsentKind.CARE_RELATIONSHIP,
            version=CONSENT_VERSION,
            reference=str(relationship.pk),
        )
        return self._respond(relationship)

    @extend_schema(request=None, responses=CareRelationshipSerializer)
    @action(detail=True, methods=['post'])
    def decline(self, request, pk):
        """Decline an invitation"""
        relationship = self.get_object()
        if relationship.professional_id == request.user.id:
            raise exceptions.PermissionDenied()
        if relationship.status != RelationshipStatus.INVITED:
            raise exceptions.ValidationError(_('This invitation is not open anymore.'))
        relationship.status = RelationshipStatus.ENDED
        relationship.ended = timezone.now()
        relationship.save()
        return self._respond(relationship)

    @extend_schema(request=None, responses=CareRelationshipSerializer)
    @action(detail=True, methods=['post'])
    def pause(self, request, pk):
        relationship = self._get_professional_relationship()
        if relationship.status != RelationshipStatus.ACTIVE:
            raise exceptions.ValidationError(_('Only active relationships can be paused.'))
        relationship.status = RelationshipStatus.PAUSED
        relationship.save()
        return self._respond(relationship)

    @extend_schema(request=None, responses=CareRelationshipSerializer)
    @action(detail=True, methods=['post'])
    def resume(self, request, pk):
        relationship = self._get_professional_relationship()
        if relationship.status != RelationshipStatus.PAUSED:
            raise exceptions.ValidationError(_('Only paused relationships can be resumed.'))
        relationship.status = RelationshipStatus.ACTIVE
        relationship.save()
        return self._respond(relationship)

    @extend_schema(request=None, responses=CareRelationshipSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def end(self, request, pk):
        """End the relationship, from either side. Shared data stops being shared."""
        relationship = self.get_object()
        if request.user.id not in (relationship.professional_id, relationship.patient_id):
            raise exceptions.PermissionDenied()
        if relationship.status == RelationshipStatus.ENDED:
            raise exceptions.ValidationError(_('This relationship has already ended.'))
        relationship.status = RelationshipStatus.ENDED
        relationship.ended = timezone.now()
        relationship.save()
        relationship.grants.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
        return self._respond(relationship)

    @extend_schema(responses=SharedDataSerializer)
    @action(detail=True, methods=['get'])
    def shared(self, request, pk):
        """
        The data the patient shares with the professional of this relationship
        """
        relationship = self._get_professional_relationship()
        if not relationship.is_open:
            raise exceptions.PermissionDenied()

        scopes = sorted(policy.active_scopes(relationship))
        data = {}
        for scope in scopes:
            data[scope] = sharing.BUILDERS[scope](relationship.patient, relationship)
            policy.log_access(request.user, relationship, scope)
        return Response(SharedDataSerializer({'scopes': scopes, 'data': data}).data)

    def _module_relationship(self, discipline):
        relationship = self._get_professional_relationship()
        if not relationship.is_open or relationship.discipline != discipline:
            raise exceptions.PermissionDenied()
        return relationship

    def _date_param(self, relationship) -> datetime.date:
        raw = self.request.query_params.get('date')
        if not raw:
            return timezone.localdate(timezone=relationship.patient.userprofile.zone_info)
        try:
            return datetime.date.fromisoformat(raw)
        except ValueError:
            raise exceptions.ValidationError({'date': _('Use the format YYYY-MM-DD.')})

    @extend_schema(
        parameters=[OpenApiParameter('date', str, description='Day in the patient timezone')],
        responses={200: dict},
    )
    @action(detail=True, methods=['get'], url_path='nutrition-diary')
    def nutrition_diary(self, request, pk):
        """The food diary of a nutrition patient for one day"""
        # wger
        from wger.nutrition.api.serializers import LogItemSerializer
        from wger.nutrition.models import LogItem

        relationship = self._module_relationship(Discipline.NUTRITION)
        day = self._date_param(relationship)
        zone = relationship.patient.userprofile.zone_info
        start = datetime.datetime.combine(day, datetime.time.min, tzinfo=zone)
        end = start + datetime.timedelta(days=1)
        items = LogItem.objects.filter(
            plan__user=relationship.patient,
            datetime__gte=start,
            datetime__lt=end,
        ).select_related('ingredient', 'weight_unit')

        total = None
        rows = []
        for item, data in zip(items, LogItemSerializer(items, many=True).data):
            values = item.get_nutritional_values()
            total = values if total is None else total + values
            rows.append(
                {**data, 'ingredient_name': item.ingredient.name, 'values': _values(values)}
            )

        return Response({'date': day, 'items': rows, 'total': _values(total)})

    @extend_schema(responses={200: dict})
    @action(detail=True, methods=['get'], url_path='workout-logs')
    def workout_logs(self, request, pk):
        """The latest training logs of a training patient"""
        # wger
        from wger.manager.api.serializers import WorkoutLogSerializer
        from wger.manager.models import WorkoutLog

        relationship = self._module_relationship(Discipline.TRAINING)
        logs = WorkoutLog.objects.filter(user=relationship.patient).order_by('-date')[:200]
        return Response({'results': WorkoutLogSerializer(logs, many=True).data})


def _values(values) -> dict | None:
    if values is None:
        return None
    return {
        'energy': values.energy,
        'protein': values.protein,
        'carbohydrates': values.carbohydrates,
        'fat': values.fat,
        'fiber': values.fiber,
    }


class AccessGrantViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Data a patient shares with their professionals. Deleting revokes the grant,
    which is kept as evidence.
    """

    serializer_class = AccessGrantSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ('relationship', 'scope')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return AccessGrant.objects.none()
        user = self.request.user
        queryset = AccessGrant.objects.filter(
            Q(relationship__patient=user) | Q(relationship__professional=user)
        )
        if self.request.query_params.get('include_revoked') != 'true':
            queryset = queryset.filter(revoked_at__isnull=True)
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        grant = serializer.save(consent_version=CONSENT_VERSION)
        ConsentRecord.objects.create(
            user=self.request.user,
            kind=ConsentKind.SHARING,
            version=CONSENT_VERSION,
            reference=str(grant.pk),
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.relationship.patient_id != self.request.user.id:
            raise exceptions.PermissionDenied()
        if instance.revoked_at is None:
            now = timezone.now()
            instance.revoked_at = now
            instance.save()
            ConsentRecord.objects.filter(
                user=self.request.user,
                kind=ConsentKind.SHARING,
                reference=str(instance.pk),
                revoked_at__isnull=True,
            ).update(revoked_at=now)


class ConsentRecordViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Consents of the user. Deleting revokes the consent, which is kept as evidence.
    """

    serializer_class = ConsentRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ('kind',)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ConsentRecord.objects.none()
        return ConsentRecord.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if instance.revoked_at is None:
            instance.revoked_at = timezone.now()
            instance.save()


class MultidisciplinaryNoteViewSet(viewsets.ModelViewSet):
    """
    Notes between the professionals of a patient. A professional reads the notes
    of the others only if the patient shares the notes with them; the patient
    reads the ones marked as visible to them.
    """

    serializer_class = MultidisciplinaryNoteSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ('relationship', 'category')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return MultidisciplinaryNote.objects.none()
        user = self.request.user
        sharing_patients = AccessGrant.objects.filter(
            relationship__professional=user,
            relationship__status__in=OPEN_STATUSES,
            scope=SharingScope.NOTES,
            revoked_at__isnull=True,
        ).values('relationship__patient')
        q = (
            Q(relationship__professional=user)
            | Q(relationship__patient__in=sharing_patients)
            | Q(relationship__patient=user, visible_to_patient=True)
        )
        queryset = MultidisciplinaryNote.objects.filter(q).select_related(
            'relationship__professional'
        )
        patient = self.request.query_params.get('patient')
        if patient:
            if not patient.isdigit():
                raise exceptions.ValidationError({'patient': _('A valid integer is required.')})
            queryset = queryset.filter(relationship__patient_id=int(patient))
        return queryset

    def _check_author(self, note):
        if note.relationship.professional_id != self.request.user.id:
            raise exceptions.PermissionDenied()

    def perform_update(self, serializer):
        self._check_author(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_author(instance)
        instance.delete()


class MyDayView(APIView):
    """
    The patient's day: today's training and meals, with what was logged
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter('date', str, description='Day, defaults to today')],
        responses=MyDaySerializer,
    )
    def get(self, request):
        raw = request.query_params.get('date')
        if raw:
            try:
                day = datetime.date.fromisoformat(raw)
            except ValueError:
                raise exceptions.ValidationError({'date': _('Use the format YYYY-MM-DD.')})
        else:
            day = timezone.localdate(timezone=request.user.userprofile.zone_info)
        return Response(MyDaySerializer(my_day(request.user, day)).data)


class MyDataView(APIView):
    """
    All personal data of the user as a JSON file (LGPD access and portability)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        DataRequest.objects.create(
            user=request.user,
            user_reference=request.user.username,
            kind=DataRequestKind.EXPORT,
            status=DataRequestStatus.DONE,
            completed_at=timezone.now(),
        )
        response = Response(export.export_user_data(request.user))
        response['Content-Disposition'] = (
            f'attachment; filename="{export.export_filename(request.user)}"'
        )
        return response


class DataRequestViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Data subject requests of the user. Creating one asks for the deletion of
    the account: the follow-ups end at once, the platform team deletes the
    account afterwards.
    """

    serializer_class = DataRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DataRequest.objects.none()
        return DataRequest.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data_request = deletion.request_deletion(request.user)
        return Response(self.get_serializer(data_request).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=DataRequestSerializer)
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk):
        """Withdraw a pending deletion request. Ended follow-ups stay ended."""
        data_request = self.get_object()
        if data_request.status != DataRequestStatus.PENDING:
            raise exceptions.ValidationError(_('Only pending requests can be cancelled.'))
        data_request.status = DataRequestStatus.CANCELLED
        data_request.completed_at = timezone.now()
        data_request.save()
        return Response(self.get_serializer(data_request).data)


class CalendarView(APIView):
    """
    The patient's calendar: training or rest, food plan, physio protocols and
    appointments of each day, in the patient's timezone (at most 62 days)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('start', str, description='First day, YYYY-MM-DD'),
            OpenApiParameter('end', str, description='Last day, YYYY-MM-DD'),
        ],
        responses={200: dict},
    )
    def get(self, request):
        today = timezone.localdate(timezone=request.user.userprofile.zone_info)
        try:
            start = datetime.date.fromisoformat(request.query_params.get('start') or '')
        except ValueError:
            start = today.replace(day=1)
        try:
            end = datetime.date.fromisoformat(request.query_params.get('end') or '')
        except ValueError:
            end = start + datetime.timedelta(days=41)
        if end < start or (end - start).days >= agenda.MAX_DAYS:
            raise exceptions.ValidationError({'end': _('The calendar covers at most 62 days.')})
        return Response(agenda.patient_calendar(request.user, start, end))


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Appointments of the user, as professional or as patient. Professionals
    schedule, change and complete them; both sides can cancel.
    """

    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {
        'start': ['gte', 'lt'],
        'status': ['exact'],
        'relationship': ['exact'],
    }
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Appointment.objects.none()
        user = self.request.user
        return Appointment.objects.filter(
            Q(relationship__professional=user) | Q(relationship__patient=user)
        ).select_related('relationship__professional', 'relationship__patient')

    def _check_professional(self, appointment):
        if appointment.relationship.professional_id != self.request.user.id:
            raise exceptions.PermissionDenied()

    def perform_update(self, serializer):
        self._check_professional(serializer.instance)
        if serializer.instance.status != AppointmentStatus.SCHEDULED:
            raise exceptions.ValidationError(_('Only scheduled appointments can be changed.'))
        serializer.save()

    @extend_schema(request=None, responses=AppointmentSerializer)
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk):
        appointment = self.get_object()
        if appointment.status != AppointmentStatus.SCHEDULED:
            raise exceptions.ValidationError(_('Only scheduled appointments can be changed.'))
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_by = request.user
        appointment.save()
        return Response(self.get_serializer(appointment).data)

    @extend_schema(request=None, responses=AppointmentSerializer)
    @action(detail=True, methods=['post'])
    def done(self, request, pk):
        appointment = self.get_object()
        self._check_professional(appointment)
        if appointment.status != AppointmentStatus.SCHEDULED:
            raise exceptions.ValidationError(_('Only scheduled appointments can be changed.'))
        appointment.status = AppointmentStatus.DONE
        appointment.save()
        return Response(self.get_serializer(appointment).data)


class ModulesView(APIView):
    """
    The modules the app shows the current user, derived from their professionals
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=ModulesSerializer)
    def get(self, request):
        return Response(ModulesSerializer(policy.patient_modules(request.user)).data)

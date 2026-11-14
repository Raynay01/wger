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
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# Third Party
from rest_framework import serializers

# wger
from wger.care import policy
from wger.care.disciplines import COUNCIL_BY_DISCIPLINE
from wger.care.models import (
    PENDING_STATUSES,
    AccessGrant,
    Appointment,
    CareRelationship,
    ConsentRecord,
    DataRequest,
    Membership,
    MultidisciplinaryNote,
    Organization,
    ProfessionalRegistration,
)


class OrganizationSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'kind', 'document', 'is_active', 'created', 'my_role']
        read_only_fields = ['is_active', 'created']

    def get_my_role(self, obj) -> str | None:
        request = self.context.get('request')
        if request is None:
            return None
        membership = obj.memberships.filter(user=request.user, is_active=True).first()
        return membership.role if membership else None


class MembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, required=False)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            'id',
            'organization',
            'email',
            'username',
            'full_name',
            'role',
            'is_active',
            'created',
        ]
        read_only_fields = ['created']

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name()

    def validate(self, data):
        if self.instance is None:
            email = data.pop('email', None)
            if not email:
                raise serializers.ValidationError({'email': _('This field is required.')})
            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                raise serializers.ValidationError(
                    {'email': _('There is no user with this email address.')}
                )
            if Membership.objects.filter(organization=data['organization'], user=user).exists():
                raise serializers.ValidationError(
                    {'email': _('This user is already a member of the organization.')}
                )
            data['user'] = user
        else:
            data.pop('email', None)
            data.pop('organization', None)
        return data


class ProfessionalRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalRegistration
        fields = ['id', 'discipline', 'council', 'number', 'region', 'status', 'verified_at']
        read_only_fields = ['council', 'status', 'verified_at']

    def validate_region(self, value):
        value = value.upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError(_('Use the two letter code of the state.'))
        return value

    def validate(self, data):
        discipline = data.get('discipline', getattr(self.instance, 'discipline', None))
        if self.instance is not None and discipline != self.instance.discipline:
            raise serializers.ValidationError(
                {'discipline': _('The discipline of a registration cannot be changed.')}
            )
        user = self.context['request'].user
        others = ProfessionalRegistration.objects.filter(user=user, discipline=discipline)
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise serializers.ValidationError(
                {'discipline': _('You already have a registration for this discipline.')}
            )
        data['council'] = COUNCIL_BY_DISCIPLINE[discipline]
        return data


class CareRelationshipSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()
    professional_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    invitation_token = serializers.SerializerMethodField()

    class Meta:
        model = CareRelationship
        fields = [
            'id',
            'organization',
            'organization_name',
            'professional',
            'professional_name',
            'patient',
            'patient_name',
            'discipline',
            'status',
            'invited_email',
            'invitation_token',
            'invitation_sent_at',
            'created',
            'started',
            'ended',
            'my_role',
        ]
        read_only_fields = [
            'professional',
            'patient',
            'status',
            'invitation_sent_at',
            'created',
            'started',
            'ended',
        ]

    def _user(self):
        return self.context['request'].user

    def get_my_role(self, obj) -> str:
        return 'professional' if obj.professional_id == self._user().id else 'patient'

    def get_professional_name(self, obj) -> str:
        return obj.professional.get_full_name() or obj.professional.username

    def get_patient_name(self, obj) -> str | None:
        if obj.patient is None:
            return None
        return obj.patient.get_full_name() or obj.patient.username

    def get_invitation_token(self, obj) -> str | None:
        """Only the professional sees the token, to send the invitation link"""
        if obj.professional_id == self._user().id:
            return str(obj.invitation_token)
        return None

    def validate(self, data):
        if self.instance is not None:
            raise serializers.ValidationError(
                _('Use the actions to change the status of a relationship.')
            )

        user = self._user()
        organization = data['organization']
        discipline = data['discipline']
        email = data.get('invited_email')

        if not email:
            raise serializers.ValidationError({'invited_email': _('This field is required.')})
        if email.lower() == (user.email or '').lower():
            raise serializers.ValidationError(
                {'invited_email': _('You cannot follow yourself as a patient.')}
            )
        if not policy.is_caring_member(user, organization):
            raise serializers.ValidationError(
                {'organization': _('You cannot follow patients in this organization.')}
            )
        if not policy.has_registration(user, discipline):
            raise serializers.ValidationError(
                {'discipline': _('You need a council registration for this discipline.')}
            )

        duplicate = CareRelationship.objects.filter(
            professional=user,
            discipline=discipline,
            status__in=PENDING_STATUSES,
        ).filter(invited_email__iexact=email)
        existing = User.objects.filter(email__iexact=email).first()
        if existing is not None:
            duplicate = duplicate | CareRelationship.objects.filter(
                professional=user,
                discipline=discipline,
                status__in=PENDING_STATUSES,
                patient=existing,
            )
        if duplicate.exists():
            raise serializers.ValidationError(
                {'invited_email': _('You already follow or invited this patient.')}
            )
        return data


class AcceptInvitationSerializer(serializers.Serializer):
    accept_terms = serializers.BooleanField()
    token = serializers.UUIDField(required=False)

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError(
                _('You need to agree to be followed by this professional.')
            )
        return value


class AccessGrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessGrant
        fields = ['id', 'relationship', 'scope', 'granted_at', 'revoked_at', 'consent_version']
        read_only_fields = ['granted_at', 'revoked_at']

    def validate(self, data):
        relationship = data['relationship']
        if relationship.patient_id != self.context['request'].user.id:
            raise serializers.ValidationError(
                {'relationship': _('You can only share your own data.')}
            )
        if not relationship.is_open:
            raise serializers.ValidationError(
                {'relationship': _('This professional does not follow you anymore.')}
            )
        if AccessGrant.objects.filter(
            relationship=relationship,
            scope=data['scope'],
            revoked_at__isnull=True,
        ).exists():
            raise serializers.ValidationError({'scope': _('You already share this.')})
        return data


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = ['id', 'kind', 'version', 'reference', 'accepted_at', 'revoked_at']
        read_only_fields = ['accepted_at', 'revoked_at']


class MultidisciplinaryNoteSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    discipline = serializers.CharField(source='relationship.discipline', read_only=True)
    patient = serializers.IntegerField(source='relationship.patient_id', read_only=True)

    class Meta:
        model = MultidisciplinaryNote
        fields = [
            'id',
            'relationship',
            'patient',
            'author',
            'discipline',
            'category',
            'text',
            'visible_to_patient',
            'created',
            'updated',
        ]
        read_only_fields = ['created', 'updated']

    def get_author(self, obj) -> str:
        user = obj.relationship.professional
        return user.get_full_name() or user.username

    def validate_relationship(self, value):
        if self.instance is not None and value != self.instance.relationship:
            raise serializers.ValidationError(_('The relationship of a note cannot be changed.'))
        if value.professional_id != self.context['request'].user.id or not value.is_open:
            raise serializers.ValidationError(_('You do not follow this patient.'))
        return value


class DataRequestSerializer(serializers.ModelSerializer):
    confirm = serializers.BooleanField(write_only=True)

    class Meta:
        model = DataRequest
        fields = ['id', 'kind', 'status', 'created', 'completed_at', 'notes', 'confirm']
        read_only_fields = ['kind', 'status', 'created', 'completed_at', 'notes']

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError(
                _('Please confirm that you want to delete your account.')
            )
        return value


class AppointmentSerializer(serializers.ModelSerializer):
    professional = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    discipline = serializers.CharField(source='relationship.discipline', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id',
            'relationship',
            'kind',
            'start',
            'duration_minutes',
            'location',
            'notes',
            'status',
            'discipline',
            'professional',
            'patient',
            'created',
        ]
        read_only_fields = ['status', 'created']

    def get_professional(self, obj) -> str:
        user = obj.relationship.professional
        return user.get_full_name() or user.username

    def get_patient(self, obj) -> str | None:
        user = obj.relationship.patient
        return (user.get_full_name() or user.username) if user else None

    def validate_relationship(self, value):
        if self.instance is not None and value != self.instance.relationship:
            raise serializers.ValidationError(_('The patient of an appointment cannot be changed.'))
        if value.professional_id != self.context['request'].user.id or not value.is_open:
            raise serializers.ValidationError(_('You do not follow this patient.'))
        return value


class ModulesSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['guided', 'self'])
    modules = serializers.ListField(child=serializers.CharField())
    combined_view = serializers.BooleanField()


class MyDaySerializer(ModulesSerializer):
    date = serializers.DateField()
    training = serializers.DictField(allow_null=True)
    nutrition = serializers.DictField(allow_null=True)
    physio = serializers.DictField(allow_null=True)


class SharedDataSerializer(serializers.Serializer):
    scopes = serializers.ListField(child=serializers.CharField())
    data = serializers.DictField()

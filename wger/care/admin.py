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
from django.contrib import admin
from django.utils import timezone

# wger
from wger.care.models import (
    AccessGrant,
    AccessLog,
    CareRelationship,
    ConsentRecord,
    Membership,
    Organization,
    ProfessionalRegistration,
    VerificationStatus,
)


class MembershipInline(admin.TabularInline):
    model = Membership
    raw_id_fields = ('user',)
    extra = 0


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'document', 'is_active', 'created')
    list_filter = ('kind', 'is_active')
    search_fields = ('name', 'document')
    inlines = [MembershipInline]


@admin.register(ProfessionalRegistration)
class ProfessionalRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'discipline', 'council', 'number', 'region', 'status', 'verified_at')
    list_filter = ('status', 'discipline', 'region')
    search_fields = ('user__username', 'user__email', 'number')
    raw_id_fields = ('user',)
    actions = ['mark_verified', 'mark_rejected']

    @admin.action(description='Mark as verified')
    def mark_verified(self, request, queryset):
        queryset.update(status=VerificationStatus.VERIFIED, verified_at=timezone.now())

    @admin.action(description='Mark as rejected')
    def mark_rejected(self, request, queryset):
        queryset.update(status=VerificationStatus.REJECTED, verified_at=None)


@admin.register(CareRelationship)
class CareRelationshipAdmin(admin.ModelAdmin):
    list_display = ('professional', 'patient', 'invited_email', 'discipline', 'status', 'created')
    list_filter = ('discipline', 'status')
    raw_id_fields = ('professional', 'patient')


@admin.register(AccessGrant)
class AccessGrantAdmin(admin.ModelAdmin):
    list_display = ('relationship', 'scope', 'granted_at', 'revoked_at')
    list_filter = ('scope',)


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'kind', 'version', 'accepted_at', 'revoked_at')
    list_filter = ('kind',)
    raw_id_fields = ('user',)


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'patient', 'resource')
    raw_id_fields = ('actor', 'patient')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

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
Export of the personal data of a user (LGPD art. 18: access and portability)

Only the data about the user themselves: what a professional prescribed for
them is included, data of the patients a professional follows is not.
"""

# Standard Library
import datetime

# Django
from django.apps import apps
from django.contrib.auth.models import User
from django.utils import timezone

# wger
from wger.care.models import (
    AccessGrant,
    AccessLog,
    CareRelationship,
    ConsentRecord,
    DataRequest,
    Membership,
    Message,
    MultidisciplinaryNote,
    ProfessionalRegistration,
)


# (app label, model name, filter on the user) of the user's own data
OWN_DATA = (
    ('nutrition', 'NutritionPlan', 'user'),
    ('nutrition', 'Meal', 'plan__user'),
    ('nutrition', 'MealItem', 'meal__plan__user'),
    ('nutrition', 'SubstitutionOption', 'meal_item__meal__plan__user'),
    ('nutrition', 'LogItem', 'plan__user'),
    ('nutrition', 'MealAdherence', 'user'),
    ('nutrition', 'WaterLog', 'user'),
    ('manager', 'Routine', 'user'),
    ('manager', 'Day', 'routine__user'),
    ('manager', 'Slot', 'day__routine__user'),
    ('manager', 'SlotEntry', 'slot__day__routine__user'),
    ('manager', 'WorkoutSession', 'user'),
    ('manager', 'WorkoutLog', 'user'),
    ('manager', 'TrainingPlan', 'user'),
    ('manager', 'TrainingBlock', 'plan__user'),
    ('measurements', 'Category', 'user'),
    ('measurements', 'Measurement', 'category__user'),
    ('gallery', 'Image', 'user'),
    ('trophies', 'UserTrophy', 'user'),
    ('physio', 'PhysioProtocol', 'user'),
    ('physio', 'ProtocolExercise', 'protocol__user'),
    ('physio', 'PainRecord', 'user'),
    ('physio', 'ExerciseRecord', 'user'),
    ('physio', 'FunctionalAssessment', 'relationship__patient'),
    ('nutrition', 'NutritionalAnamnesis', 'relationship__patient'),
    ('nutrition', 'NutritionalAssessment', 'relationship__patient'),
)

ACCOUNT_FIELDS = ('id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'last_login')


def _rows(queryset) -> list[dict]:
    return list(queryset.values())


def export_user_data(user: User) -> dict:
    """Everything stored about the user, as plain JSON-ready structures"""
    relationships = CareRelationship.objects.filter(patient=user).select_related(
        'professional',
        'organization',
    )

    data = {
        'exported_at': timezone.now(),
        'account': {field: getattr(user, field) for field in ACCOUNT_FIELDS},
        'profile': _rows(apps.get_model('core', 'UserProfile').objects.filter(user=user)),
        'consents': _rows(ConsentRecord.objects.filter(user=user)),
        'data_requests': _rows(DataRequest.objects.filter(user=user)),
        'care': {
            'professionals': [
                {
                    'id': r.pk,
                    'professional': r.professional.get_full_name() or r.professional.username,
                    'organization': r.organization.name,
                    'discipline': r.discipline,
                    'status': r.status,
                    'started': r.started,
                    'ended': r.ended,
                }
                for r in relationships
            ],
            'sharing': _rows(AccessGrant.objects.filter(relationship__patient=user)),
            'messages': [
                {
                    'relationship': m.relationship_id,
                    'mine': m.sender_id == user.id,
                    'sender': (m.sender.get_full_name() or m.sender.username) if m.sender else None,
                    'text': m.text,
                    'attachment_name': m.attachment_name,
                    'exercise': m.exercise_id,
                    'created': m.created,
                    'reviewed_at': m.reviewed_at,
                }
                for m in Message.objects.filter(relationship__patient=user).select_related('sender')
            ],
            'notes_for_you': list(
                MultidisciplinaryNote.objects.filter(
                    relationship__patient=user,
                    visible_to_patient=True,
                ).values('category', 'text', 'created')
            ),
            'reads_of_your_shared_data': list(
                AccessLog.objects.filter(patient=user).values(
                    'timestamp',
                    'resource',
                    'actor__username',
                )
            ),
        },
        'as_professional': {
            'memberships': list(
                Membership.objects.filter(user=user).values(
                    'organization__name',
                    'role',
                    'is_active',
                    'created',
                )
            ),
            'registrations': _rows(ProfessionalRegistration.objects.filter(user=user)),
        },
    }

    for app_label, model_name, lookup in OWN_DATA:
        model = apps.get_model(app_label, model_name)
        data.setdefault(app_label, {})[model_name] = _rows(model.objects.filter(**{lookup: user}))
    return data


def export_filename(user: User) -> str:
    return f'dados-{user.username}-{datetime.date.today().isoformat()}.json'

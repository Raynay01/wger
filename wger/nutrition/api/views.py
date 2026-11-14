# -*- coding: utf-8 -*-

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
import logging

# Django
from django.conf import settings
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_page

# Third Party
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
)
from rest_framework import (
    exceptions,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# wger
from wger.care import policy
from wger.care.api.prescription import (
    PrescriptionViewSetMixin,
    PrescriptionWriteGuardMixin,
)
from wger.care.disciplines import Discipline
from wger.care.models import Membership
from wger.care.prescription import visible_prescriptions_q
from wger.nutrition import professional_foods
from wger.nutrition.api.filtersets import (
    IngredientFilterSet,
    LogItemFilterSet,
)
from wger.nutrition.api.serializers import (
    IngredientImageSerializer,
    IngredientInfoSerializer,
    IngredientSerializer,
    IngredientValuesSerializer,
    IngredientWeightUnitSerializer,
    LogItemSerializer,
    MealAdherenceSerializer,
    MealItemSerializer,
    MealSerializer,
    NutritionalValuesSerializer,
    NutritionPlanInfoSerializer,
    NutritionPlanSerializer,
    ProfessionalFoodSerializer,
    SubstitutionOptionSerializer,
    WaterLogSerializer,
)
from wger.nutrition.forms import UnitChooserForm
from wger.nutrition.models import (
    Image,
    Ingredient,
    IngredientWeightUnit,
    LogItem,
    Meal,
    MealAdherence,
    MealItem,
    NutritionPlan,
    ProfessionalFood,
    SubstitutionOption,
    WaterLog,
)
from wger.utils.pagination import (
    IngredientCursorPagination,
    IngredientLimitOffsetPagination,
)
from wger.utils.viewsets import WgerOwnerObjectModelViewSet


logger = logging.getLogger(__name__)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for ingredient objects. For a read-only endpoint with all
    the information of an ingredient, see /api/v2/ingredientinfo/
    """

    serializer_class = IngredientSerializer
    # Restrict ordering to indexed columns
    ordering_fields = (
        'id',
        'name',
        'code',
        'uuid',
        'remote_id',
        'last_update',
        'last_imported',
        'nutriscore',
    )
    filterset_class = IngredientFilterSet

    # Strip default ordering ('name'), this makes the API/DB more performant
    queryset = Ingredient.objects.prefetch_related('ingredientweightunit_set').order_by()
    pagination_class = IngredientLimitOffsetPagination
    throttle_scope = 'ingredient_list'

    def get_throttles(self):
        """
        Apply distinct throttle scopes to list and detail actions.

        List queries on a 3M-row table are expensive (sort, deep pagination);
        detail queries are cheap PK lookups. Separate buckets keep autocomplete
        and detail loads from competing for the same quota.
        """
        self.throttle_scope = 'ingredient_list' if self.action == 'list' else 'ingredient_detail'
        return super().get_throttles()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                'amount',
                OpenApiTypes.DECIMAL,
                OpenApiParameter.QUERY,
                required=True,
                description='The amount to calculate the values for',
            ),
            OpenApiParameter(
                'unit',
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description='ID of an ingredient weight unit. Defaults to grams.',
            ),
        ],
        responses={200: IngredientValuesSerializer},
    )
    @action(detail=True)
    def get_values(self, request, pk):
        """
        Calculates the nutritional values for current ingredient and
        the given amount and unit.

        This function basically just performs a multiplication (in the model), and
        is a candidate to be moved to pure AJAX calls, however doing it like this
        keeps the logic nicely hidden and respects the DRY principle.
        """

        result = {
            'energy': 0,
            'protein': 0,
            'carbohydrates': 0,
            'carbohydrates_sugar': 0,
            'fat': 0,
            'fat_saturated': 0,
            'fiber': 0,
            'sodium': 0,
            'errors': [],
        }
        ingredient = self.get_object()

        form = UnitChooserForm(request.GET)

        if form.is_valid():
            # Create a temporary MealItem object
            if form.cleaned_data['unit']:
                unit_id = form.cleaned_data['unit'].id
            else:
                unit_id = None

            item = MealItem()
            item.ingredient = ingredient
            item.weight_unit_id = unit_id
            item.amount = form.cleaned_data['amount']

            result = item.get_nutritional_values().to_dict
        else:
            result['errors'] = form.errors

        return Response(result)


class IngredientInfoViewSet(IngredientViewSet):
    """
    Read-only info API endpoint for ingredient objects. Returns nested data
    structures for more easy parsing.
    """

    serializer_class = IngredientInfoSerializer

    def get_queryset(self):
        """Optimize the queryset with select_related to avoid n+1 queries"""

        # See IngredientViewSet.queryset for the rationale behind .order_by().
        return (
            Ingredient.objects.select_related('language', 'license', 'image')
            .prefetch_related('ingredientweightunit_set')
            .order_by()
        )


class IngredientSyncAutoSchema(AutoSchema):
    """
    Gives the cursor-paginated response its own component.

    This endpoint shares its serializer with /api/v2/ingredientinfo/, so both
    wrappers would be called PaginatedIngredientInfoList. The cursor one has no
    count, and whichever is generated last wins.
    """

    def get_paginated_name(self, serializer_name: str) -> str:
        return f'Cursor{super().get_paginated_name(serializer_name)}'


class IngredientSyncViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Cursor-paginated read-only endpoint designed for syncing the ingredient
    catalogue.

    Unlike /api/v2/ingredient/, this endpoint uses cursor pagination so deep
    pagination stays fast and is intended for clients such as local wger instances.

    For incremental syncs, combine with the `last_update__gt` filter to only
    fetch ingredients that changed since that time.

    Note: the response does not contain a `count` key.
    """

    schema = IngredientSyncAutoSchema()
    serializer_class = IngredientInfoSerializer
    pagination_class = IngredientCursorPagination
    filterset_class = IngredientFilterSet
    throttle_scope = 'ingredient_sync'

    def get_queryset(self):
        return Ingredient.objects.select_related(
            'language',
            'license',
            'image',
        ).prefetch_related('ingredientweightunit_set')


class ImageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for ingredient images
    """

    serializer_class = IngredientImageSerializer
    ordering_fields = '__all__'
    filterset_fields = ('uuid', 'ingredient_id', 'ingredient__uuid')

    @method_decorator(cache_page(settings.WGER_SETTINGS['INGREDIENT_CACHE_TTL']))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Optimize the queryset"""

        return Image.objects.select_related('ingredient')


class IngredientWeightUnitViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for ingredient weight unit objects
    """

    queryset = IngredientWeightUnit.objects.all()
    serializer_class = IngredientWeightUnitSerializer
    ordering_fields = '__all__'
    filterset_fields = (
        'gram',
        'ingredient',
        'name',
    )


class NutritionPlanViewSet(PrescriptionViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for nutrition plan objects. For a read-only endpoint with all
    the information of nutritional plan(s), see /api/v2/nutritionplaninfo/

    A nutritionist creates a plan for a patient by passing ``care_relationship``;
    it stays a draft, invisible to the patient, until published.
    """

    serializer_class = NutritionPlanSerializer
    is_private = True
    ordering_fields = '__all__'
    filterset_fields = (
        'creation_date',
        'description',
        'has_goal_calories',
        'status',
        'care_relationship',
        'lineage_id',
    )

    def get_queryset(self):
        """
        Only allow access to appropriate objects
        """
        # REST API generation
        if getattr(self, 'swagger_fake_view', False):
            return NutritionPlan.objects.none()

        return NutritionPlan.objects.filter(visible_prescriptions_q(self.request.user))

    def perform_create(self, serializer):
        """
        Set the owner
        """
        serializer.save(user=self.request.user)

    @extend_schema(responses={200: NutritionalValuesSerializer})
    @action(detail=True)
    def nutritional_values(self, request, pk):
        """
        Return an overview of the nutritional plan's values
        """
        serializer = NutritionalValuesSerializer(
            self.get_object().get_nutritional_values()['total'],
        )
        return Response(serializer.data)

    @staticmethod
    def get_owner_objects():
        return []


class NutritionPlanInfoViewSet(NutritionPlanViewSet):
    """
    Read-only info API endpoint for nutrition plan objects. Returns nested data
    structures for more easy parsing.
    """

    serializer_class = NutritionPlanInfoSerializer
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        """
        Prefetch the nutritional plan sub-objects
        """
        # REST API generation
        if getattr(self, 'swagger_fake_view', False):
            return NutritionPlan.objects.none()

        return NutritionPlan.objects.filter(
            visible_prescriptions_q(self.request.user)
        ).prefetch_related(
            Prefetch(
                'meal_set',
                queryset=Meal.objects.prefetch_related(
                    Prefetch(
                        'mealitem_set',
                        queryset=MealItem.objects.select_related(
                            'ingredient',
                            'ingredient__language',
                            'ingredient__license',
                            'ingredient__image',
                            'weight_unit',
                        ).prefetch_related(
                            Prefetch(
                                'ingredient__ingredientweightunit_set',
                                queryset=IngredientWeightUnit.objects.select_related('ingredient'),
                            ),
                            Prefetch(
                                'substitutions',
                                queryset=SubstitutionOption.objects.select_related('ingredient'),
                            ),
                        ),
                    ),
                ),
            ),
        )


class MealViewSet(PrescriptionWriteGuardMixin, WgerOwnerObjectModelViewSet):
    """
    API endpoint for meal objects
    """

    prescription_children = True

    serializer_class = MealSerializer
    is_private = True
    ordering_fields = '__all__'
    filterset_fields = (
        'order',
        'plan',
        'time',
    )

    def get_queryset(self):
        """
        Only allow access to appropriate objects
        """
        # REST API generation
        if getattr(self, 'swagger_fake_view', False):
            return Meal.objects.none()

        return Meal.objects.filter(visible_prescriptions_q(self.request.user, 'plan__'))

    def perform_create(self, serializer):
        """
        Set the order
        """
        serializer.save(order=1)

    @staticmethod
    def get_owner_objects():
        """
        Return objects to check for ownership permission
        """
        return [(NutritionPlan, 'plan')]

    @extend_schema(responses={200: NutritionalValuesSerializer})
    @action(detail=True)
    def nutritional_values(self, request, pk):
        """
        Return an overview of the nutritional plan's values
        """
        serializer = NutritionalValuesSerializer(self.get_object().get_nutritional_values())
        return Response(serializer.data)


class MealItemViewSet(PrescriptionWriteGuardMixin, WgerOwnerObjectModelViewSet):
    """
    API endpoint for meal item objects
    """

    prescription_children = True

    serializer_class = MealItemSerializer
    is_private = True
    ordering_fields = '__all__'
    filterset_fields = (
        'amount',
        'ingredient',
        'meal',
        'order',
        'weight_unit',
    )

    def get_queryset(self):
        """
        Only allow access to appropriate objects
        """
        # REST API generation
        if getattr(self, 'swagger_fake_view', False):
            return MealItem.objects.none()

        return MealItem.objects.filter(visible_prescriptions_q(self.request.user, 'meal__plan__'))

    def perform_create(self, serializer):
        """
        Set the order
        """
        serializer.save(order=1)

    @staticmethod
    def get_owner_objects():
        """
        Return objects to check for ownership permission
        """
        return [(Meal, 'meal')]

    @extend_schema(responses={200: NutritionalValuesSerializer})
    @action(detail=True)
    def nutritional_values(self, request, pk):
        """
        Return an overview of the nutritional plan's values
        """
        serializer = NutritionalValuesSerializer(self.get_object().get_nutritional_values())
        return Response(serializer.data)


class LogItemViewSet(WgerOwnerObjectModelViewSet):
    """
    API endpoint for a meal log item
    """

    serializer_class = LogItemSerializer
    is_private = True
    ordering_fields = '__all__'
    filterset_class = LogItemFilterSet

    def get_queryset(self):
        """
        Only allow access to appropriate objects
        """
        # REST API generation
        if getattr(self, 'swagger_fake_view', False):
            return LogItem.objects.none()

        return LogItem.objects.select_related('plan').filter(plan__user=self.request.user)

    @staticmethod
    def get_owner_objects():
        """
        Return objects to check for ownership permission
        """
        return [(NutritionPlan, 'plan'), (Meal, 'meal')]

    @extend_schema(responses={200: NutritionalValuesSerializer})
    @action(detail=True)
    def nutritional_values(self, request, pk):
        """
        Return an overview of the nutritional plan's values
        """
        serializer = NutritionalValuesSerializer(self.get_object().get_nutritional_values())
        return Response(serializer.data)


class SubstitutionOptionViewSet(PrescriptionWriteGuardMixin, WgerOwnerObjectModelViewSet):
    """
    API endpoint for the substitution options of a meal item. Only whoever
    writes the plan adds them, the patient only reads the approved ones.
    """

    serializer_class = SubstitutionOptionSerializer
    is_private = True
    prescription_children = True
    filterset_fields = ('meal_item', 'ingredient', 'criterion')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SubstitutionOption.objects.none()

        return SubstitutionOption.objects.filter(
            visible_prescriptions_q(self.request.user, 'meal_item__meal__plan__')
        )

    @staticmethod
    def get_owner_objects():
        return [(MealItem, 'meal_item')]


class MealAdherenceViewSet(WgerOwnerObjectModelViewSet):
    """
    API endpoint to record whether a prescribed meal was followed on a day.
    There is one record per meal and day: posting again updates it.
    """

    serializer_class = MealAdherenceSerializer
    is_private = True
    filterset_fields = ('meal', 'date', 'status')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return MealAdherence.objects.none()

        return MealAdherence.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        self._check_owner_permission(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        instance, created = MealAdherence.objects.update_or_create(
            user=request.user,
            meal=data['meal'],
            date=data['date'],
            defaults={'status': data['status'], 'notes': data.get('notes', '')},
        )
        return Response(
            self.get_serializer(instance).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @staticmethod
    def get_owner_objects():
        return [(Meal, 'meal')]


class WaterLogViewSet(WgerOwnerObjectModelViewSet):
    """
    API endpoint for the water the user drank
    """

    serializer_class = WaterLogSerializer
    is_private = True
    filterset_fields = {
        'datetime': ['exact', 'gt', 'gte', 'lt', 'lte'],
    }

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return WaterLog.objects.none()

        return WaterLog.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @staticmethod
    def get_owner_objects():
        return []


class ProfessionalFoodViewSet(viewsets.ModelViewSet):
    """
    Foods added to the shared food database by the nutritionists of the user's
    organizations. They are visible to everyone like any other food; only the
    organization changes them, and only while no published plan or diary uses them.
    """

    serializer_class = ProfessionalFoodSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ('organization',)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ProfessionalFood.objects.none()
        organizations = Membership.objects.filter(
            user=self.request.user,
            is_active=True,
        ).values('organization')
        return ProfessionalFood.objects.filter(organization__in=organizations).select_related(
            'ingredient',
            'author',
        )

    @staticmethod
    def _values(data: dict) -> dict:
        fields = data.get('ingredient', {})
        return {f: fields[f] for f in professional_foods.VALUE_FIELDS if f in fields}

    def perform_create(self, serializer):
        data = serializer.validated_data
        organization = data['organization']
        if not policy.is_caring_member(
            self.request.user, organization
        ) or not policy.has_registration(self.request.user, Discipline.NUTRITION):
            raise exceptions.ValidationError(
                {'organization': _('Only nutritionists of the organization can add foods.')}
            )
        try:
            food = professional_foods.create_food(
                organization=organization,
                author=self.request.user,
                name=data['ingredient']['name'],
                brand=data['ingredient'].get('brand', ''),
                values=self._values(data),
                based_on=data.get('based_on'),
            )
        except ValueError as error:
            raise exceptions.ValidationError({'detail': str(error)})
        serializer.instance = food

    def perform_update(self, serializer):
        food = serializer.instance
        if professional_foods.in_use(food.ingredient):
            raise exceptions.ValidationError(
                _('This food is already used in published plans or diaries. Add a new one instead.')
            )
        data = serializer.validated_data
        try:
            professional_foods.update_food(
                food, data.get('name'), data.get('brand'), self._values(data)
            )
        except ValueError as error:
            raise exceptions.ValidationError({'detail': str(error)})

    def perform_destroy(self, instance):
        if professional_foods.referenced(instance.ingredient):
            raise exceptions.ValidationError(_('This food is used in plans or diaries.'))
        instance.ingredient.delete()

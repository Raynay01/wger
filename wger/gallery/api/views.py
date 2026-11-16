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

# Third Party
from drf_spectacular.utils import extend_schema
from rest_framework import (
    exceptions,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated

# wger
from wger.care.messages import attachment_response
from wger.gallery.api.serializers import ImageSerializer
from wger.gallery.files import image_storage
from wger.gallery.models import Image


logger = logging.getLogger(__name__)


class GalleryImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for gallery image
    """

    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]
    serializer_class = ImageSerializer
    is_private = True
    ordering_fields = '__all__'
    filterset_fields = (
        'id',
        'date',
        'description',
    )

    def get_queryset(self):
        """
        Only allow access to appropriate objects
        """
        # REST API generation
        if getattr(self, 'swagger_fake_view', False):
            return Image.objects.none()

        return Image.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Set the owner
        """
        serializer.save(user=self.request.user)

    @extend_schema(responses={(200, 'application/octet-stream'): bytes})
    @action(detail=True, methods=['get'])
    def file(self, request, pk):
        """The image file, only for its owner (the files are not public)"""
        image = self.get_object()
        storage = image_storage(image.image.name)
        if storage is None:
            raise exceptions.NotFound()
        image.image.storage = storage
        return attachment_response(request, image.image)

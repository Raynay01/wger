# Django
from django.urls import reverse

# Third Party
from rest_framework import serializers

# wger
from wger.gallery.models import Image
from wger.utils.images import validate_image_static_no_animation


class GalleryFileField(serializers.ImageField):
    """The upload; reads give the address that serves the file to its owner"""

    def to_representation(self, value):
        if not value:
            return None
        url = reverse('gallery-file', kwargs={'pk': value.instance.pk})
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url


class ImageSerializer(serializers.ModelSerializer):
    """
    Gallery image serializer
    """

    image = GalleryFileField(validators=[validate_image_static_no_animation])

    class Meta:
        model = Image
        fields = ('id', 'date', 'image', 'description', 'height', 'width')

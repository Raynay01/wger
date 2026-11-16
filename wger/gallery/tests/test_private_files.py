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
import io
import os
import tempfile

# Django
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

# Third Party
from PIL import Image as PillowImage
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.core.tests.base_testcase import BaseTestCase
from wger.gallery.models import Image


def jpeg() -> io.BytesIO:
    data = io.BytesIO()
    PillowImage.new('RGB', (40, 30), 'red').save(data, 'JPEG')
    data.seek(0)
    data.name = 'progresso.jpg'
    return data


class PrivateGalleryFilesTestCase(BaseTestCase, APITestCase):
    """
    Progress photos are stored outside the public media and served only to
    their owner; photos from before are served from the public media until
    copy-gallery-to-private copies them
    """

    def setUp(self):
        super().setUp()
        self.private_root = tempfile.mkdtemp()
        self.media_root = tempfile.mkdtemp()
        settings = override_settings(
            PRIVATE_MEDIA_ROOT=self.private_root,
            MEDIA_ROOT=self.media_root,
        )
        settings.enable()
        self.addCleanup(settings.disable)
        self.owner = User.objects.get(username='test')
        self.other = User.objects.get(username='admin')

    def upload(self) -> dict:
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse('gallery-list'),
            {'date': '2026-11-16', 'description': 'Semana 4', 'image': jpeg()},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def fetch(self, user, pk):
        self.client.force_authenticate(user)
        return self.client.get(reverse('gallery-file', kwargs={'pk': pk}))

    def test_upload_is_private(self):
        data = self.upload()
        name = Image.objects.get(pk=data['id']).image.name
        self.assertTrue(os.path.exists(os.path.join(self.private_root, name)))
        self.assertFalse(default_storage.exists(name))
        self.assertTrue(data['image'].endswith(reverse('gallery-file', kwargs={'pk': data['id']})))

        response = self.fetch(self.owner, data['id'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(
            b''.join(response.streaming_content if response.streaming else [response.content])[:2],
            b'\xff\xd8',
        )

        self.assertEqual(self.fetch(self.other, data['id']).status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(None)
        self.assertIn(
            self.client.get(reverse('gallery-file', kwargs={'pk': data['id']})).status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_delete_removes_the_private_file(self):
        data = self.upload()
        name = Image.objects.get(pk=data['id']).image.name
        self.client.delete(reverse('gallery-detail', kwargs={'pk': data['id']}))
        self.assertFalse(os.path.exists(os.path.join(self.private_root, name)))

    def legacy_image(self) -> Image:
        """A photo uploaded before, still in the public media"""
        image = Image.objects.filter(user=self.owner).first()
        self.assertEqual(default_storage.save(image.image.name, jpeg()), image.image.name)
        self.addCleanup(default_storage.delete, image.image.name)
        return image

    def test_copy_command(self):
        image = self.legacy_image()
        private = os.path.join(self.private_root, image.image.name)
        # Served from the public media until copied
        self.assertEqual(self.fetch(self.owner, image.pk).status_code, status.HTTP_200_OK)

        out = io.StringIO()
        call_command('copy-gallery-to-private', stdout=out, stderr=io.StringIO())
        self.assertIn('Copied: 1', out.getvalue())
        self.assertTrue(os.path.exists(private))
        self.assertTrue(default_storage.exists(image.image.name))
        self.assertEqual(self.fetch(self.owner, image.pk).status_code, status.HTTP_200_OK)

        # Again: nothing to copy, the originals go only on request
        out = io.StringIO()
        call_command('copy-gallery-to-private', '--delete-public', stdout=out, stderr=io.StringIO())
        self.assertIn('Copied: 0', out.getvalue())
        self.assertIn('public copies deleted: 1', out.getvalue())
        self.assertFalse(default_storage.exists(image.image.name))
        self.assertTrue(os.path.exists(private))
        self.assertEqual(self.fetch(self.owner, image.pk).status_code, status.HTTP_200_OK)

    def test_missing_file(self):
        image = Image.objects.filter(user=self.owner).first()
        self.assertEqual(self.fetch(self.owner, image.pk).status_code, status.HTTP_404_NOT_FOUND)

    def test_overview_page_links_the_served_file(self):
        image = self.legacy_image()
        self.client.force_login(self.owner)
        response = self.client.get(reverse('gallery:images:overview'))
        self.assertContains(response, reverse('gallery-file', kwargs={'pk': image.pk}))
        self.assertNotContains(response, '/media/gallery/')

    def test_upload_is_validated(self):
        gif = io.BytesIO()
        PillowImage.new('RGB', (40, 30), 'blue').save(gif, 'GIF')
        gif.seek(0)
        gif.name = 'progresso.gif'
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse('gallery-list'),
            {'date': '2026-11-16', 'image': gif},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('image', response.data)

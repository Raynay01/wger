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
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

# wger
from wger.care.storage import private_storage
from wger.gallery.models import Image


class Command(BaseCommand):
    """
    Copies the gallery images from the public media to the private storage
    """

    help = (
        'Copies the files of the gallery images from the public media to the '
        'private storage, keeping the originals. Run it again any time: files '
        'already copied are skipped. --delete-public then removes the public '
        'copies that have an identical private one.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-public',
            action='store_true',
            help='Remove the public files whose private copy has the same size',
        )

    def handle(self, **options):
        copied = present = missing = deleted = 0
        for name in Image.objects.exclude(image='').values_list('image', flat=True):
            public = default_storage.exists(name)
            if private_storage.exists(name):
                present += 1
            elif public:
                with default_storage.open(name, 'rb') as source:
                    saved = private_storage.save(name, source)
                if saved != name:
                    private_storage.delete(saved)
                    raise RuntimeError(f'{name} was stored as {saved}')
                copied += 1
            else:
                missing += 1
                self.stderr.write(f'Missing: {name}')
                continue

            if (
                options['delete_public']
                and public
                and default_storage.size(name) == private_storage.size(name)
            ):
                default_storage.delete(name)
                deleted += 1

        self.stdout.write(
            f'Copied: {copied}, already private: {present}, missing: {missing}, '
            f'public copies deleted: {deleted}'
        )

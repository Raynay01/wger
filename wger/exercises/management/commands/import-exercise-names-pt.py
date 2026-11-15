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
from django.core.management.base import BaseCommand

# wger
from wger.exercises.portuguese_names import (
    import_names,
    load_names,
)


class Command(BaseCommand):
    """
    Adds Brazilian Portuguese names to the exercises without a Portuguese
    translation. Run it after syncing the exercises; running it again updates
    the names it created and never touches translations from wger.de.
    """

    help = 'Adds Brazilian Portuguese names to exercises without a Portuguese translation'

    def handle(self, **options):
        result = import_names(load_names())
        self.stdout.write(
            self.style.SUCCESS(
                f'Created {result.created}, updated {result.updated}, '
                f'unchanged {result.unchanged}; kept {result.kept_upstream} translations '
                f'from wger.de; {result.unknown} exercises not in this database'
            )
        )

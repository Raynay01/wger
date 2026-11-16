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
from wger.care.notifications import notify_unread_messages


class Command(BaseCommand):
    """
    Emails about unread messages. Celery runs it every 5 minutes; without
    Celery, run this command from cron at the same pace.
    """

    help = 'Emails people about messages unread for a few minutes'

    def handle(self, **options):
        self.stdout.write(f'Emails sent: {notify_unread_messages()}')

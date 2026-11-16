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
from celery.schedules import crontab

# wger
from wger.care.notifications import notify_unread_messages
from wger.celery_configuration import app


logger = logging.getLogger(__name__)


@app.task
def notify_unread_messages_task():
    """Emails about messages unread for a few minutes"""
    sent = notify_unread_messages()
    if sent:
        logger.info('Sent %s emails about new messages', sent)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute='*/5'),
        notify_unread_messages_task.s(),
        name='Email about unread messages',
    )

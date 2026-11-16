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
import datetime

# Django
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

# Third Party
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.export import export_user_data
from wger.care.models import (
    Message,
    NotificationLog,
    NotificationPreference,
)
from wger.care.notifications import (
    MESSAGE_DELAY,
    MESSAGE_INTERVAL,
    notify_prescription_published,
    notify_unread_messages,
)
from wger.care.prescription import start_prescription
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.manager.models import Routine


@override_settings(WEB_APP_URL='https://app.almova.com.br/', WEB_APP_NAME='ALMOVA')
class MessageNoticeTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """
    One email per conversation about messages still unread after a few
    minutes, without their content
    """

    def setUp(self):
        super().setUp()
        self.build_team()
        self.now = timezone.now()

    def message(self, minutes_ago: int, sender=None, read=False):
        return Message.objects.create(
            relationship=self.training_rel,
            sender=sender or self.patient,
            text='Meu joelho doeu no agachamento',
            created=self.now - datetime.timedelta(minutes=minutes_ago),
            read_at=self.now if read else None,
        )

    def test_unread_after_the_delay(self):
        self.message(minutes_ago=10)
        self.assertEqual(notify_unread_messages(self.now), 1)
        (email,) = mail.outbox
        self.assertEqual(email.to, [self.trainer.email])
        self.assertIn('ALMOVA', email.subject)
        self.assertIn(f'https://app.almova.com.br/pro/mensagens/{self.training_rel.pk}', email.body)
        self.assertNotIn('joelho', email.body)
        self.assertNotIn('joelho', email.subject)
        log = NotificationLog.objects.get()
        self.assertEqual((log.user, log.kind), (self.trainer, 'messages'))

    def test_to_the_patient(self):
        self.message(minutes_ago=10, sender=self.trainer)
        notify_unread_messages(self.now)
        (email,) = mail.outbox
        self.assertEqual(email.to, [self.patient.email])
        self.assertIn(f'/app/mensagens/{self.training_rel.pk}', email.body)

    def test_not_before_the_delay_nor_when_read(self):
        self.message(minutes_ago=MESSAGE_DELAY.seconds // 60 - 1)
        self.message(minutes_ago=30, read=True)
        self.assertEqual(notify_unread_messages(self.now), 0)
        self.assertEqual(mail.outbox, [])

    def test_once_per_conversation_and_interval(self):
        self.message(minutes_ago=20)
        self.message(minutes_ago=10)
        self.assertEqual(notify_unread_messages(self.now), 1)
        # A message after the email: nothing within the interval
        self.message(minutes_ago=-10)
        self.assertEqual(notify_unread_messages(self.now + datetime.timedelta(minutes=20)), 0)
        # After the interval, one more email, then none while nothing new arrives
        self.assertEqual(notify_unread_messages(self.now + MESSAGE_INTERVAL), 1)
        self.assertEqual(notify_unread_messages(self.now + 3 * MESSAGE_INTERVAL), 0)
        self.assertEqual(len(mail.outbox), 2)

    def test_turned_off_or_without_email(self):
        self.message(minutes_ago=10)
        self.message(minutes_ago=10, sender=self.trainer)
        NotificationPreference.objects.create(user=self.trainer, email_messages=False)
        self.patient.email = ''
        self.patient.save()
        self.assertEqual(notify_unread_messages(self.now), 0)
        self.assertFalse(NotificationLog.objects.exists())

    def test_command(self):
        Message.objects.create(
            relationship=self.training_rel,
            sender=self.patient,
            text='Oi',
            created=timezone.now() - datetime.timedelta(minutes=10),
        )
        call_command('send-message-notices', stdout=open('/dev/null', 'w'))
        self.assertEqual(len(mail.outbox), 1)


@override_settings(WEB_APP_URL='https://app.almova.com.br')
class UpdateNoticeTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """Published plans and appointments are told to the other side"""

    def setUp(self):
        super().setUp()
        self.build_team()
        self.patient.userprofile.time_zone = 'America/Sao_Paulo'
        self.patient.userprofile.save()

    def test_published_plan(self):
        routine = Routine(name='Hipertrofia para o joelho', start=datetime.date(2026, 3, 9))
        start_prescription(routine, self.training_rel, self.trainer)
        routine.end = routine.start + datetime.timedelta(days=27)
        routine.save()
        self.client.force_authenticate(self.trainer)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('routine-publish', kwargs={'pk': routine.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        (email,) = mail.outbox
        self.assertEqual(email.to, [self.patient.email])
        self.assertIn('https://app.almova.com.br/app', email.body)
        self.assertNotIn('joelho', email.body.lower())

    def test_published_plan_turned_off(self):
        NotificationPreference.objects.create(user=self.patient, email_prescriptions=False)
        routine = Routine(name='Força', start=datetime.date(2026, 3, 9))
        start_prescription(routine, self.training_rel, self.trainer)
        routine.end = routine.start + datetime.timedelta(days=27)
        routine.save()
        self.client.force_authenticate(self.trainer)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('routine-publish', kwargs={'pk': routine.pk}))
        self.assertEqual(mail.outbox, [])

    def test_own_plan_is_not_told(self):
        """A plan the patient made needs no notice"""
        routine = Routine.objects.create(
            user=self.patient,
            name='Meu treino',
            start=datetime.date(2026, 3, 9),
            end=datetime.date(2026, 4, 9),
        )
        self.assertFalse(notify_prescription_published(routine))
        self.assertEqual(mail.outbox, [])

    def schedule(self):
        self.client.force_authenticate(self.physio)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse('appointment-list'),
                {
                    'relationship': str(self.physio_rel.pk),
                    'kind': 'session',
                    'start': '2026-03-10T14:00:00-03:00',
                    'duration_minutes': 50,
                },
            )

    def test_appointment_scheduled_changed_and_cancelled(self):
        pk = self.schedule().data['id']
        self.assertEqual(mail.outbox[-1].to, [self.patient.email])
        # The time in the patient's time zone
        self.assertIn('10/03/2026 14:00', mail.outbox[-1].body)
        self.assertIn('https://app.almova.com.br/app/agenda', mail.outbox[-1].body)

        detail = reverse('appointment-detail', kwargs={'pk': pk})
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(detail, {'duration_minutes': 30})
        self.assertEqual(len(mail.outbox), 1)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(detail, {'start': '2026-03-11T09:30:00-03:00'})
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('11/03/2026 09:30', mail.outbox[-1].body)

        # Cancelled by the patient: the physiotherapist is told
        self.client.force_authenticate(self.patient)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('appointment-cancel', kwargs={'pk': pk}))
        self.assertEqual(mail.outbox[-1].to, [self.physio.email])
        self.assertIn('/pro/agenda', mail.outbox[-1].body)
        self.assertEqual(NotificationLog.objects.filter(kind='appointment').count(), 3)

    def test_export_lists_the_notices(self):
        self.schedule()
        exported = export_user_data(self.patient)['care']
        self.assertEqual([n['kind'] for n in exported['notices_sent']], ['appointment'])


class NoticePreferenceTestCase(CareScenarioMixin, BaseTestCase, APITestCase):
    """Each person turns their email notices on and off"""

    def setUp(self):
        super().setUp()
        self.build_team()
        self.url = reverse('care-notices')

    def test_defaults_and_change(self):
        self.client.force_authenticate(self.patient)
        self.assertEqual(
            self.client.get(self.url).data,
            {
                'email_messages': True,
                'email_prescriptions': True,
                'email_appointments': True,
                'push_messages': True,
                'push_prescriptions': True,
                'push_appointments': True,
            },
        )
        response = self.client.patch(self.url, {'email_messages': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.client.get(self.url).data['email_messages'])
        self.assertTrue(self.client.get(self.url).data['email_appointments'])

        # Someone else keeps their own choices
        self.client.force_authenticate(self.trainer)
        self.assertTrue(self.client.get(self.url).data['email_messages'])

    def test_login_required(self):
        self.assertIn(
            self.client.get(self.url).status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

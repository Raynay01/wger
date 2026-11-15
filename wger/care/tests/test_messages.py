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
import pathlib
import tempfile

# Django
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

# Third Party
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

# wger
from wger.care.export import export_user_data
from wger.care.models import (
    Message,
    RelationshipStatus,
)
from wger.care.tests.helpers import CareScenarioMixin
from wger.core.tests.base_testcase import BaseTestCase
from wger.exercises.models import Exercise


VIDEO = b'\x00\x00\x00\x18ftypmp42' + bytes(range(256)) * 4


def png_upload(name: str = 'foto.jpg') -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), 'red').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


class MessageScenarioMixin(CareScenarioMixin):
    """The care team, private media in a temporary folder and chat helpers"""

    def setUp(self):
        super().setUp()
        self.build_team()
        self.private_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.private_root.cleanup)
        media_root = tempfile.TemporaryDirectory()
        self.addCleanup(media_root.cleanup)
        settings = override_settings(
            PRIVATE_MEDIA_ROOT=self.private_root.name,
            MEDIA_ROOT=media_root.name,
        )
        settings.enable()
        self.addCleanup(settings.disable)
        self.media_root = media_root.name
        self.url = reverse('care-message-list')

    def send(self, user, relationship=None, **data):
        self.client.force_authenticate(user)
        data['relationship'] = str((relationship or self.training_rel).pk)
        return self.client.post(self.url, data, format='multipart')

    def messages(self, user, relationship=None):
        self.client.force_authenticate(user)
        params = {'relationship': str((relationship or self.training_rel).pk)}
        return self.client.get(self.url, params).data['results']

    def attachment(self, user, message_id, **headers):
        self.client.force_authenticate(user)
        return self.client.get(
            reverse('care-message-attachment', kwargs={'pk': message_id}),
            **headers,
        )


class MessageTestCase(MessageScenarioMixin, BaseTestCase, APITestCase):
    """
    Chat between the patient and the professional of a follow-up
    """

    def test_conversation(self):
        """Both sides see the messages in order, each marked as theirs or not"""
        self.assertEqual(self.send(self.patient, text='Posso treinar hoje?').status_code, 201)
        self.assertEqual(self.send(self.trainer, text='  Pode, leve.  ').status_code, 201)

        result = self.messages(self.patient)
        self.assertEqual([m['text'] for m in result], ['Posso treinar hoje?', 'Pode, leve.'])
        self.assertEqual([m['mine'] for m in result], [True, False])
        self.assertEqual(result[1]['sender_name'], 'rp_trainer')
        self.assertEqual([m['mine'] for m in self.messages(self.trainer)], [False, True])

    def test_other_professionals_and_strangers(self):
        """Only the two people of the follow-up read and write in it"""
        self.send(self.patient, text='Dor no joelho')

        self.assertEqual(self.messages(self.physio), [])
        response = self.send(self.physio, text='Oi')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('relationship', response.data)
        self.assertEqual(Message.objects.count(), 1)

    def test_ended_follow_up(self):
        """After the end, nobody writes, both still read the history"""
        self.send(self.patient, text='Obrigado!')
        self.training_rel.status = RelationshipStatus.ENDED
        self.training_rel.save()

        self.assertEqual(self.send(self.trainer, text='De nada').status_code, 400)
        self.assertEqual(len(self.messages(self.trainer)), 1)
        self.assertEqual(len(self.messages(self.patient)), 1)

    def test_empty_message(self):
        response = self.send(self.patient, text='   ')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_photo(self):
        """
        A photo is stored outside MEDIA_ROOT with the extension of its real
        format and served only to the two people of the follow-up
        """
        response = self.send(self.patient, attachment=png_upload('agachamento.jpg'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['attachment_kind'], 'image')
        self.assertEqual(response.data['attachment_name'], 'agachamento.jpg')
        self.assertNotIn('attachment', response.data)

        message = Message.objects.get()
        stored = pathlib.Path(message.attachment.path)
        self.assertEqual(stored.suffix, '.png')
        self.assertTrue(stored.is_relative_to(self.private_root.name))
        self.assertEqual(list(pathlib.Path(self.media_root).rglob('*.*')), [])

        served = self.attachment(self.trainer, message.pk)
        self.assertEqual(served.status_code, status.HTTP_200_OK)
        self.assertEqual(served['Content-Type'], 'image/png')
        self.assertEqual(served['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.attachment(self.physio, message.pk).status_code, 404)

    def test_video_range(self):
        """Videos can be read in parts, which browsers use for seeking"""
        response = self.send(
            self.patient,
            text='Minha execução',
            attachment=SimpleUploadedFile('execucao.mp4', VIDEO, content_type='video/mp4'),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['attachment_kind'], 'video')

        part = self.attachment(self.trainer, response.data['id'], HTTP_RANGE='bytes=4-11')
        self.assertEqual(part.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(part['Content-Type'], 'video/mp4')
        self.assertEqual(part['Content-Range'], f'bytes 4-11/{len(VIDEO)}')
        self.assertEqual(b''.join(part.streaming_content), VIDEO[4:12])

        tail = self.attachment(self.trainer, response.data['id'], HTTP_RANGE='bytes=-10')
        self.assertEqual(b''.join(tail.streaming_content), VIDEO[-10:])

        beyond = self.attachment(self.trainer, response.data['id'], HTTP_RANGE='bytes=99999-')
        self.assertEqual(beyond.status_code, status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)

        whole = self.attachment(self.trainer, response.data['id'])
        self.assertEqual(whole.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(whole.streaming_content), VIDEO)

    def test_rejected_files(self):
        """Files that are not photos or videos are refused"""
        for name, content in (
            ('execucao.mp4', b'not a video at all'),
            ('foto.jpg', b'not an image'),
            ('desenho.svg', b'<svg xmlns="http://www.w3.org/2000/svg"/>'),
            ('exame.pdf', b'%PDF-1.4'),
        ):
            with self.subTest(name=name):
                response = self.send(self.patient, attachment=SimpleUploadedFile(name, content))
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('attachment', response.data)
        self.assertFalse(Message.objects.exists())

    def test_unread_and_read(self):
        """Unread counts per follow-up; reading marks only what the other side sent"""
        self.send(self.trainer, text='Bom dia')
        self.send(self.trainer, text='Como foi o treino?')
        self.send(self.nutritionist, relationship=self.nutrition_rel, text='Beba água')
        self.send(self.patient, text='Foi bem')

        self.client.force_authenticate(self.patient)
        unread = self.client.get(reverse('care-message-unread')).data
        self.assertEqual(unread, {str(self.training_rel.pk): 2, str(self.nutrition_rel.pk): 1})

        read_url = reverse('care-message-read')
        response = self.client.post(read_url, {'relationship': str(self.training_rel.pk)})
        self.assertEqual(response.data, {'marked': 2})
        unread = self.client.get(reverse('care-message-unread')).data
        self.assertEqual(unread, {str(self.nutrition_rel.pk): 1})

        self.client.force_authenticate(self.trainer)
        self.assertEqual(
            self.client.get(reverse('care-message-unread')).data, {str(self.training_rel.pk): 1}
        )

        # The trainer, followed by the nutritionist as a patient
        self.follow(self.nutritionist, self.trainer, 'nutrition')
        self.send(self.nutritionist, relationship=self.trainer.care_professionals.get(), text='Oi')
        self.client.force_authenticate(self.trainer)
        unread_url = reverse('care-message-unread')
        self.assertEqual(len(self.client.get(unread_url).data), 2)
        self.assertEqual(
            list(self.client.get(unread_url, {'role': 'professional'}).data),
            [str(self.training_rel.pk)],
        )
        self.assertEqual(len(self.client.get(unread_url, {'role': 'patient'}).data), 1)

        self.client.force_authenticate(self.physio)
        response = self.client.post(read_url, {'relationship': str(self.training_rel.pk)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete(self):
        """Senders delete their own messages, the file goes with them"""
        self.send(self.patient, attachment=png_upload())
        message = Message.objects.get()
        path = pathlib.Path(message.attachment.path)
        url = reverse('care-message-detail', kwargs={'pk': message.pk})

        self.client.force_authenticate(self.trainer)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(path.exists())

        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(path.exists())

    def test_export(self):
        """The patient's data export contains their conversations"""
        self.send(self.patient, text='Posso trocar o arroz?')
        self.send(
            self.nutritionist,
            relationship=self.nutrition_rel,
            text='Pode',
        )

        exported = export_user_data(self.patient)['care']['messages']
        self.assertEqual(
            [(m['text'], m['mine']) for m in exported],
            [('Posso trocar o arroz?', True), ('Pode', False)],
        )


class ExecutionVideoTestCase(MessageScenarioMixin, BaseTestCase, APITestCase):
    """
    Videos of the patient with the exercise they show, the professional's
    queue of videos to review and the review with feedback
    """

    def setUp(self):
        super().setUp()
        self.exercise = Exercise.objects.first()

    def video(self, user=None, relationship=None, **data):
        return self.send(
            user or self.patient,
            relationship,
            attachment=SimpleUploadedFile('agachamento.mp4', VIDEO, content_type='video/mp4'),
            **data,
        )

    def queue(self, user=None, **params):
        self.client.force_authenticate(user or self.trainer)
        response = self.client.get(reverse('care-message-videos'), params)
        return response

    def review(self, video_id, user=None, **data):
        self.client.force_authenticate(user or self.trainer)
        return self.client.post(
            reverse('care-message-review', kwargs={'pk': video_id}),
            data,
            format='json',
        )

    def test_video_with_exercise(self):
        """The patient's video to the trainer names the exercise it shows"""
        response = self.video(exercise=self.exercise.pk)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['exercise'], self.exercise.pk)
        self.assertEqual(
            response.data['exercise_name'],
            self.exercise.get_translation('en').name,
        )
        self.assertIsNone(response.data['reviewed_at'])

    def test_exercise_only_on_patient_videos_to_the_trainer(self):
        """A photo, a text, the trainer's video or a video to another area show no exercise"""
        cases = [
            self.send(self.patient, text='Assim?', exercise=self.exercise.pk),
            self.send(self.patient, attachment=png_upload(), exercise=self.exercise.pk),
            self.video(self.trainer, exercise=self.exercise.pk),
            self.video(relationship=self.physio_rel, exercise=self.exercise.pk),
        ]
        for response in cases:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('exercise', response.data)
        self.assertFalse(Message.objects.exists())

    def test_queue(self):
        """The professional sees the patients' videos to review, oldest first"""
        first = self.video(exercise=self.exercise.pk).data['id']
        second = self.video().data['id']
        self.send(self.patient, attachment=png_upload())
        self.video(self.trainer)
        self.video(relationship=self.physio_rel)

        response = self.queue()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data['results']
        self.assertEqual([v['id'] for v in result], [first, second])
        self.assertEqual(result[0]['patient_name'], 'rp_patient')
        self.assertEqual(result[0]['exercise'], self.exercise.pk)

        # Each professional only sees the videos sent to them
        physio = self.queue(self.physio).data['results']
        self.assertEqual(len(physio), 1)
        self.assertEqual(self.queue(self.nutritionist).data['results'], [])
        self.assertEqual(self.queue(self.patient).data['results'], [])

    def test_review_with_feedback(self):
        """The review leaves the queue and the feedback is a message of the trainer"""
        video = self.video(exercise=self.exercise.pk).data['id']
        response = self.review(video, feedback='Joelhos para fora na descida.')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['reviewed_at'])

        self.assertEqual(self.queue().data['results'], [])
        reviewed = self.queue(reviewed='true').data['results']
        self.assertEqual([v['id'] for v in reviewed], [video])

        result = self.messages(self.patient)
        self.assertEqual(result[0]['id'], video)
        self.assertIsNotNone(result[0]['reviewed_at'])
        self.assertEqual(result[1]['text'], 'Joelhos para fora na descida.')
        self.assertFalse(result[1]['mine'])

    def test_review_without_feedback(self):
        video = self.video().data['id']
        self.assertEqual(self.review(video).status_code, status.HTTP_200_OK)
        self.assertEqual(len(self.messages(self.patient)), 1)
        self.assertEqual(self.queue().data['results'], [])

    def test_only_the_professional_reviews_patient_videos(self):
        video = self.video().data['id']
        own = self.video(self.trainer).data['id']
        photo = self.send(self.patient, attachment=png_upload()).data['id']

        self.assertEqual(self.review(video, self.patient).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.review(video, self.nutritionist).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(self.review(own).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.review(photo).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNone(Message.objects.get(pk=video).reviewed_at)

    def test_ended_follow_up(self):
        """Videos of an ended follow-up leave the queue and are no longer reviewed"""
        video = self.video().data['id']
        self.training_rel.status = RelationshipStatus.ENDED
        self.training_rel.save()
        self.assertEqual(self.queue().data['results'], [])
        self.assertEqual(self.review(video).status_code, status.HTTP_400_BAD_REQUEST)

    def test_queue_validation(self):
        self.assertEqual(self.queue(reviewed='sim').status_code, status.HTTP_400_BAD_REQUEST)

    def test_export_has_exercise_and_review(self):
        video = self.video(exercise=self.exercise.pk).data['id']
        self.review(video)
        (exported,) = export_user_data(self.patient)['care']['messages']
        self.assertEqual(exported['exercise'], self.exercise.pk)
        self.assertIsNotNone(exported['reviewed_at'])

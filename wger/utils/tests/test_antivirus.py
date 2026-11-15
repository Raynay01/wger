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
import socket
import struct
import threading
import unittest

# Django
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import (
    SimpleTestCase,
    override_settings,
)

# Third Party
from PIL import Image

# wger
from wger.exercises.models.video import validate_video
from wger.utils.antivirus import scan_upload
from wger.utils.images import validate_image_static_no_animation


EICAR = rb'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

VIDEO = b'\x00\x00\x00\x18ftypmp42' + bytes(range(256)) * 4


def png() -> bytes:
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), 'red').save(buffer, format='PNG')
    return buffer.getvalue()


class FakeClamd:
    """A clamd that answers INSTREAM with a fixed reply and keeps what it received"""

    def __init__(self, answer: bytes):
        self.answer = answer
        self.received = []
        self.server = socket.create_server(('127.0.0.1', 0))
        self.port = self.server.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def _read(self, connection, size: int) -> bytes:
        data = b''
        while len(data) < size:
            data += connection.recv(size - len(data))
        return data

    def _serve(self):
        while True:
            try:
                connection, _ = self.server.accept()
            except OSError:
                return
            with connection:
                assert self._read(connection, 10) == b'zINSTREAM\0'
                content = b''
                while length := struct.unpack('!L', self._read(connection, 4))[0]:
                    content += self._read(connection, length)
                self.received.append(content)
                connection.sendall(self.answer + b'\0')

    def close(self):
        self.server.close()


class AntivirusTestCase(SimpleTestCase):
    """
    Uploads only pass once clamd answers OK; an infected file or an unreachable
    scanner refuses them
    """

    def clamd(self, answer: bytes) -> FakeClamd:
        clamd = FakeClamd(answer)
        self.addCleanup(clamd.close)
        settings = override_settings(CLAMAV_HOST='127.0.0.1', CLAMAV_PORT=clamd.port)
        settings.enable()
        self.addCleanup(settings.disable)
        return clamd

    def test_clean_file(self):
        clamd = self.clamd(b'stream: OK')
        upload = SimpleUploadedFile('foto.png', png())
        # Another check may have read it already
        upload.read()
        scan_upload(upload)
        self.assertEqual(clamd.received, [png()])
        self.assertEqual(upload.tell(), 0)

    def test_infected_file(self):
        self.clamd(b'stream: Eicar-Test-Signature FOUND')
        with self.assertRaisesMessage(ValidationError, 'The virus scan refused this file.'):
            scan_upload(SimpleUploadedFile('foto.png', png()))

    def test_large_file_in_chunks(self):
        clamd = self.clamd(b'stream: OK')
        content = os.urandom(200 * 1024)
        scan_upload(SimpleUploadedFile('video.mp4', content))
        self.assertEqual(clamd.received, [content])

    def test_scanner_error_refuses(self):
        self.clamd(b'INSTREAM size limit exceeded. ERROR')
        with self.assertRaisesMessage(ValidationError, 'not available'):
            scan_upload(SimpleUploadedFile('foto.png', png()))

    def test_unreachable_scanner_refuses(self):
        with socket.create_server(('127.0.0.1', 0)) as unused:
            port = unused.getsockname()[1]
        with override_settings(CLAMAV_HOST='127.0.0.1', CLAMAV_PORT=port, CLAMAV_TIMEOUT=2):
            with self.assertRaisesMessage(ValidationError, 'not available'):
                scan_upload(SimpleUploadedFile('foto.png', png()))

    @override_settings(CLAMAV_HOST='')
    def test_off_without_host(self):
        scan_upload(SimpleUploadedFile('foto.png', EICAR))

    def test_stored_files_are_not_scanned_again(self):
        clamd = self.clamd(b'stream: Eicar-Test-Signature FOUND')
        stored = SimpleUploadedFile('foto.png', png())
        stored._committed = True
        scan_upload(stored)
        self.assertEqual(clamd.received, [])

    def test_image_and_video_validators_scan(self):
        """Gallery and exercise images, exercise videos"""
        clamd = self.clamd(b'stream: Eicar-Test-Signature FOUND')
        with self.assertRaises(ValidationError):
            validate_image_static_no_animation(SimpleUploadedFile('foto.png', png()))
        with self.assertRaises(ValidationError):
            validate_video(SimpleUploadedFile('video.mp4', VIDEO))
        self.assertEqual(len(clamd.received), 2)


@unittest.skipUnless(os.environ.get('CLAMAV_TEST_HOST'), 'needs a running clamd (CLAMAV_TEST_HOST)')
class RealClamdTestCase(SimpleTestCase):
    """Against a real clamd that knows the EICAR test file"""

    def test_eicar_and_clean_file(self):
        with override_settings(
            CLAMAV_HOST=os.environ['CLAMAV_TEST_HOST'],
            CLAMAV_PORT=int(os.environ.get('CLAMAV_TEST_PORT', 3310)),
        ):
            with self.assertRaisesMessage(ValidationError, 'refused'):
                scan_upload(SimpleUploadedFile('eicar.txt', EICAR))
            scan_upload(SimpleUploadedFile('foto.png', png()))

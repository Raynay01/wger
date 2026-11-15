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

"""
Virus scan of uploaded files with ClamAV (clamd, INSTREAM command)

Off while CLAMAV_HOST is empty. Once it is set, a file is only accepted after
clamd answers OK: an unreachable scanner refuses the upload.
"""

# Standard Library
import logging
import socket
import struct

# Django
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


logger = logging.getLogger(__name__)

CHUNK = 64 * 1024


class ScanUnavailable(Exception):
    pass


def _scan(file) -> str | None:
    """The name of the signature clamd found, or None for a clean file"""
    try:
        with socket.create_connection(
            (settings.CLAMAV_HOST, settings.CLAMAV_PORT),
            timeout=settings.CLAMAV_TIMEOUT,
        ) as connection:
            connection.sendall(b'zINSTREAM\0')
            file.seek(0)
            while chunk := file.read(CHUNK):
                connection.sendall(struct.pack('!L', len(chunk)) + chunk)
            connection.sendall(struct.pack('!L', 0))
            answer = b''
            while not answer.endswith(b'\0'):
                data = connection.recv(4096)
                if not data:
                    break
                answer += data
    except OSError as error:
        raise ScanUnavailable(str(error)) from error
    finally:
        file.seek(0)

    answer = answer.rstrip(b'\0').decode(errors='replace')
    if answer.endswith(' OK'):
        return None
    if answer.endswith(' FOUND'):
        return answer.removeprefix('stream: ').removesuffix(' FOUND')
    # e.g. "INSTREAM size limit exceeded. ERROR"
    raise ScanUnavailable(answer)


def scan_upload(file) -> None:
    """Raises a ValidationError for an infected upload or when the scan is not possible"""
    if not settings.CLAMAV_HOST or getattr(file, '_committed', False):
        # Off, or a file that is already stored and was scanned on upload
        return
    try:
        signature = _scan(file)
    except ScanUnavailable as error:
        logger.error('Virus scan not possible, upload refused: %s', error)
        raise ValidationError(_('The virus scan is not available right now. Try again later.'))
    if signature:
        logger.warning('Upload refused by the virus scan: %s (%s bytes)', signature, file.size)
        raise ValidationError(_('The virus scan refused this file.'))

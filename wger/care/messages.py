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
Chat between the patient and the professional of a relationship
"""

# Standard Library
import pathlib
import re

# Django
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import (
    Count,
    Q,
)
from django.db.models.fields.files import FieldFile
from django.http import (
    FileResponse,
    HttpResponse,
    StreamingHttpResponse,
)
from django.utils import timezone
from django.utils.translation import gettext as _

# Third Party
from PIL import Image

# wger
from wger.care.models import (
    AttachmentKind,
    CareRelationship,
    Message,
)
from wger.exercises.models.video import (
    VIDEO_EXTENSIONS,
    has_video_signature,
)
from wger.utils.images import validate_image_static_no_animation


MAX_VIDEO_MB = 50

IMAGE_EXTENSIONS = ('jpg', 'jpeg', 'png', 'webp', 'avif')

CONTENT_TYPES = {
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
    'avif': 'image/avif',
    'mp4': 'video/mp4',
    'mov': 'video/quicktime',
    'webm': 'video/webm',
    'ogv': 'video/ogg',
    'ogg': 'video/ogg',
}

RANGE = re.compile(r'^bytes=(\d*)-(\d*)$')

CHUNK = 64 * 1024


def is_party(user: User, relationship: CareRelationship) -> bool:
    return user.id in (relationship.professional_id, relationship.patient_id)


def classify_attachment(upload) -> str:
    """
    Validates a photo or video and returns its kind. Images are renamed to
    the extension of their real format, which decides the served content type.
    """
    ext = pathlib.Path(upload.name).suffix.lower().lstrip('.')
    if ext in IMAGE_EXTENSIONS:
        validate_image_static_no_animation(upload)
        upload.seek(0)
        image_format = Image.open(upload).format.lower()
        upload.seek(0)
        upload.name = f'image.{image_format}'
        return AttachmentKind.IMAGE

    FileExtensionValidator(VIDEO_EXTENSIONS)(upload)
    if upload.size > 1024 * 1024 * MAX_VIDEO_MB:
        raise ValidationError(_('Maximum file size is %(size)sMB.') % {'size': MAX_VIDEO_MB})
    if not has_video_signature(upload):
        raise ValidationError(_('File is not a valid video'))
    return AttachmentKind.VIDEO


def mark_read(user: User, relationship: CareRelationship) -> int:
    """Marks the messages the other side sent as read"""
    return (
        relationship.messages.filter(read_at__isnull=True)
        .exclude(sender=user)
        .update(read_at=timezone.now())
    )


def unread_counts(user: User, role: str | None = None) -> dict[str, int]:
    """Unread messages per relationship of the user, as professional, patient or both"""
    if role == 'professional':
        q = Q(relationship__professional=user)
    elif role == 'patient':
        q = Q(relationship__patient=user)
    else:
        q = Q(relationship__professional=user) | Q(relationship__patient=user)
    rows = (
        Message.objects.filter(q, read_at__isnull=True)
        .exclude(sender=user)
        .values('relationship')
        .annotate(count=Count('id'))
    )
    return {str(row['relationship']): row['count'] for row in rows}


def _chunks(handle, length: int):
    try:
        while length > 0:
            data = handle.read(min(CHUNK, length))
            if not data:
                break
            length -= len(data)
            yield data
    finally:
        handle.close()


def attachment_response(request, attachment: FieldFile) -> HttpResponse:
    """
    The file with support for range requests, which Safari needs to play videos
    """
    ext = pathlib.Path(attachment.name).suffix.lower().lstrip('.')
    content_type = CONTENT_TYPES.get(ext, 'application/octet-stream')
    size = attachment.size
    handle = attachment.storage.open(attachment.name, 'rb')

    match = RANGE.match(request.headers.get('Range', ''))
    if match and (match[1] or match[2]):
        if match[1]:
            start = int(match[1])
            end = min(int(match[2]), size - 1) if match[2] else size - 1
        else:
            start = max(size - int(match[2]), 0)
            end = size - 1
        if start > end:
            handle.close()
            response = HttpResponse(status=416)
            response['Content-Range'] = f'bytes */{size}'
            return response
        handle.seek(start)
        response = StreamingHttpResponse(
            _chunks(handle, end - start + 1),
            status=206,
            content_type=content_type,
        )
        response['Content-Range'] = f'bytes {start}-{end}/{size}'
        response['Content-Length'] = str(end - start + 1)
    else:
        response = FileResponse(handle, content_type=content_type)

    response['Accept-Ranges'] = 'bytes'
    response['Content-Disposition'] = 'inline'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, max-age=3600'
    return response

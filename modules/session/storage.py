"""Removing files from MEDIA_ROOT once nothing points at them any more.

Deleting a Session or a user only removes database rows; the snapshot PNGs and
uploaded files on disk have to be cleaned up separately, otherwise "deleted"
data would still be lying around.
"""
import logging

from django.conf import settings
from django.core.files.storage import default_storage

from .models import Session, UploadedFile

logger = logging.getLogger(__name__)


def media_path(url):
    """Map a /media/... URL back to its storage path (None for other URLs)."""
    if url and url.startswith(settings.MEDIA_URL):
        return url[len(settings.MEDIA_URL):]
    return None


def session_file_paths(sessions):
    """Storage paths of the snapshots and uploads belonging to ``sessions``."""
    paths = {media_path(url) for url in sessions.values_list("snapshot_url", flat=True)}
    paths.update(UploadedFile.objects.filter(session__in=sessions).values_list("file", flat=True))
    paths.discard(None)
    paths.discard("")
    return paths


def delete_unreferenced(paths):
    """Delete each file unless a remaining session or upload still uses it.

    Duplicated sessions share their original's snapshot, so a snapshot is only
    removed when no session points at it any more.
    """
    for path in paths:
        if not path:
            continue
        url = settings.MEDIA_URL + path
        if Session.objects.filter(snapshot_url=url).exists() or UploadedFile.objects.filter(file=path).exists():
            continue
        try:
            default_storage.delete(path)
        except Exception:
            logger.exception("Could not delete media file %s", path)

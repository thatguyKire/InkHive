"""Who may see what: shared by views, the WebSocket consumer and file serving."""
import re

from django.conf import settings
from django.db.models import Q

from .models import Session, Participant

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# <session>_<timestamp>.png, plus the random suffix Django's storage adds when
# two snapshots land in the same second (e.g. _1760425200_AbC12xY.png)
_SNAPSHOT_RE = re.compile(rf"^snapshots/({_UUID})_\d+(?:_[A-Za-z0-9]+)?\.png$")
_UPLOAD_RE = re.compile(rf"^session_files/({_UUID})/[^/]+$")


def can_manage(user, session):
    """Owner or staff: may change, export, delete or announce to the session."""
    return user == session.created_by or user.is_staff


def accessible_sessions(user):
    """Sessions the user owns or has joined (staff: all)."""
    if user.is_staff:
        return Session.objects.all()
    joined = Participant.objects.filter(user=user).values("session_id")
    return Session.objects.filter(Q(created_by=user) | Q(id__in=joined))


def can_access_media(user, path):
    """True if ``user`` may download MEDIA_ROOT/``path``.

    Snapshots belong to the session in their file name, and also to any
    duplicated session that points at the same snapshot. Uploads belong to the
    session folder they are stored in. Anything else is not served.
    """
    if not user.is_authenticated:
        return False
    match = _SNAPSHOT_RE.match(path)
    if match:
        url = settings.MEDIA_URL + path
        return accessible_sessions(user).filter(Q(id=match.group(1)) | Q(snapshot_url=url)).exists()
    match = _UPLOAD_RE.match(path)
    if match:
        return accessible_sessions(user).filter(id=match.group(1)).exists()
    return False

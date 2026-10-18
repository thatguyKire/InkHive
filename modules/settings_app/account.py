"""Self-service data rights: download everything about an account, or delete it.

The Privacy Policy (modules/legal) promises both, so keep it in sync with
what these functions actually export and delete.
"""
from django.db import transaction
from django.utils import timezone

from modules.chat.models import Message
from modules.notifications.models import Notification
from modules.session.models import Session, Participant, ChatMessage, UploadedFile
from modules.session.storage import session_file_paths, delete_unreferenced


def _iso(value):
    return value.isoformat() if value else None


def export_user_data(user):
    """Everything stored about ``user``, as JSON-ready data."""
    return {
        "exported_at": timezone.now().isoformat(),
        "account": {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "student_id": user.student_id,
            "date_joined": _iso(user.date_joined),
            "last_login": _iso(user.last_login),
            "terms_version": user.terms_version,
            "terms_accepted_at": _iso(user.terms_accepted_at),
        },
        "sessions_created": [
            {
                "id": str(s.id),
                "title": s.title,
                "code": s.code,
                "created_at": _iso(s.created_at),
                "scheduled_for": _iso(s.scheduled_for),
                "snapshot_url": s.snapshot_url,
                "is_saved": s.is_saved,
                "is_archived": s.is_archived,
            }
            for s in Session.objects.filter(created_by=user).order_by("created_at")
        ],
        "sessions_joined": [
            {
                "session_id": str(p.session_id),
                "session_title": p.session.title,
                "joined_at": _iso(p.joined_at),
                "last_active": _iso(p.last_active),
                "can_draw": p.can_draw,
                "strokes_count": p.strokes_count,
                "uploads_count": p.uploads_count,
            }
            for p in Participant.objects.filter(user=user).select_related("session").order_by("joined_at")
        ],
        "chat_messages": [
            {"session_id": str(m.room.session_id) if m.room.session_id else None,
             "content": m.content, "sent_at": _iso(m.timestamp)}
            for m in Message.objects.filter(sender=user).select_related("room").order_by("timestamp")
        ] + [
            {"session_id": str(m.session_id), "content": m.content, "sent_at": _iso(m.timestamp)}
            for m in ChatMessage.objects.filter(sender=user).order_by("timestamp")
        ],
        "uploads": [
            {"session_id": str(u.session_id), "file_name": u.original_name,
             "file_url": u.file_url, "uploaded_at": _iso(u.uploaded_at)}
            for u in UploadedFile.objects.filter(uploaded_by=user).order_by("uploaded_at")
        ],
        "notifications": [
            {"content": n.content, "session_id": str(n.session_id) if n.session_id else None,
             "urgent": n.is_urgent, "created_at": _iso(n.created_at), "read_at": _iso(n.read_at)}
            for n in Notification.objects.filter(recipient=user).order_by("created_at")
        ],
    }


def delete_user_account(user):
    """Delete ``user`` with everything they own, including files on disk.

    Database cascades remove the user's sessions (with their participants,
    chats and uploads), their participation, messages, uploads and
    notifications elsewhere. Notifications other users got about the deleted
    sessions are removed too, and finally the snapshot/upload files.
    """
    owned = Session.objects.filter(created_by=user)
    files = session_file_paths(owned)
    files.update(UploadedFile.objects.filter(uploaded_by=user).values_list("file", flat=True))
    with transaction.atomic():
        Notification.objects.filter(session__in=owned).delete()
        user.delete()
    delete_unreferenced(files)

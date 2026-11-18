"""Announcements a teacher sent, as one row each.

An announcement is stored as one Notification per recipient; rows with the
same text and urgency sent in the same minute (and session) are one
announcement.
"""
from django.db.models import Count, Min
from django.db.models.functions import TruncMinute

from .models import Notification


def recent_announcements(sessions, limit=30):
    """Newest-first announcements sent to ``sessions`` (a Session queryset)."""
    rows = (
        Notification.objects
        .filter(session__in=sessions)
        .annotate(sent_minute=TruncMinute("created_at"))
        .values("content", "is_urgent", "sent_minute", "session_id", "session__title")
        .annotate(
            created_at=Min("created_at"),
            first_id=Min("id"),
            recipient_count=Count("recipient", distinct=True),
        )
        .order_by("-created_at")[:limit]
    )
    return [
        {
            "id": r["first_id"],
            "content": r["content"],
            "is_urgent": r["is_urgent"],
            "created_at": r["created_at"],
            "recipient_count": r["recipient_count"],
            "session_title": r["session__title"],
        }
        for r in rows
    ]

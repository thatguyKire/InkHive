"""Numbers behind the teacher dashboard, kept out of the view."""
from datetime import timedelta

from django.db.models import Count, Max
from django.utils import timezone

from modules.chat.models import Message
from modules.notifications.announcements import recent_announcements
from modules.session.models import Participant, Session, UploadedFile
from modules.session.presence import online_count


def teacher_overview(user, *, sessions_shown=5, bulletin_size=3):
    """Headline stats, open sessions, the latest saved board and recent announcements."""
    sessions = Session.objects.filter(created_by=user)
    week_ago = timezone.now() - timedelta(days=7)
    participants = Participant.objects.filter(session__in=sessions)

    open_sessions = list(
        sessions.annotate(student_count=Count("participants")).order_by("-created_at")[:sessions_shown]
    )
    for session in open_sessions:
        session.online = online_count(session.id)

    return {
        "class_count": sessions.count(),
        "classes_this_week": sessions.filter(created_at__gte=week_ago).count(),
        "students_this_week": participants.filter(joined_at__gte=week_ago)
                                          .values("user").distinct().count(),
        "open_sessions": open_sessions,
        "canvas_session": sessions.exclude(snapshot_url__isnull=True).exclude(snapshot_url="")
                                  .order_by("-created_at").first(),
        "bulletin": recent_announcements(sessions, limit=bulletin_size),
    }


def teacher_performance(user):
    """One row per student across all of ``user``'s sessions, plus totals and chart data."""
    sessions = Session.objects.filter(created_by=user)
    participants = Participant.objects.filter(session__in=sessions).select_related("user")

    uploads = {
        u["uploaded_by_id"]: u
        for u in UploadedFile.objects.filter(session__in=sessions)
        .values("uploaded_by_id").annotate(upload_count=Count("id"), last_upload=Max("uploaded_at"))
    }
    messages = {
        m["sender_id"]: m
        for m in Message.objects.filter(room__session__in=sessions)
        .values("sender_id").annotate(msg_count=Count("id"), last_msg=Max("timestamp"))
    }

    rows_by_user = {}
    for p in participants:
        row = rows_by_user.get(p.user_id)
        if row is None:
            up, ms = uploads.get(p.user_id), messages.get(p.user_id)
            row = rows_by_user[p.user_id] = {
                "username": p.user.username,
                "strokes": 0,
                "uploads": up["upload_count"] if up else 0,
                "messages": ms["msg_count"] if ms else 0,
                "last_active": max(
                    [d for d in (up["last_upload"] if up else None, ms["last_msg"] if ms else None) if d],
                    default=None,
                ),
            }
        row["strokes"] += p.strokes_count
        seen = [d for d in (row["last_active"], p.last_active, p.joined_at) if d]
        row["last_active"] = max(seen) if seen else None
    rows = sorted(rows_by_user.values(), key=lambda r: r["username"].lower())

    today = timezone.localdate()
    totals = {
        "total_students": len(rows),
        "active_today": sum(
            1 for r in rows if r["last_active"] and timezone.localtime(r["last_active"]).date() == today
        ),
        "total_strokes": sum(r["strokes"] for r in rows),
        "total_uploads": sum(r["uploads"] for r in rows),
        "total_messages": sum(r["messages"] for r in rows),
    }
    chart = {
        "labels": [r["username"] for r in rows],
        "uploads": [r["uploads"] for r in rows],
        "messages": [r["messages"] for r in rows],
        "strokes": [r["strokes"] for r in rows],
    }
    return rows, totals, chart

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from modules.core import ratelimit
from modules.session.access import can_manage
from modules.session.models import Session, Participant
from .announcements import recent_announcements
from .models import Notification
from .notify import notify

ANNOUNCEMENTS_PER_MINUTE = 10


def _as_json(n):
    return {
        "id": n.id,
        "content": n.content,
        "is_urgent": n.is_urgent,
        "created_at": n.created_at.isoformat(),
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "session_id": n.session_id,
    }


@require_GET
@login_required
def latest_json(request):
    qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")[:20]
    return JsonResponse({"items": [_as_json(n) for n in qs]})

@login_required
def notifications_view(request):
    items = Notification.objects.filter(recipient=request.user).order_by("-created_at")[:100]
    return render(request, "notifications/notifications.html", {"items": items})

@login_required
def unread_count(request):
    cnt = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
    return JsonResponse({"count": cnt})

@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return JsonResponse({"ok": True})

@login_required
@require_POST
def mark_read(request, pk: int):
    n = get_object_or_404(Notification, pk=pk, recipient=request.user, read_at__isnull=True)
    n.read_at = timezone.now()
    n.save(update_fields=["read_at"])
    return JsonResponse({"ok": True})

@login_required
@require_POST
def send_announcement(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if not can_manage(request.user, session):
        return JsonResponse({"ok": False, "error": "permission_denied"}, status=403)

    text = request.POST.get("message", "").strip()
    urgent = request.POST.get("urgent") == "1"
    if not text:
        return JsonResponse({"ok": False, "error": "empty"}, status=400)
    if len(text) > 1000:
        return JsonResponse({"ok": False, "error": "too_long"}, status=400)
    if not ratelimit.allow("announce", request.user.pk, ANNOUNCEMENTS_PER_MINUTE, 60):
        return JsonResponse({"ok": False, "error": "rate_limited"}, status=429)

    participant_qs = (
        Participant.objects
        .filter(session=session)
        .exclude(user=session.created_by)
        .select_related("user")
    )

    # Dedup user IDs
    seen = set()
    targets = []
    for p in participant_qs:
        if p.user_id not in seen:
            seen.add(p.user_id)
            targets.append(p.user)

    sent = 0
    for u in targets:
        if notify(u, text, session=session, urgent=urgent):
            sent += 1
    return JsonResponse({"ok": True, "sent": sent})

@login_required
def session_announcements_json(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if not can_manage(request.user, session):
        return JsonResponse({"items": []})
    items = recent_announcements(Session.objects.filter(pk=session.pk))
    data = [
        {key: a[key] for key in ("id", "content", "is_urgent", "recipient_count")}
        | {"created_at": a["created_at"].isoformat()}
        for a in items
    ]
    return JsonResponse({"items": data})

@login_required
def session_student_announcements_json(request, session_id):
    """
    Return announcements for the current user in a session (students + teacher).
    Used by the student whiteboard to bootstrap and by realtime to filter.
    """
    session = get_object_or_404(Session, id=session_id)
    # Ensure user is participant, teacher, or staff
    is_allowed = (
        request.user == session.created_by
        or request.user.is_staff
        or Participant.objects.filter(session=session, user=request.user).exists()
    )
    if not is_allowed:
        return JsonResponse({"items": []})
    qs = Notification.objects.filter(session=session, recipient=request.user).order_by("-created_at")[:50]
    return JsonResponse({"items": [_as_json(n) for n in qs]})

import csv
import json
import logging
import time as systime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from modules.core import ratelimit
from modules.core.decorators import safe_view
from ..access import can_manage
from ..file_checks import content_matches
from ..models import Session, Participant
from ..storage import session_file_paths, delete_unreferenced

logger = logging.getLogger(__name__)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_SNAPSHOT_BYTES = 15 * 1024 * 1024
SNAPSHOTS_PER_10_MIN = 30


@login_required
@safe_view
def delete_session(request, session_id):
    """Delete a session (POST only). Only the owner or staff may delete."""
    session = get_object_or_404(Session, id=session_id)

    if not can_manage(request.user, session):
        messages.error(request, "You do not have permission to delete this session.")
        return redirect(reverse("session_list"))

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect(reverse("session_list"))

    title = session.title
    try:
        files = session_file_paths(Session.objects.filter(pk=session.pk))
        session.delete()
        delete_unreferenced(files)
        messages.success(request, f"Session '{title}' deleted.")
    except Exception as exc:
        logger.exception("Failed to delete session %s: %s", session_id, exc)
        messages.error(request, "Failed to delete session.")
    return redirect(reverse("session_list"))


@login_required
@require_POST
@safe_view
def toggle_draw_permission(request, session_id, user_id):
    session = get_object_or_404(Session, id=session_id)
    if request.user != session.created_by:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = request.POST or {}

    raw = str(data.get("can_draw", "")).lower()
    can = raw in ("1", "true", "on", "yes")

    p = Participant.objects.filter(session=session, user_id=user_id).first()
    if not p:
        return JsonResponse({"ok": False, "error": "participant_not_found"}, status=404)

    p.can_draw = can
    p.save(update_fields=["can_draw"])
    return JsonResponse({"ok": True, "user_id": user_id, "can_draw": p.can_draw})


@login_required
@safe_view
def save_snapshot(request, session_id):
    """Store a uniquely named PNG snapshot (MEDIA_ROOT/snapshots/) and mark the session as saved."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    session = get_object_or_404(Session, id=session_id)
    if not can_manage(request.user, session):
        return JsonResponse({"ok": False, "error": "permission"}, status=403)

    img_file = request.FILES.get("image")
    if not img_file:
        return JsonResponse({"ok": False, "error": "no_image"}, status=400)

    if not ratelimit.allow("snapshot", request.user.pk, SNAPSHOTS_PER_10_MIN, 10 * 60):
        return JsonResponse({"ok": False, "error": "rate_limited"}, status=429)
    if img_file.size > MAX_SNAPSHOT_BYTES:
        return JsonResponse({"ok": False, "error": "too_large"}, status=400)
    data = img_file.read()
    if not data.startswith(PNG_SIGNATURE) or not content_matches(".png", data):
        return JsonResponse({"ok": False, "error": "not_png"}, status=400)

    file_path = f"snapshots/{session_id}_{int(systime.time())}.png"
    try:
        saved_path = default_storage.save(file_path, ContentFile(data))
    except Exception:
        logger.exception("Failed to store snapshot for session %s", session_id)
        return JsonResponse({"ok": False, "error": "save_failed"}, status=500)
    public_url = default_storage.url(saved_path)

    session.snapshot_url = public_url
    session.is_saved = True
    session.is_offline_available = True
    session.save(update_fields=["snapshot_url", "is_saved", "is_offline_available"])
    logger.info("Snapshot saved: %s", file_path)
    return JsonResponse({"ok": True, "url": public_url})


@login_required
@safe_view
def export_session(request, session_id):
    """Send the latest saved snapshot (PNG) to the owner; 404 if never saved."""
    session = get_object_or_404(Session, id=session_id)
    if not can_manage(request.user, session):
        return HttpResponse(status=403)
    if not session.snapshot_url:
        return HttpResponse("No snapshot available", status=404)
    return redirect(session.snapshot_url)


@login_required
@require_POST
@safe_view
def toggle_chat(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if not can_manage(request.user, session):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    session.chat_enabled = not session.chat_enabled
    session.save(update_fields=["chat_enabled"])
    return JsonResponse({"ok": True, "chat_enabled": session.chat_enabled, "session_id": str(session.id)})


@login_required
@require_POST
@safe_view
def presence_sync(request, session_id):
    """Teacher-initiated presence sync: revoke can_draw for absent users.

    Body: JSON {"present_user_ids": [int, ...]} (fetch with X-CSRFToken), or a
    form with present_user_ids=<JSON list> + csrfmiddlewaretoken (sendBeacon on
    page unload, which cannot set headers). CSRF is enforced either way.
    - Only the session owner (teacher) or staff can invoke this.
    - Participants are never deleted; absent users just lose can_draw.
    """
    session = get_object_or_404(Session, id=session_id)
    if not can_manage(request.user, session):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    try:
        if request.content_type == "application/json":
            data = json.loads(request.body or "{}")
        else:
            data = {"present_user_ids": json.loads(request.POST.get("present_user_ids") or "[]")}
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    present_ids = set()
    for val in (data.get("present_user_ids") or []):
        try:
            present_ids.add(int(val))
        except (TypeError, ValueError):
            continue

    now = timezone.now()
    qs = Participant.objects.filter(session=session)
    if present_ids:
        qs.filter(user_id__in=present_ids).update(last_active=now)
    # Absent users lose drawing rights; stamp the time they were last seen.
    updated = qs.exclude(user_id__in=present_ids).filter(can_draw=True).update(can_draw=False, last_active=now)

    all_ids = set(qs.values_list("user_id", flat=True))
    return JsonResponse({
        "ok": True,
        "updated_count": updated,
        "present": sorted(all_ids & present_ids),
        "absent": sorted(all_ids - present_ids),
    })


@login_required
@safe_view
def attendance_json(request, session_id):
    """Attendance data as JSON for live updates on the attendance page."""
    session = get_object_or_404(Session, id=session_id)
    if not can_manage(request.user, session):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    parts = Participant.objects.filter(session=session).select_related("user").order_by("joined_at")
    data = [{
        "user_id": p.user_id,
        "username": p.user.username,
        "email": p.user.email,
        "can_draw": p.can_draw,
        "joined_at": p.joined_at.isoformat() if p.joined_at else None,
        "last_active": p.last_active.isoformat() if p.last_active else None,
    } for p in parts]
    return JsonResponse({"ok": True, "participants": data, "now": timezone.now().isoformat()})


@login_required
@safe_view
def attendance_view(request, session_id):
    """Attendance / participation log for a session (owner or staff only).

    Supports CSV export via ``?export=csv``.
    """
    session = get_object_or_404(Session, id=session_id)
    if not can_manage(request.user, session):
        return HttpResponse(status=403)

    participants = Participant.objects.filter(session=session).select_related("user").order_by("joined_at")

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="attendance_session_{session_id}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Student", "Email", "Joined", "Last Active", "Strokes", "Uploads"])
        for p in participants:
            writer.writerow([
                p.user.username,
                p.user.email,
                p.joined_at.isoformat() if p.joined_at else "",
                p.last_active.isoformat() if p.last_active else "",
                p.strokes_count,
                p.uploads_count,
            ])
        return response

    return render(request, "session/attendance.html", {
        "session": session,
        "participants": participants,
        "now": timezone.now(),
    })

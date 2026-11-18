import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from modules.authentication.decorators import role_required
from django.db.models import Count
from modules.authentication.models import CustomUser
from modules.chat.models import Message
from modules.session.models import Participant, UploadedFile, Session
from .metrics import teacher_overview, teacher_performance

logger = logging.getLogger(__name__)


# ---------- STUDENT DASHBOARD ----------
@login_required
def student_dashboard(request):
    """
    Displays sessions joined by the student.
    """
    joined = list(
        Participant.objects.filter(user=request.user)
        .select_related("session")
        .order_by("-joined_at")
    )
    performance_chart = {
        "labels": [p.session.title or "Session" for p in joined],
        "strokes": [p.strokes_count for p in joined],
        "uploads": [p.uploads_count for p in joined],
    }
    return render(request, "dashboard/student_dashboard.html", {
        "joined_sessions": joined,
        "student_perf_chart": performance_chart,
    })


# ---------- TEACHER DASHBOARD ----------
@login_required
@role_required(['teacher'])
def teacher_dashboard(request):
    """Teacher home: headline stats, open sessions, latest board, announcements, performance."""
    rows, totals, chart = teacher_performance(request.user)
    return render(request, "dashboard/teacher_dashboard.html", {
        **teacher_overview(request.user),
        "performance_rows": rows,
        "performance_totals": totals,
        "performance_chart": chart,
    })


# ---------- ADMIN DASHBOARD ----------
@login_required
@role_required(['admin'])
def admin_dashboard(request):
    """
    Platform-wide counts for administrators.
    """
    role_counts = dict(CustomUser.objects.values_list("role").annotate(n=Count("id")))
    context = {
        "student_count": role_counts.get("student", 0),
        "teacher_count": role_counts.get("teacher", 0),
        "admin_count": role_counts.get("admin", 0),
        "session_count": Session.objects.count(),
        "participant_count": Participant.objects.count(),
        "upload_count": UploadedFile.objects.count(),
        "message_count": Message.objects.count(),
        "recent_sessions": Session.objects.select_related("created_by").order_by("-created_at")[:10],
    }
    return render(request, "dashboard/admin_dashboard.html", context)


# ---------- REDIRECT DASHBOARD ----------
@login_required
def redirect_dashboard(request):
    """
    Redirect users to their role-based dashboard.
    """
    role = getattr(request.user, "role", None)
    if role == "student":
        return redirect("student_dashboard")
    elif role == "teacher":
        return redirect("teacher_dashboard")
    elif role == "admin":
        return redirect("admin_dashboard")
    return redirect("auth:login")

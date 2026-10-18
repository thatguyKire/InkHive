from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from modules.authentication.models import CustomUser
from modules.core import ratelimit
from .accounts import ensure_demo_data, TEACHER, STUDENT

ROLES = {"teacher": TEACHER, "student": STUDENT}
DEMO_LOGINS_PER_IP_PER_HOUR = 30


@require_POST
def demo_login(request, role):
    """Sign in as a shared demo account (only when DEMO_MODE is on)."""
    if not settings.DEMO_MODE or role not in ROLES:
        raise Http404
    if not ratelimit.allow("demo-login", ratelimit.client_ip(request), DEMO_LOGINS_PER_IP_PER_HOUR, 60 * 60):
        messages.error(request, "⚠️ Too many demo sign-ins from your network. Please try again later.")
        return redirect("auth:login")

    ensure_demo_data()
    user = CustomUser.objects.get(username=ROLES[role], is_demo=True)
    login(request, user, backend="modules.authentication.backends.EmailOrUsernameModelBackend")
    return redirect("redirect_dashboard")

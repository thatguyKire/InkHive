from functools import lru_cache

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse


@lru_cache(maxsize=1)
def _locked_paths():
    """Pages that would let one visitor lock the others out of a shared demo account."""
    return frozenset(reverse(name) for name in ("password_change", "edit_profile", "delete_account"))


class DemoModeMiddleware:
    """Public demo rules.

    With DEMO_MODE on, sign-up is turned off (visitors use the demo buttons on
    the login page). Demo accounts can never change their password or email or
    delete themselves, whatever DEMO_MODE says.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEMO_MODE and request.path == reverse("auth:signup"):
            messages.info(request, "Sign-up is turned off in the demo. Use a demo account instead.")
            return redirect("auth:login")

        if getattr(request.user, "is_demo", False) and request.path in _locked_paths():
            if request.method in ("GET", "HEAD"):
                return redirect("settings")
            return JsonResponse({"ok": False, "error": "demo_account"}, status=403)

        return self.get_response(request)

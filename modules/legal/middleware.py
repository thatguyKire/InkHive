"""Make signed-in users agree to the current Terms before using the app.

Users who have not accepted settings.TERMS_VERSION (accounts created before the
terms existed, or after the terms changed) are sent to the accept page on any
page load, and other requests get 403. The legal pages themselves, logging
out, deleting or downloading the account, static/media files, the health check
and the Django admin stay reachable so nobody is trapped.
"""
from functools import lru_cache
from urllib.parse import urlencode

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse


@lru_cache(maxsize=1)
def _exempt_prefixes():
    return (
        "/legal/",
        "/healthz/",
        "/" + settings.ADMIN_URL,
        settings.STATIC_URL,
        settings.MEDIA_URL,
        reverse("auth:logout"),
        reverse("delete_account"),
        reverse("export_data"),
    )


class TermsAcceptanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (user is not None and user.is_authenticated and not user.has_accepted_terms
                and not request.path.startswith(_exempt_prefixes())):
            if request.method in ("GET", "HEAD"):
                return redirect(f"{reverse('legal:accept')}?{urlencode({'next': request.get_full_path()})}")
            return JsonResponse(
                {"ok": False, "error": "Please accept the updated Terms of Service first."}, status=403
            )
        return self.get_response(request)

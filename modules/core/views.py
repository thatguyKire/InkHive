import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.static import serve

INLINE_MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def landing(request):
    # Redirect root to the login page
    return redirect("auth:login")


def home(request):
    # Legacy path → also go to login
    return redirect("auth:login")


@never_cache
def healthz(request):
    """Liveness check for the hosting platform (exempt from the HTTPS redirect)."""
    return HttpResponse("ok", content_type="text/plain")


@login_required
def media(request, path):
    """Serve an uploaded file or snapshot to members of its session only.

    Everyone else gets 404 (not 403) so file names cannot be probed. Files are
    served with a sandboxing CSP, nosniff and, for non-images, as downloads so
    a crafted upload can never run as a page on this site.
    """
    from modules.session.access import can_access_media

    if not can_access_media(request.user, path):
        raise Http404("Not found")
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    response["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; sandbox"
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, max-age=3600"
    if os.path.splitext(path)[1].lower() not in INLINE_MEDIA_EXTENSIONS:
        response["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
    return response

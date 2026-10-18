from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme


def _context(**extra):
    return {
        "effective_date": date.fromisoformat(settings.TERMS_VERSION),
        **extra,
    }


def terms(request):
    """Terms of Service (public)."""
    return render(request, "legal/terms.html", _context())


def privacy(request):
    """Privacy Policy (public)."""
    return render(request, "legal/privacy.html", _context())


@login_required
def accept_terms(request):
    """Ask a signed-in user to agree to the current Terms and Privacy Policy.

    TermsAcceptanceMiddleware sends users here when they have not accepted
    settings.TERMS_VERSION (accounts made before the terms existed, or after
    the terms changed). New users accept on the sign-up form instead.
    """
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        next_url = ""

    if request.method == "POST":
        if request.POST.get("agree") == "on":
            request.user.accept_terms()
            request.user.save(update_fields=["terms_version", "terms_accepted_at"])
            return redirect(next_url or "redirect_dashboard")
        messages.error(request, "Please tick the box to agree, or log out.")
    elif request.user.has_accepted_terms:
        return redirect(next_url or "redirect_dashboard")

    return render(request, "legal/accept.html", _context(next=next_url))

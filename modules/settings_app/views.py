import json
import logging

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponse
from django.utils.text import slugify

from modules.core import ratelimit
from .account import export_user_data, delete_user_account

logger = logging.getLogger(__name__)

DELETE_ATTEMPTS_PER_15_MIN = 5


@login_required
def settings_view(request):
    return render(request, "settings_app/settings.html")


@login_required
def export_data(request):
    """Download everything stored about the signed-in user as JSON."""
    data = json.dumps(export_user_data(request.user), indent=2, ensure_ascii=False)
    response = HttpResponse(data, content_type="application/json; charset=utf-8")
    filename = f"{slugify(settings.SITE_NAME)}-my-data.json"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def delete_account(request):
    """Permanently delete the signed-in user's account after a password check."""
    user = request.user
    if user.is_staff or user.is_superuser:
        messages.error(request, "Admin accounts can only be removed by another admin.")
        return redirect("settings")

    status = 200
    if request.method == "POST":
        if ratelimit.is_limited("delete-account", user.pk, DELETE_ATTEMPTS_PER_15_MIN):
            messages.error(request, "Too many attempts. Please wait 15 minutes and try again.")
            status = 429
        elif request.POST.get("confirm") != "on":
            messages.error(request, "Please tick the box to confirm.")
            status = 400
        elif not user.check_password(request.POST.get("password") or ""):
            ratelimit.hit("delete-account", user.pk, 15 * 60)
            messages.error(request, "Wrong password. Your account was not deleted.")
            status = 400
        else:
            username = user.username
            delete_user_account(user)
            logout(request)
            logger.info("Account deleted by its owner: %s", username)
            messages.success(request, "Your account and data have been deleted.")
            return redirect("auth:login")

    return render(request, "settings_app/delete_account.html", status=status)

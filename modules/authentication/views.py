import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.db import IntegrityError
from django.urls import reverse_lazy

from modules.core import ratelimit
from .forms import CustomSignupForm

logger = logging.getLogger(__name__)

SIGNUPS_PER_IP_PER_HOUR = 10


def signup_view(request):
    """Handles user registration."""
    if request.method == "POST":
        form = CustomSignupForm(request.POST)
        ip = ratelimit.client_ip(request)
        if ratelimit.is_limited("signup-ip", ip, SIGNUPS_PER_IP_PER_HOUR):
            logger.warning("Signup blocked (rate limit) from %s", ip)
            messages.error(request, "⚠️ Too many sign-ups from your network. Please try again later.")
            return render(request, "authentication/signup.html", {"form": form}, status=429)
        if form.is_valid():
            ratelimit.hit("signup-ip", ip, 60 * 60)
            try:
                user = form.save()
                login(request, user, backend="modules.authentication.backends.EmailOrUsernameModelBackend")
                messages.success(request, f"✅ Welcome, {user.username}!")
                return redirect("redirect_dashboard")
            except IntegrityError:
                messages.error(request, "⚠️ That Student ID or email is already in use.")
        else:
            messages.error(request, "⚠️ Please correct the errors below.")
    else:
        form = CustomSignupForm()

    return render(request, "authentication/signup.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "authentication/login.html"
    # Signed-in users can still open the login page (e.g. to switch account).
    redirect_authenticated_user = False

    def get_success_url(self):
        # Ignore `next`: it could point back at a session the user has no access to now.
        return reverse_lazy("redirect_dashboard")

    def form_invalid(self, form):
        if getattr(self.request, "login_locked", False):
            messages.error(self.request, "⚠️ Too many failed attempts. Please wait 15 minutes and try again.")
            response = super().form_invalid(form)
            response.status_code = 429
            return response
        messages.error(self.request, "⚠️ Invalid credentials. Please try again.")
        return super().form_invalid(form)

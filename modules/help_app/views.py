from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def help_view(request):
    return render(request, "help_app/help.html", {"contact_email": settings.CONTACT_EMAIL})

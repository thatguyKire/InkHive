"""Root URL configuration."""
from django.contrib import admin
from django.urls import path, include, re_path

from django.conf import settings

from modules.core import views as core_views

urlpatterns = [
    # Django admin (superusers / staff); path configurable via ADMIN_URL
    path(settings.ADMIN_URL, admin.site.urls),
    path('healthz/', core_views.healthz, name='healthz'),

    # Core landing page (redirects to login)
    path('', include('modules.core.urls')),

    # Authentication
    path('auth/', include(('modules.authentication.urls', 'authentication'), namespace='auth')),

    # Other modules
    path('profiles/', include('modules.profiles.urls')),
    path('dashboard/', include('modules.dashboard.urls')),
    path('settings/', include('modules.settings_app.urls')),
    path('notifications/', include(("modules.notifications.urls", "notifications"), namespace="notifications")),
    path('help/', include('modules.help_app.urls')),
    path('session/', include('modules.session.urls')),
    path("chat/", include("modules.chat.urls")),
    path('legal/', include(('modules.legal.urls', 'legal'), namespace='legal')),
    path('demo/', include(('modules.demo.urls', 'demo'), namespace='demo')),

]

# Uploaded files and snapshots live on local disk; serve them in every
# environment (static() alone only works with DEBUG=True).
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", core_views.media, name="media"),
]

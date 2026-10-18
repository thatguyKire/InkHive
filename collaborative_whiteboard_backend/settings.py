"""
Django settings for collaborative_whiteboard_backend project.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
import dj_database_url
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -------------------------------------------------------------
# PATHS
# -------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------------------------------------------
# SECURITY SETTINGS
# -------------------------------------------------------------
# The fallback key is public (it is in git) and only for local development.
_DEV_SECRET_KEY = "django-insecure-4-b^8=^287@np#7mr$+l9*5!+2tvn_6ecx#4n+six8ep3!ln-#"
SECRET_KEY = os.getenv("SECRET_KEY", _DEV_SECRET_KEY)

# Render sets RENDER=true, so production defaults to DEBUG off unless overridden.
DEBUG = os.getenv("DEBUG", "False" if os.getenv("RENDER") else "True") == "True"

if not DEBUG and (SECRET_KEY == _DEV_SECRET_KEY or len(SECRET_KEY) < 50):
    raise ImproperlyConfigured(
        "SECRET_KEY must be set to a long random value (50+ characters) when DEBUG is off. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )

ALLOWED_HOSTS = [
    'collaboard-z4sx.onrender.com',
    'localhost',
    '127.0.0.1',
]
ALLOWED_HOSTS += [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
if os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])

CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h not in ("localhost", "127.0.0.1")]

# Behind Render's proxy: trust its X-Forwarded-Proto (so request.is_secure()
# works) and X-Forwarded-For (client IP for rate limiting). Never trust these
# headers when the app is reachable directly, because clients could forge them.
BEHIND_PROXY = bool(os.getenv("RENDER")) or os.getenv("BEHIND_PROXY") == "True"
TRUST_X_FORWARDED_FOR = BEHIND_PROXY
if BEHIND_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookies: not readable by JS (session), same-site, sent over HTTPS only in production.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # log in again after a week

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Redirect http → https and tell browsers to stay on https (HSTS).
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True") == "True"
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", str(60 * 60 * 24 * 30)))

# Django admin lives here; set ADMIN_URL to something less guessable in production.
ADMIN_URL = os.getenv("ADMIN_URL", "admin/").strip("/") + "/"

# Terms of Service / Privacy Policy (modules/legal). Bump TERMS_VERSION whenever
# either text changes in a way users must agree to: everyone is asked again.
TERMS_VERSION = "2026-10-18"
# Shown on the legal and help pages for privacy, copyright and abuse reports.
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "COLLABoardDevTeam@gmail.com")

# Rate-limit counters (single process, so local memory is enough).
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "collaboard"},
}

# -------------------------------------------------------------
# APPLICATIONS
# -------------------------------------------------------------
INSTALLED_APPS = [
    # ASGI server: must come first so `runserver` serves WebSockets too
    'daphne',

    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'channels',

    # Your modular apps
    'modules.authentication',
    'modules.profiles',         # ✅ renamed “profile” → “profiles” to avoid conflicts
    'modules.dashboard',
    'modules.settings_app',
    'modules.notifications',
    'modules.help_app',
    'modules.session',
    'modules.core',             # ✅ where base templates/icons live
    'modules.chat',
    'modules.legal',
]

# -------------------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'modules.core.middleware.security_headers.SecurityHeadersMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'modules.core.middleware.no_cache.NoCacheForAuthMiddleware',  # renamed to match actual class
    'django.contrib.messages.middleware.MessageMiddleware',
    'modules.legal.middleware.TermsAcceptanceMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -------------------------------------------------------------
# URL & WSGI
# -------------------------------------------------------------
ROOT_URLCONF = 'collaborative_whiteboard_backend.urls'
WSGI_APPLICATION = 'collaborative_whiteboard_backend.wsgi.application'
ASGI_APPLICATION = 'collaborative_whiteboard_backend.asgi.application'

# Realtime whiteboard (WebSockets). The in-memory layer needs a single server
# process, which is how the app runs (one Daphne process).
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

# -------------------------------------------------------------
# TEMPLATES
# -------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # ✅ Include a global "modules/core/templates" directory for shared templates
        'DIRS': [BASE_DIR / 'modules' / 'core' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'modules.notifications.notifcounts.notif_counts',  # was wrong module path
            ],
        },
    },
]

# -------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------
# SQLite by default. SQLITE_PATH lets production keep the file on a persistent
# disk; DATABASE_URL (PostgreSQL) still works if you ever move to a server DB.
SQLITE_PATH = os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3"))

if os.getenv("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(conn_max_age=600, ssl_require=not DEBUG)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": SQLITE_PATH,
            "OPTIONS": {
                # WAL + immediate transactions avoid "database is locked" when the
                # web and WebSocket handlers write at the same time.
                "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
                "transaction_mode": "IMMEDIATE",
                "timeout": 20,
            },
        }
    }

# -------------------------------------------------------------
# AUTHENTICATION
# -------------------------------------------------------------
AUTH_USER_MODEL = "authentication.CustomUser"
AUTHENTICATION_BACKENDS = [
    "modules.authentication.backends.EmailOrUsernameModelBackend",
]

LOGIN_REDIRECT_URL = "/dashboard/redirect/"
LOGOUT_REDIRECT_URL = "/auth/login/"
LOGIN_URL = "/auth/login/"

# -------------------------------------------------------------
# PASSWORD VALIDATION
# -------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    # Project-specific complexity validator: requires uppercase, digit, special char
    {'NAME': 'modules.authentication.validators.ComplexPasswordValidator'},
]

# -------------------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'  # ✅ optional — better for PH timezone
USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------
# STATIC & MEDIA FILES
# -------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

# App static folders (modules/<app>/static/) are found automatically.

# Snapshots and uploads are stored on local disk (MEDIA_ROOT) and served by
# the app at /media/. Point MEDIA_ROOT at a persistent disk in production.
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(BASE_DIR / 'media')))

# ✅ WhiteNoise for Render (static caching)
STORAGES = {
    # Handles Django static files
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },

    # ✅ Handles user uploads (images, PDFs, etc.)
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
            "base_url": MEDIA_URL,
        },
    },
}

# -------------------------------------------------------------
# DEFAULT PRIMARY KEY
# -------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------------------------------
# UPLOADS & LOGGING
# -------------------------------------------------------------
# Whiteboard snapshots are posted as PNG form data; allow up to 15 MB in memory.
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}

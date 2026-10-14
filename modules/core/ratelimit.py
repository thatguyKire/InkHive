"""Small cache-backed rate limiter (fixed windows).

Used for login/signup brute-force protection and to stop users spamming the
board APIs. Counters live in Django's cache (process memory by default, which
matches the single-process deployment).

IP addresses can be spoofed behind some proxies, so every security-relevant
limit is also keyed on something the client cannot forge (username, user id).
"""
import hashlib

from django.conf import settings
from django.core.cache import cache


def client_ip(request):
    """Best-effort client IP.

    Behind Render's proxy the client address is the first X-Forwarded-For
    entry. Only trust that header when TRUST_X_FORWARDED_FOR is on (it is
    enabled automatically on Render); otherwise use the socket address.
    """
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def _key(scope, ident):
    digest = hashlib.sha256(str(ident).lower().encode("utf-8")).hexdigest()[:32]
    return f"rl:{scope}:{digest}"


def count(scope, ident):
    return cache.get(_key(scope, ident), 0)


def is_limited(scope, ident, limit):
    return count(scope, ident) >= limit


def hit(scope, ident, window):
    """Record one event; returns the new count within the window."""
    key = _key(scope, ident)
    cache.add(key, 0, timeout=window)
    try:
        return cache.incr(key)
    except ValueError:  # expired between add() and incr()
        cache.set(key, 1, timeout=window)
        return 1


def allow(scope, ident, limit, window):
    """Count this event and say whether it is within the limit."""
    return hit(scope, ident, window) <= limit


def reset(scope, ident):
    cache.delete(_key(scope, ident))

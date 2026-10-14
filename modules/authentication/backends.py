import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from modules.core import ratelimit

logger = logging.getLogger("security")

# Brute-force protection (failed attempts per 15 minutes)
LOCKOUT_WINDOW = 15 * 60
MAX_FAILS_PER_IP_AND_ACCOUNT = 5
MAX_FAILS_PER_ACCOUNT = 10   # cannot be dodged by changing/spoofing IP
MAX_FAILS_PER_IP = 50        # one address guessing many accounts


class EmailOrUsernameModelBackend(ModelBackend):
    """Authenticate with either the username or the email address.

    The login page asks for "Username / Institutional Email", so both must work.
    Failed attempts are throttled; this backend also protects the Django admin
    login because it goes through the same authenticate() call.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        identifier = username.strip().lower()
        ip = ratelimit.client_ip(request) if request is not None else "no-request"
        pair = f"{ip}|{identifier}"

        if (ratelimit.is_limited("login-pair", pair, MAX_FAILS_PER_IP_AND_ACCOUNT)
                or ratelimit.is_limited("login-account", identifier, MAX_FAILS_PER_ACCOUNT)
                or ratelimit.is_limited("login-ip", ip, MAX_FAILS_PER_IP)):
            if request is not None:
                request.login_locked = True
            logger.warning("Login blocked (too many failures) for %r from %s", identifier, ip)
            # Hash anyway so a locked response takes as long as a normal one.
            get_user_model()().set_password(password)
            return None

        user = self._find_user(username.strip())
        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            ratelimit.reset("login-pair", pair)
            return user

        if user is None:
            # Run the hasher anyway to reduce timing differences.
            get_user_model()().set_password(password)
        ratelimit.hit("login-pair", pair, LOCKOUT_WINDOW)
        ratelimit.hit("login-account", identifier, LOCKOUT_WINDOW)
        ratelimit.hit("login-ip", ip, LOCKOUT_WINDOW)
        logger.info("Failed login for %r from %s", identifier, ip)
        return None

    @staticmethod
    def _find_user(identifier):
        User = get_user_model()
        if "@" in identifier:
            # Emails are stored lower-cased at signup; fall back to username
            # in case someone registered a username containing "@".
            user = User.objects.filter(email__iexact=identifier).order_by("id").first()
            if user is not None:
                return user
        return User.objects.filter(username=identifier).first()

"""Extra security headers that Django 5.2 does not set on its own.

* Content-Security-Policy: scripts only from this site (no inline scripts, no
  CDNs), so an injected <script> tag will not run even if escaping ever fails.
  Inline *styles* are still allowed because templates use style="" attributes.
* Permissions-Policy: the board needs none of these browser features.
"""

PERMISSIONS_POLICY = ", ".join(
    f"{feature}=()"
    for feature in (
        "accelerometer", "camera", "geolocation", "gyroscope", "magnetometer",
        "microphone", "payment", "usb",
    )
)


def build_csp(request):
    host = request.get_host()
    ws = "wss" if request.is_secure() else "ws"
    directives = {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self' 'unsafe-inline'",
        # data: for layer syncs (PNG data URLs), blob: for canvas exports
        "img-src": "'self' data: blob:",
        "font-src": "'self'",
        "connect-src": f"'self' {ws}://{host}",
        "media-src": "'self'",
        "object-src": "'none'",
        "frame-src": "'none'",
        "frame-ancestors": "'none'",
        "base-uri": "'none'",
        "form-action": "'self'",
    }
    return "; ".join(f"{k} {v}" for k, v in directives.items())


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Views may set a stricter policy (e.g. sandboxed uploaded files).
        if "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = build_csp(request)
        response.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        return response

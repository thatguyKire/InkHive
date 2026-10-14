# Security

**System:** COLLABoard: Collaborative Whiteboard · **Last review:** 2026-10-14

This document lists what COLLABoard protects, how, and what must be done before (and after) going live. Every control below has an automated test in `modules/core/test_security.py`, `modules/session/test_realtime.py` or the module test suites (97 tests in total).

> **Status: not yet approved for launch.** Complete the [pre-launch checklist](#4-pre-launch-checklist) first.

---

## 1. What we protect, and from whom

| Asset | Threat |
|---|---|
| Accounts (students, teachers, admins) | Password guessing, credential stuffing, session theft |
| Class boards (drawings, uploads, snapshots, chat) | Outsiders reading or drawing on a board; students taking over teacher controls |
| The server | Malicious uploads, injected scripts (XSS), request forgery (CSRF), flooding |
| Admin site | Brute force, discovery |

Out of scope for this app: DDoS at network level (handled by Render/Cloudflare), physical/host security (Render).

## 2. Controls

### 2.1 Authentication
| Control | Where |
|---|---|
| Passwords hashed with PBKDF2 (Django default) | Django |
| Password policy: ≥ 10 characters, upper case, digit, special character, not common, not numeric-only, not similar to username | `settings.AUTH_PASSWORD_VALIDATORS`, `authentication/validators.py` |
| **Brute-force lockout**: 5 failures per IP+account, 10 per account (any IP), 50 per IP, within 15 minutes → HTTP 429. Applies to the app login **and** the Django admin login. Correct password is refused while locked. | `authentication/backends.py` |
| Same cost for unknown users and locked accounts (password hashed anyway) to limit user enumeration by timing | `authentication/backends.py` |
| Sign-up limit: 10 accounts per IP per hour | `authentication/views.py` |
| Session cookie: HttpOnly, SameSite=Lax, Secure in production, expires after 7 days; session id rotated at login | `settings.py` |
| Logout only via POST with CSRF token | `authentication/urls.py` |
| Admin URL configurable (`ADMIN_URL`) so it is not at the well-known `/admin/` | `urls.py`, `settings.py` |

### 2.2 Authorization
| Control | Where |
|---|---|
| Every page and API except login/signup/health requires login | `@login_required` everywhere |
| Teacher-only pages need role `teacher`/`admin` | `role_required` |
| Every session action checks ownership (owner/staff) or membership (participant) on the server | `session/views/*`, `chat/views.py`, `notifications/views.py` |
| Drawing/uploading requires the teacher's per-student `can_draw` | upload view, WebSocket consumer |
| Users cannot sign up as admin | `authentication/forms.py` |
| Uploaded files and snapshots: only members of that session can download them (others get 404) | `core/views.py::media`, `session/access.py` |

### 2.3 Real-time (WebSocket)
| Control | Where |
|---|---|
| Only the session owner, staff, or participants can connect (session cookie); everyone else is closed with code 4403 | `session/consumers.py` |
| **Origin check** blocks cross-site WebSocket hijacking (a malicious site using a student's cookies) | `asgi.py` (`AllowedHostsOriginValidator`) |
| Server enforces rights per message: draw events need `can_draw`; `perm`, `meta` (chat toggle) and `clear_all` are teacher-only; unknown events dropped | `session/consumers.py` |
| Sender identity (`sid`) is overwritten by the server, so nobody can impersonate another user's strokes | `session/consumers.py` |
| Presence role cannot be faked (server sets `uid`/`role`) | `session/consumers.py` |
| Flood protection: > 200 messages/second are dropped; sustained flooding closes the connection (4429); frames > 2 MB, binary frames and malformed JSON are ignored | `session/consumers.py` |

### 2.4 Input, output and files
| Control | Where |
|---|---|
| Django templates auto-escape; no `|safe`/`mark_safe`; JS renders user text with `textContent` only | templates, JS |
| **Content-Security-Policy**: scripts only from this site, no inline scripts, no third-party scripts, no plugins, no framing, no `<base>` hijack, forms only to this site, connections only to this site | `core/middleware/security_headers.py` |
| All third-party assets vendored (Chart.js verified byte-identical to the official npm release) | `dashboard/static/dashboard/vendor/` |
| Uploads: extension allow-list (png, jpg, gif, webp, pdf, docx, pptx; **no** SVG/HTML), ≤ 10 MB, **content verified** (images parsed by Pillow, decompression bombs rejected, PDF/Office signatures checked), file names sanitized | `session/views/upload_views.py`, `session/file_checks.py` |
| Snapshots must be genuine PNGs (≤ 15 MB) | `session/views/manage_views.py` |
| Served files get `Content-Security-Policy: sandbox`, `nosniff`, and non-images are forced to download | `core/views.py::media` |
| Path traversal in `/media/` rejected | `django.views.static.serve` + strict path patterns |
| ORM only (no raw SQL), no `eval`, no shell calls, no pickle | code review |

### 2.5 Request forgery and transport
| Control | Where |
|---|---|
| CSRF token on every state-changing request, **no exemptions** (the page-unload beacon sends the token in its form body) | Django middleware, `participants.js` |
| HTTPS forced in production (HTTP → 301), HSTS 30 days, Secure cookies | `settings.py` |
| `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` (clickjacking) | `settings.py`, middleware |
| `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin`, `Permissions-Policy` disables camera, mic, location, payment, USB… | `settings.py`, middleware |
| Authenticated pages are not cached by browsers/proxies | `core/middleware/no_cache.py` |

### 2.6 Abuse limits
| Action | Limit |
|---|---|
| Wrong join codes | 10 per account per 10 min (stops scanning for class codes) |
| Chat messages | 30 per user per minute |
| Announcements | 10 per teacher per minute |
| Uploads / snapshots | 30 per user per 10 min each |

### 2.7 Configuration safety
| Control | Where |
|---|---|
| App **refuses to start** in production (DEBUG off) with the public development `SECRET_KEY` or any key shorter than 50 characters | `settings.py` |
| DEBUG defaults to off on Render; error pages never show stack traces in production | `settings.py` |
| Proxy headers (`X-Forwarded-For/Proto`) are trusted only behind Render (`RENDER`/`BEHIND_PROXY`), so they cannot be forged on a direct connection | `settings.py`, `core/ratelimit.py` |
| No third-party API keys exist; `.env` is gitignored | repo |
| Dependencies audited with `pip-audit`: **0 known vulnerabilities** (Django 5.2.18 LTS, Pillow 12.3.0, python-dotenv 1.2.4); unused Django REST Framework removed | `requirements.txt` |
| Security events logged (failed logins, lockouts, blocked sign-ups/joins, rejected uploads, flooding) to stdout | logger `security` and view loggers |

## 3. Known limitations (accepted for now)

| Limitation | Risk | Mitigation / plan |
|---|---|---|
| Anyone can sign up as a **teacher** | Low: a fake teacher only controls their own sessions and cannot see others' data | If needed, add admin approval for teacher accounts |
| Changing your email does not ask for your password | Low: email is not used for login recovery (no password reset by email) | Require password when email reset is added |
| Rate-limit counters are in memory | Restarting the server resets lockouts | Acceptable for one instance; use Redis cache if scaling out |
| Per-IP limits depend on Render's `X-Forwarded-For` | If Render's header is spoofable, the per-IP limit can be dodged | Per-account limits cannot be dodged and still apply |
| Inline `style=""` attributes allowed by CSP | Very low (style injection only) | Move styles to CSS files |
| A previous version of the app may still be running on Render | **High**: it lacks all of the above | See checklist item 1 |

## 4. Pre-launch checklist

Do these **in order** before letting users in:

1. ☐ **Suspend or redeploy the current Render service.** The live site still runs the old code (before these fixes). Render → *Settings* → *Suspend Web Service* until steps 2–8 are done.
2. ☐ In Render → *Environment*: **delete** `DATABASE_URL` and all `SUPABASE_*` variables.
3. ☐ Set `SECRET_KEY` to a fresh random value: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Never reuse a key that was ever committed or shared.
4. ☐ Set `ADMIN_URL` to something unguessable (e.g. `manage-7f3k9q/`).
5. ☐ Attach a persistent disk at `/var/data`; set `SQLITE_PATH=/var/data/db.sqlite3` and `MEDIA_ROOT=/var/data/media`.
6. ☐ Start command: `daphne -b 0.0.0.0 -p $PORT collaborative_whiteboard_backend.asgi:application`; instances = 1; health check path `/healthz/`.
7. ☐ Deploy, then create the admin with a strong unique password: `python manage.py createsuperuser` (Render shell).
8. ☐ Verify from outside: `http://` redirects to `https://`; `/admin/` returns 404; response headers include `Content-Security-Policy` and `Strict-Transport-Security`; a logged-out request to a `/media/...` URL redirects to login.
9. ☐ Run the two-browser checklist (Implementation Plan §6.2).
10. ☐ Turn on Render log alerts for repeated "Login blocked" / "Closing flooding" messages.

## 5. Ongoing maintenance

* Monthly: `pip-audit -r requirements.txt` and update Django (5.2 LTS gets security fixes until April 2028).
* Before every release: `python manage.py test modules`, `python manage.py check --deploy` with production environment variables.
* Rotate `SECRET_KEY` if it may have leaked (this logs everyone out).
* Back up `db.sqlite3` and `media/` regularly (see TRD §4).

## 6. Reporting a vulnerability

Please do not open a public GitHub issue. Email the lead developer (eriksamuel.bien@cit.edu) with steps to reproduce. We aim to respond within 7 days.

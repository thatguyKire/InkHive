"""Security regression tests: each test is an attack that must fail."""
import io
import json
import os
import re
import subprocess
import sys
import zipfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from modules.chat.models import ChatRoom
from modules.core.testing import AppTestCase, TEST_PASSWORD
from modules.session.models import Session, generate_session_code


def png_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, format="PNG")
    return buf.getvalue()


def docx_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>", re.I)
EXTERNAL_ASSET = re.compile(r"""<(?:script|link|img)[^>]+(?:src|href)=["']https?://""", re.I)


class SecurityHeaderTests(AppTestCase):
    def test_headers_on_every_page(self):
        self.client.force_login(self.teacher)
        resp = self.client.get(reverse("teacher_dashboard"))
        csp = resp["Content-Security-Policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline';", csp.split("script-src")[1].split(";")[0] + ";")
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertEqual(resp["X-Frame-Options"], "DENY")
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertIn("camera=()", resp["Permissions-Policy"])
        self.assertIn("no-store", resp["Cache-Control"])

    def test_no_inline_scripts_or_third_party_assets(self):
        """The CSP blocks inline scripts, so pages must not contain any."""
        self.join(self.student)
        pages = [
            (self.teacher, reverse("whiteboard", args=[self.session.id])),
            (self.teacher, reverse("attendance", args=[self.session.id])),
            (self.teacher, reverse("teacher_dashboard")),
            (self.teacher, reverse("session_list")),
            (self.student, reverse("student_whiteboard", args=[self.session.id])),
            (self.student, reverse("student_dashboard")),
            (None, reverse("auth:login")),
            (None, reverse("auth:signup")),
        ]
        for user, url in pages:
            with self.subTest(url=url):
                if user:
                    self.client.force_login(user)
                else:
                    self.client.logout()
                html = self.client.get(url).content.decode()
                self.assertIsNone(INLINE_SCRIPT.search(html), "inline <script> found")
                self.assertIsNone(EXTERNAL_ASSET.search(html), "third-party asset found")

    def test_healthz(self):
        self.assertEqual(self.client.get("/healthz/").content, b"ok")


class LoginBruteForceTests(AppTestCase):
    def attempt(self, username, password, ip="10.0.0.1", path=None):
        return self.client.post(path or reverse("auth:login"),
                                {"username": username, "password": password}, REMOTE_ADDR=ip)

    def test_lockout_after_five_failures_even_with_right_password(self):
        for _ in range(5):
            self.assertEqual(self.attempt("teacher1", "wrong").status_code, 200)
        resp = self.attempt("teacher1", TEST_PASSWORD)
        self.assertEqual(resp.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_account_limit_cannot_be_dodged_by_switching_ip(self):
        for i in range(10):
            self.attempt("teacher1", "wrong", ip=f"10.0.1.{i}")
        resp = self.attempt("teacher1", TEST_PASSWORD, ip="10.9.9.9")
        self.assertEqual(resp.status_code, 429)

    def test_email_and_username_count_as_same_account(self):
        for _ in range(5):
            self.attempt("TEACHER1@cit.edu", "wrong")
        self.assertEqual(self.attempt("teacher1@cit.edu", TEST_PASSWORD).status_code, 429)

    def test_other_accounts_unaffected(self):
        for _ in range(5):
            self.attempt("teacher1", "wrong")
        resp = self.attempt("student1", TEST_PASSWORD)
        self.assertEqual(resp.status_code, 302)

    def test_success_resets_pair_counter(self):
        for _ in range(4):
            self.attempt("teacher1", "wrong")
        self.assertEqual(self.attempt("teacher1", TEST_PASSWORD).status_code, 302)
        self.client.logout()
        for _ in range(4):
            self.attempt("teacher1", "wrong")
        self.assertEqual(self.attempt("teacher1", TEST_PASSWORD).status_code, 302)

    def test_admin_login_is_throttled_too(self):
        self.make_user("boss", "admin", is_staff=True, is_superuser=True)
        admin_login = reverse("admin:login")
        for _ in range(5):
            self.attempt("boss", "wrong", path=admin_login)
        self.attempt("boss", TEST_PASSWORD, path=admin_login)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_x_forwarded_for_ignored_unless_behind_proxy(self):
        """Without a trusted proxy, a forged header must not reset the IP limit."""
        for i in range(5):
            self.client.post(reverse("auth:login"), {"username": "teacher1", "password": "x"},
                             REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR=f"1.2.3.{i}")
        resp = self.client.post(reverse("auth:login"), {"username": "teacher1", "password": TEST_PASSWORD},
                                REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="9.9.9.9")
        self.assertEqual(resp.status_code, 429)


class AbuseLimitTests(AppTestCase):
    def test_signup_flood_blocked(self):
        for i in range(10):
            self.client.post(reverse("auth:signup"), {
                "username": f"bot{i}", "email": f"bot{i}@x.com", "role": "teacher",
                "password1": "An0ther!Pass", "password2": "An0ther!Pass", "accept_terms": "on"}, REMOTE_ADDR="10.1.1.1")
            self.client.logout()
        resp = self.client.post(reverse("auth:signup"), {
            "username": "bot99", "email": "bot99@x.com", "role": "teacher",
            "password1": "An0ther!Pass", "password2": "An0ther!Pass", "accept_terms": "on"}, REMOTE_ADDR="10.1.1.1")
        self.assertEqual(resp.status_code, 429)

    def test_join_code_scanning_blocked(self):
        self.client.force_login(self.other_student)
        for i in range(10):
            self.client.post(reverse("join_session"), {"code": f"ZZZZ{i:02d}"})
        resp = self.client.post(reverse("join_session"), {"code": self.session.code})
        self.assertEqual(resp.status_code, 429)  # even the right code is refused for a while

    def test_chat_spam_blocked(self):
        self.join(self.student)
        self.client.force_login(self.student)
        room = ChatRoom.objects.create(name="r", session=self.session)
        url = reverse("send_message", args=[room.id])
        codes = [self.client.post(url, json.dumps({"content": f"m{i}"}), content_type="application/json").status_code
                 for i in range(31)]
        self.assertEqual(codes[:30], [200] * 30)
        self.assertEqual(codes[30], 429)

    def test_weak_short_password_rejected(self):
        resp = self.client.post(reverse("auth:signup"), {
            "username": "shorty", "email": "s@x.com", "role": "teacher",
            "password1": "Ab1!xyz9", "password2": "Ab1!xyz9"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Session.objects.filter(created_by__username="shorty").exists())
        self.assertContains(resp, "too short")


class UploadContentTests(AppTestCase):
    def upload(self, name, data, ctype="application/octet-stream"):
        self.client.force_login(self.teacher)
        return self.client.post(reverse("upload_attachment", args=[self.session.id]),
                                {"file": SimpleUploadedFile(name, data, ctype)})

    def test_html_disguised_as_image_rejected(self):
        resp = self.upload("cat.png", b"<html><script>alert(1)</script></html>", "image/png")
        self.assertEqual(resp.status_code, 400)

    def test_svg_rejected(self):
        self.assertEqual(self.upload("x.svg", b"<svg onload=alert(1)>").status_code, 400)

    def test_fake_pdf_and_docx_rejected(self):
        self.assertEqual(self.upload("a.pdf", b"not a pdf").status_code, 400)
        self.assertEqual(self.upload("a.docx", b"PK\x03\x04garbage").status_code, 400)

    def test_png_named_jpg_rejected(self):
        self.assertEqual(self.upload("photo.jpg", png_bytes()).status_code, 400)

    def test_genuine_files_accepted(self):
        self.assertEqual(self.upload("a.png", png_bytes(), "image/png").status_code, 200)
        self.assertEqual(self.upload("a.pdf", b"%PDF-1.4\n%%EOF").status_code, 200)
        self.assertEqual(self.upload("a.docx", docx_bytes()).status_code, 200)

    def test_tricky_filename_is_sanitised(self):
        resp = self.upload('../../evil "name".png', png_bytes(), "image/png")
        url = resp.json()["file_url"]
        self.assertRegex(url, r"^/media/session_files/[0-9a-f-]{36}/\d+_[\w.-]+\.png$")


class MediaAccessTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.join(self.student)
        self.client.force_login(self.teacher)
        self.png_url = self.client.post(reverse("upload_attachment", args=[self.session.id]),
                                        {"file": SimpleUploadedFile("a.png", png_bytes(), "image/png")}).json()["file_url"]
        self.pdf_url = self.client.post(reverse("upload_attachment", args=[self.session.id]),
                                        {"file": SimpleUploadedFile("a.pdf", b"%PDF-1.4\n%%EOF")}).json()["file_url"]
        self.snap_url = self.client.post(reverse("save_snapshot", args=[self.session.id]),
                                         {"image": SimpleUploadedFile("s.png", png_bytes(), "image/png")}).json()["url"]

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        resp = self.client.get(self.png_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("auth:login"), resp["Location"])

    def test_outsider_gets_404(self):
        self.client.force_login(self.other_student)
        for url in (self.png_url, self.pdf_url, self.snap_url):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_participant_can_download_with_safe_headers(self):
        self.client.force_login(self.student)
        img = self.client.get(self.png_url)
        self.assertEqual(img.status_code, 200)
        self.assertIn("sandbox", img["Content-Security-Policy"])
        self.assertFalse(img.get("Content-Disposition", "").startswith("attachment"))  # images show inline
        pdf = self.client.get(self.pdf_url)
        self.assertTrue(pdf["Content-Disposition"].startswith("attachment"))

    def test_duplicate_session_members_can_see_shared_snapshot(self):
        copy = Session.objects.create(title="Copy", created_by=self.teacher, code=generate_session_code(),
                                      snapshot_url=self.snap_url)
        self.join(self.other_student, session=copy)
        self.client.force_login(self.other_student)
        self.assertEqual(self.client.get(self.snap_url).status_code, 200)

    def test_path_traversal_and_unknown_paths(self):
        self.client.force_login(self.teacher)
        for url in ("/media/../manage.py", "/media/%2e%2e/manage.py", "/media/snapshots/../../manage.py",
                    "/media/other/file.txt", f"/media/session_files/{self.session.id}/../../x"):
            with self.subTest(url=url):
                self.assertIn(self.client.get(url).status_code, (400, 404))


class CsrfTests(AppTestCase):
    def test_presence_sync_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.teacher)
        url = reverse("presence_sync", args=[self.session.id])
        self.assertEqual(client.post(url, {"present_user_ids": "[]"}).status_code, 403)

        client.get(reverse("whiteboard", args=[self.session.id]))  # sets csrftoken cookie
        token = client.cookies["csrftoken"].value
        resp = client.post(url, {"present_user_ids": "[]", "csrfmiddlewaretoken": token})
        self.assertEqual(resp.status_code, 200)

    def test_state_changing_endpoints_reject_missing_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.teacher)
        for url in (reverse("toggle_chat", args=[self.session.id]),
                    reverse("delete_session", args=[self.session.id]),
                    reverse("notifications:mark_all_read"),
                    reverse("auth:logout")):
            with self.subTest(url=url):
                self.assertEqual(client.post(url).status_code, 403)
        self.assertTrue(Session.objects.filter(id=self.session.id).exists())


class ProductionConfigTests(AppTestCase):
    def run_settings(self, **env):
        base = {k: v for k, v in os.environ.items() if k not in ("SECRET_KEY", "DEBUG", "RENDER")}
        base.update(env, DJANGO_SETTINGS_MODULE="collaborative_whiteboard_backend.settings")
        return subprocess.run([sys.executable, "-c", "import django; django.setup()"],
                              env=base, cwd=settings.BASE_DIR, capture_output=True, text=True)

    def test_refuses_to_start_with_default_secret_key(self):
        result = self.run_settings(DEBUG="False")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)

    def test_starts_with_strong_secret_key(self):
        result = self.run_settings(DEBUG="False", SECRET_KEY="x" * 64)
        self.assertEqual(result.returncode, 0, result.stderr)

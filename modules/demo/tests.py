import io
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from modules.authentication.models import CustomUser
from modules.core.testing import AppTestCase
from modules.session.models import Session, UploadedFile, generate_session_code
from .accounts import TEACHER, STUDENT, ensure_demo_data
from .views import DEMO_LOGINS_PER_IP_PER_HOUR


class DemoOffTests(AppTestCase):
    def test_no_demo_unless_turned_on(self):
        resp = self.client.get(reverse("auth:login"))
        self.assertNotContains(resp, "Try the demo")
        self.assertContains(resp, reverse("auth:signup"))
        self.assertEqual(self.client.post(reverse("demo:login", args=["teacher"])).status_code, 404)
        self.assertFalse(CustomUser.objects.filter(is_demo=True).exists())


@override_settings(DEMO_MODE=True)
class DemoModeTests(AppTestCase):
    def demo_login(self, role):
        return self.client.post(reverse("demo:login", args=[role]))

    def signed_in_as(self, username):
        return int(self.client.session.get("_auth_user_id", 0)) == CustomUser.objects.get(username=username).pk

    def test_login_page_offers_demo_and_hides_signup(self):
        resp = self.client.get(reverse("auth:login"))
        self.assertContains(resp, "Try the demo")
        self.assertContains(resp, reverse("demo:login", args=["teacher"]))
        self.assertNotContains(resp, reverse("auth:signup"))
        self.assertContains(self.client.get(reverse("legal:privacy")), "This site is a public demo")

    def test_signup_is_turned_off(self):
        resp = self.client.post(reverse("auth:signup"), {"username": "newbie", "email": "newbie@cit.edu"})
        self.assertRedirects(resp, reverse("auth:login"), fetch_redirect_response=False)
        self.assertFalse(CustomUser.objects.filter(username="newbie").exists())

    def test_teacher_button_signs_in_to_a_sample_class(self):
        resp = self.demo_login("teacher")
        self.assertRedirects(resp, reverse("redirect_dashboard"), fetch_redirect_response=False)
        self.assertTrue(self.signed_in_as(TEACHER))
        session = Session.objects.get(created_by__username=TEACHER)
        self.assertEqual(session.participants.count(), 2)
        self.assertContains(self.client.get(reverse("teacher_dashboard")), "Demo account.")

    def test_student_button(self):
        self.assertEqual(self.client.get(reverse("demo:login", args=["student"])).status_code, 405)
        self.assertEqual(self.demo_login("admin").status_code, 404)
        self.demo_login("student")
        self.assertTrue(self.signed_in_as(STUDENT))
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 200)

    def test_demo_accounts_have_no_password(self):
        ensure_demo_data()
        self.assertFalse(CustomUser.objects.get(username=TEACHER).has_usable_password())
        self.client.post(reverse("auth:login"), {"username": TEACHER, "password": ""})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_demo_accounts_cannot_lock_others_out(self):
        self.demo_login("student")
        for name in ("password_change", "edit_profile", "delete_account"):
            self.assertRedirects(self.client.get(reverse(name)), reverse("settings"), fetch_redirect_response=False)
            resp = self.client.post(reverse(name), {"password": "x", "confirm": "on", "email": "me@evil.example"})
            self.assertEqual(resp.status_code, 403)
        student = CustomUser.objects.get(username=STUDENT)
        self.assertEqual(student.email, f"{STUDENT}@demo.invalid")
        page = self.client.get(reverse("settings"))
        self.assertNotContains(page, reverse("delete_account"))
        self.assertNotContains(page, reverse("edit_profile"))

    def test_demo_resets_after_a_day_without_touching_real_accounts(self):
        self.demo_login("teacher")
        teacher = CustomUser.objects.get(username=TEACHER)
        board = Session.objects.create(title="A visitor's board", created_by=teacher, code=generate_session_code())
        path = default_storage.save(f"session_files/{board.id}/1_cat.png", ContentFile(b"x"))
        UploadedFile.objects.create(session=board, uploaded_by=teacher, file=path, file_url=settings.MEDIA_URL + path)

        ensure_demo_data()  # less than a day old: nothing changes
        self.assertTrue(Session.objects.filter(pk=board.pk).exists())

        CustomUser.objects.filter(is_demo=True).update(date_joined=timezone.now() - timedelta(hours=25))
        self.demo_login("student")
        self.assertFalse(Session.objects.filter(pk=board.pk).exists())
        self.assertFalse(default_storage.exists(path))
        self.assertEqual(Session.objects.filter(created_by__username=TEACHER).count(), 1)
        self.assertTrue(Session.objects.filter(pk=self.session.pk).exists())
        self.assertEqual(CustomUser.objects.filter(is_demo=False).count(), 3)

    def test_seed_command(self):
        call_command("seed_demo", stdout=io.StringIO())
        first = CustomUser.objects.get(username=TEACHER).pk
        call_command("seed_demo", "--reset", stdout=io.StringIO())
        self.assertNotEqual(CustomUser.objects.get(username=TEACHER).pk, first)
        self.assertEqual(CustomUser.objects.filter(is_demo=True).count(), 3)

    def test_demo_login_is_rate_limited(self):
        for _ in range(DEMO_LOGINS_PER_IP_PER_HOUR):
            self.demo_login("student")
        resp = self.demo_login("teacher")
        self.assertRedirects(resp, reverse("auth:login"), fetch_redirect_response=False)
        self.assertTrue(self.signed_in_as(STUDENT))

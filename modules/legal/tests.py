import json

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import override_settings
from django.urls import reverse

from modules.authentication.models import CustomUser
from modules.chat.models import ChatRoom, Message
from modules.core.testing import CollaboardTestCase, TEST_PASSWORD
from modules.notifications.models import Notification
from modules.session.models import Session, Participant, UploadedFile, generate_session_code


class LegalPageTests(CollaboardTestCase):
    def test_terms_and_privacy_are_public(self):
        for name in ("legal:terms", "legal:privacy"):
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, settings.CONTACT_EMAIL)
            self.assertNotContains(resp, "<script")  # CSP: no inline scripts

    def test_auth_pages_link_to_terms(self):
        for name in ("auth:login", "auth:signup"):
            resp = self.client.get(reverse(name))
            self.assertContains(resp, reverse("legal:terms"))
            self.assertContains(resp, reverse("legal:privacy"))


class SignupAgreementTests(CollaboardTestCase):
    def signup(self, **extra):
        data = {
            "username": "newbie", "email": "newbie@cit.edu", "student_id": "2024-7777", "role": "student",
            "password1": "An0ther!Pass", "password2": "An0ther!Pass",
        }
        data.update(extra)
        return self.client.post(reverse("auth:signup"), data)

    def test_signup_requires_agreement(self):
        resp = self.signup()
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please agree to the Terms of Service")
        self.assertFalse(CustomUser.objects.filter(username="newbie").exists())

    def test_signup_records_agreement(self):
        self.signup(accept_terms="on")
        user = CustomUser.objects.get(username="newbie")
        self.assertEqual(user.terms_version, settings.TERMS_VERSION)
        self.assertIsNotNone(user.terms_accepted_at)


class TermsGateTests(CollaboardTestCase):
    """Users who have not agreed to the current terms must do so first."""

    def setUp(self):
        super().setUp()
        self.legacy = self.make_user("legacy", "student", student_id="2024-0100", terms_version="")
        self.client.force_login(self.legacy)

    def test_pages_redirect_to_accept(self):
        resp = self.client.get(reverse("student_dashboard"))
        self.assertRedirects(resp, reverse("legal:accept") + "?next=%2Fdashboard%2Fstudent%2F",
                             fetch_redirect_response=False)

    def test_other_requests_are_refused(self):
        resp = self.client.post(reverse("join_session"), {"code": self.session.code})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Participant.objects.filter(user=self.legacy).exists())

    def test_exempt_pages_still_work(self):
        self.assertEqual(self.client.get(reverse("legal:terms")).status_code, 200)
        self.assertEqual(self.client.get(reverse("legal:accept")).status_code, 200)
        self.assertEqual(self.client.get(reverse("export_data")).status_code, 200)
        self.assertEqual(self.client.get(reverse("delete_account")).status_code, 200)
        self.client.post(reverse("auth:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_accept_requires_the_box(self):
        resp = self.client.post(reverse("legal:accept"))
        self.assertEqual(resp.status_code, 200)
        self.legacy.refresh_from_db()
        self.assertEqual(self.legacy.terms_version, "")

    def test_accept_records_and_returns(self):
        resp = self.client.post(reverse("legal:accept"), {"agree": "on", "next": "/dashboard/student/"})
        self.assertRedirects(resp, "/dashboard/student/", fetch_redirect_response=False)
        self.legacy.refresh_from_db()
        self.assertTrue(self.legacy.has_accepted_terms)
        self.assertIsNotNone(self.legacy.terms_accepted_at)
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 200)

    def test_accept_ignores_offsite_next(self):
        resp = self.client.post(reverse("legal:accept"), {"agree": "on", "next": "https://evil.example/"})
        self.assertRedirects(resp, reverse("redirect_dashboard"), fetch_redirect_response=False)

    def test_changed_terms_ask_again(self):
        self.client.force_login(self.student)  # agreed to the current version
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 200)
        with override_settings(TERMS_VERSION="2099-01-01"):
            resp = self.client.get(reverse("student_dashboard"))
            self.assertEqual(resp.status_code, 302)
            self.assertContains(self.client.get(reverse("legal:accept")), "We've updated our terms")


class ExportDataTests(CollaboardTestCase):
    def test_export_contains_own_data_only(self):
        self.join(self.student)
        room = ChatRoom.objects.create(name="Algebra chat", session=self.session)
        Message.objects.create(room=room, sender=self.student, content="my answer is 42")
        Message.objects.create(room=room, sender=self.other_student, content="someone else's message")
        Notification.objects.create(recipient=self.student, session=self.session, content="Quiz tomorrow")

        self.client.force_login(self.student)
        resp = self.client.get(reverse("export_data"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment", resp["Content-Disposition"])
        data = json.loads(resp.content)
        self.assertEqual(data["account"]["email"], "student1@cit.edu")
        self.assertEqual(data["account"]["student_id"], "2024-0001")
        self.assertEqual([s["session_title"] for s in data["sessions_joined"]], ["Algebra"])
        self.assertEqual([m["content"] for m in data["chat_messages"]], ["my answer is 42"])
        self.assertEqual([n["content"] for n in data["notifications"]], ["Quiz tomorrow"])
        self.assertNotIn("someone else", resp.content.decode())
        self.assertNotIn("password", data["account"])

    def test_teacher_export_lists_created_sessions(self):
        self.client.force_login(self.teacher)
        data = json.loads(self.client.get(reverse("export_data")).content)
        self.assertEqual([s["title"] for s in data["sessions_created"]], ["Algebra"])


class DeleteAccountTests(CollaboardTestCase):
    def save_file(self, path):
        return default_storage.save(path, ContentFile(b"x"))

    def test_wrong_password_or_no_confirm_keeps_account(self):
        self.client.force_login(self.student)
        resp = self.client.post(reverse("delete_account"), {"password": "wrong", "confirm": "on"})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(reverse("delete_account"), {"password": TEST_PASSWORD})
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(CustomUser.objects.filter(pk=self.student.pk).exists())

    def test_password_guessing_is_limited(self):
        self.client.force_login(self.student)
        for _ in range(5):
            self.client.post(reverse("delete_account"), {"password": "wrong", "confirm": "on"})
        resp = self.client.post(reverse("delete_account"), {"password": TEST_PASSWORD, "confirm": "on"})
        self.assertEqual(resp.status_code, 429)
        self.assertTrue(CustomUser.objects.filter(pk=self.student.pk).exists())

    def test_staff_cannot_self_delete(self):
        admin = CustomUser.objects.create_superuser("root", "root@cit.edu", TEST_PASSWORD,
                                                   terms_version=settings.TERMS_VERSION)
        self.client.force_login(admin)
        resp = self.client.post(reverse("delete_account"), {"password": TEST_PASSWORD, "confirm": "on"})
        self.assertRedirects(resp, reverse("settings"))
        self.assertTrue(CustomUser.objects.filter(pk=admin.pk).exists())

    def test_teacher_deletion_removes_sessions_and_files(self):
        snap = self.save_file(f"snapshots/{self.session.id}_1.png")
        self.session.snapshot_url = settings.MEDIA_URL + snap
        self.session.save()
        upload = self.save_file(f"session_files/{self.session.id}/1_notes.pdf")
        UploadedFile.objects.create(session=self.session, uploaded_by=self.student, file=upload,
                                    file_url=settings.MEDIA_URL + upload)
        self.join(self.student)
        Notification.objects.create(recipient=self.student, session=self.session, content="Algebra starts")

        self.client.force_login(self.teacher)
        resp = self.client.post(reverse("delete_account"), {"password": TEST_PASSWORD, "confirm": "on"})
        self.assertRedirects(resp, reverse("auth:login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(CustomUser.objects.filter(pk=self.teacher.pk).exists())
        self.assertFalse(Session.objects.filter(pk=self.session.pk).exists())
        self.assertFalse(Participant.objects.filter(user=self.student).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.student).exists())
        self.assertFalse(default_storage.exists(snap))
        self.assertFalse(default_storage.exists(upload))
        self.assertTrue(CustomUser.objects.filter(pk=self.student.pk).exists())

    def test_student_deletion_removes_their_uploads_only(self):
        mine = self.save_file(f"session_files/{self.session.id}/1_mine.png")
        theirs = self.save_file(f"session_files/{self.session.id}/1_theirs.png")
        for user, path in ((self.student, mine), (self.other_student, theirs)):
            UploadedFile.objects.create(session=self.session, uploaded_by=user, file=path,
                                        file_url=settings.MEDIA_URL + path)
        self.join(self.student)

        self.client.force_login(self.student)
        self.client.post(reverse("delete_account"), {"password": TEST_PASSWORD, "confirm": "on"})
        self.assertFalse(CustomUser.objects.filter(pk=self.student.pk).exists())
        self.assertFalse(default_storage.exists(mine))
        self.assertTrue(default_storage.exists(theirs))
        self.assertTrue(Session.objects.filter(pk=self.session.pk).exists())


class SessionDeleteFilesTests(CollaboardTestCase):
    def test_deleting_a_session_removes_its_files_but_keeps_shared_snapshots(self):
        snap = default_storage.save(f"snapshots/{self.session.id}_2.png", ContentFile(b"x"))
        self.session.snapshot_url = settings.MEDIA_URL + snap
        self.session.save()
        copy = Session.objects.create(title="Algebra (copy)", created_by=self.teacher, code=generate_session_code(),
                                      snapshot_url=self.session.snapshot_url)
        upload = default_storage.save(f"session_files/{self.session.id}/2_a.pdf", ContentFile(b"x"))
        UploadedFile.objects.create(session=self.session, uploaded_by=self.teacher, file=upload,
                                    file_url=settings.MEDIA_URL + upload)

        self.client.force_login(self.teacher)
        self.client.post(reverse("delete_session", args=[self.session.id]))
        self.assertFalse(default_storage.exists(upload))
        self.assertTrue(default_storage.exists(snap))  # the copy still uses it

        self.client.post(reverse("delete_session", args=[copy.id]))
        self.assertFalse(default_storage.exists(snap))

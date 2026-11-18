import json

from django.conf import settings
from django.urls import reverse

from modules.authentication.models import CustomUser
from modules.chat.models import ChatRoom, Message
from modules.core.testing import AppTestCase, TEST_PASSWORD
from modules.session.models import Session


class DashboardTests(AppTestCase):
    def test_teacher_metrics_are_real(self):
        p = self.join(self.student, can_draw=True)
        p.strokes_count = 7
        p.save()
        room = ChatRoom.objects.create(name="r", session=self.session)
        Message.objects.create(room=room, sender=self.student, content="hi")

        self.client.force_login(self.teacher)
        resp = self.client.get(reverse("teacher_dashboard"))
        self.assertEqual(resp.status_code, 200)
        totals = resp.context["performance_totals"]
        self.assertEqual(totals["total_students"], 1)
        self.assertEqual(totals["total_strokes"], 7)
        self.assertEqual(totals["total_messages"], 1)
        self.assertEqual(totals["active_today"], 1)

    def test_student_counted_once_across_sessions(self):
        second = Session.objects.create(title="Physics", created_by=self.teacher, code="PHY234")
        self.join(self.student)
        self.join(self.student, session=second)
        self.client.force_login(self.teacher)
        rows = self.client.get(reverse("teacher_dashboard")).context["performance_rows"]
        self.assertEqual(len(rows), 1)

    def test_student_dashboard_has_chart_host(self):
        self.join(self.student)
        self.client.force_login(self.student)
        resp = self.client.get(reverse("student_dashboard"))
        self.assertContains(resp, 'id="participationGraph"')
        self.assertContains(resp, reverse("student_whiteboard", args=[self.session.id]))

    def test_admin_dashboard_shows_real_counts(self):
        admin = CustomUser.objects.create_superuser("root", "root@cit.edu", TEST_PASSWORD,
                                                   terms_version=settings.TERMS_VERSION)
        self.client.force_login(admin)
        resp = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(resp.context["student_count"], 2)
        self.assertEqual(resp.context["teacher_count"], 1)
        self.assertEqual(resp.context["session_count"], 1)

    def test_students_blocked_from_teacher_dashboard(self):
        self.client.force_login(self.student)
        self.assertRedirects(self.client.get(reverse("teacher_dashboard")), reverse("redirect_dashboard"),
                             target_status_code=302)


class PageSmokeTests(AppTestCase):
    """Every page renders for the roles that can see it."""

    def test_pages_render(self):
        self.join(self.student)
        pages = {
            self.teacher: ["teacher_dashboard", "session_list", "saved_sessions", "profile", "edit_profile",
                           "settings", "password_change", "help", "notifications:notifications"],
            self.student: ["student_dashboard", "join_session", "profile", "edit_profile", "settings", "help",
                           "notifications:notifications"],
        }
        for user, names in pages.items():
            self.client.force_login(user)
            for name in names:
                with self.subTest(user=user.username, page=name):
                    self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(reverse("attendance", args=[self.session.id])).status_code, 200)

    def test_anonymous_pages(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("auth:login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("auth:signup")).status_code, 200)
        self.assertRedirects(self.client.get("/"), reverse("auth:login"))
        resp = self.client.get(reverse("session_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("auth:login"), resp["Location"])

    def test_edit_profile_email_validation(self):
        self.client.force_login(self.student)
        self.client.post(reverse("edit_profile"), {"email": "teacher1@cit.edu"})
        self.student.refresh_from_db()
        self.assertEqual(self.student.email, "student1@cit.edu")
        self.client.post(reverse("edit_profile"), {"email": "Fresh@cit.edu"})
        self.student.refresh_from_db()
        self.assertEqual(self.student.email, "fresh@cit.edu")


class TeacherHomeTests(AppTestCase):
    """The redesigned teacher dashboard shows real numbers, not the mockup's."""

    def test_overview_counts_this_week_and_live_users(self):
        from modules.session.presence import PRESENCE

        self.join(self.student)
        PRESENCE[str(self.session.id)]["chan-1"] = {"uid": str(self.student.id), "meta": {}}
        self.addCleanup(PRESENCE.clear)
        self.client.force_login(self.teacher)
        resp = self.client.get(reverse("teacher_dashboard"))
        self.assertEqual(resp.context["class_count"], 1)
        self.assertEqual(resp.context["classes_this_week"], 1)
        self.assertEqual(resp.context["students_this_week"], 1)
        [session] = resp.context["open_sessions"]
        self.assertEqual((session.online, session.student_count), (1, 1))
        self.assertContains(resp, "Live &middot; 1 online", html=False)

    def test_bulletin_lists_sent_announcements(self):
        from modules.notifications.notify import notify

        self.join(self.student)
        notify(self.student, "Bring your rulers tomorrow", session=self.session)
        self.client.force_login(self.teacher)
        resp = self.client.get(reverse("teacher_dashboard"))
        self.assertContains(resp, "Bring your rulers tomorrow")
        self.assertContains(resp, "Algebra:")


class InitialsTests(AppTestCase):
    def test_initials_from_full_name_or_username(self):
        self.teacher.first_name, self.teacher.last_name = "Maria", "Reyes"
        self.assertEqual((self.teacher.display_name, self.teacher.initials), ("Maria Reyes", "MR"))
        self.assertEqual(CustomUser(username="demo_teacher").initials, "DT")
        self.assertEqual(CustomUser(username="x").initials, "X")

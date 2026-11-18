"""The app shell in core/templates/core/base.html: flash messages and layout hooks."""
from django.urls import reverse

from modules.core.testing import AppTestCase


class FlashMessageTests(AppTestCase):
    def test_message_shows_once_on_the_page_after_a_redirect(self):
        # The profile page has no message markup of its own; the shell shows it as a toast.
        self.client.force_login(self.student)
        resp = self.client.post(reverse("edit_profile"), {"email": "new@cit.edu"}, follow=True)
        self.assertRedirects(resp, reverse("profile"))
        self.assertContains(resp, "Profile updated successfully.", count=1)
        self.assertContains(resp, 'class="toast toast--success"')

    def test_page_with_inline_errors_does_not_repeat_them_as_toasts(self):
        self.client.force_login(self.student)
        resp = self.client.post(reverse("delete_account"), {"password": "wrong", "confirm": "on"})
        self.assertContains(resp, "Wrong password", count=1, status_code=400)
        self.assertNotContains(resp, 'id="toastStack"', status_code=400)


class LayoutHookTests(AppTestCase):
    def test_only_the_whiteboard_locks_the_main_area_to_the_viewport(self):
        self.client.force_login(self.teacher)
        board = self.client.get(reverse("whiteboard", args=[self.session.id]))
        self.assertContains(board, 'class="main main--fill"')
        dashboard = self.client.get(reverse("teacher_dashboard"))
        self.assertNotContains(dashboard, "main--fill")

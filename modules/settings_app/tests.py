from django.urls import reverse

from modules.core.testing import AppTestCase


class SettingsPageTests(AppTestCase):
    def test_password_card_links_to_password_change(self):
        self.client.force_login(self.student)
        page = self.client.get(reverse("settings"))
        self.assertContains(page, f'href="{reverse("password_change")}"')

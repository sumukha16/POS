from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .middleware import SERVER_INSTANCE_ID


class POSAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cashier",
            password="test-password",
        )

    def test_pos_screen_requires_login(self):
        response = self.client.get(reverse("pos:table_screen"))

        self.assertRedirects(response, reverse("admin_panel:login"))

    def test_pos_screen_is_available_to_an_authenticated_user(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["pos_server_instance_id"] = SERVER_INSTANCE_ID
        session.save()

        response = self.client.get(reverse("pos:table_screen"))

        self.assertEqual(response.status_code, 200)

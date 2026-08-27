from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class UserManagementTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="owner",
            password="test-password",
            email="owner@example.com",
        )
        self.cashier = get_user_model().objects.create_user(
            username="cashier",
            password="test-password",
        )

    def test_only_a_superuser_can_open_user_management(self):
        self.client.force_login(self.cashier)

        response = self.client.get(reverse("admin_panel:user_management"))

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_create_a_cashier(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("admin_panel:user_management"),
            {
                "username": "new-cashier",
                "password1": "A-secure-password-123",
                "password2": "A-secure-password-123",
            },
        )

        self.assertRedirects(response, reverse("admin_panel:user_management"))
        user = get_user_model().objects.get(username="new-cashier")
        self.assertTrue(user.check_password("A-secure-password-123"))
        self.assertFalse(user.is_staff)

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient


class WebConsoleAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="console-user", password="test-password")
        self.client = APIClient(enforce_csrf_checks=True)

    def test_session_endpoint_is_public_and_sets_csrf_cookie(self):
        response = self.client.get("/api/auth/session/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "username": None})
        self.assertIn("csrftoken", response.cookies)

    def test_login_establishes_session_for_protected_api(self):
        self.client.get("/api/auth/session/")
        response = self.client.post(
            "/api/auth/login/",
            {"username": "console-user", "password": "test-password"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        dashboard = self.client.get("/api/dashboard/")
        self.assertEqual(dashboard.status_code, 200)

    def test_invalid_login_is_rejected(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "console-user", "password": "wrong"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid username or password.")

    def test_registration_creates_user_and_session(self):
        self.client.get("/api/auth/session/")
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "new-user",
                "email": "new@example.com",
                "password": "long-test-password",
                "password_confirm": "long-test-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["authenticated"])
        self.assertTrue(User.objects.filter(username="new-user", email="new@example.com").exists())
        dashboard = self.client.get("/api/dashboard/")
        self.assertEqual(dashboard.status_code, 200)

    def test_registration_rejects_duplicate_username_and_mismatched_password(self):
        duplicate = self.client.post(
            "/api/auth/register/",
            {
                "username": "console-user",
                "email": "other@example.com",
                "password": "long-test-password",
                "password_confirm": "long-test-password",
            },
            format="json",
        )
        mismatch = self.client.post(
            "/api/auth/register/",
            {
                "username": "another-user",
                "email": "another@example.com",
                "password": "long-test-password",
                "password_confirm": "different-password",
            },
            format="json",
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(mismatch.status_code, 400)

    def test_logout_requires_csrf_and_ends_session(self):
        self.client.get("/api/auth/session/")
        self.client.post(
            "/api/auth/login/",
            {"username": "console-user", "password": "test-password"},
            format="json",
        )
        csrf_token = self.client.cookies["csrftoken"].value

        response = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        protected = self.client.get("/api/dashboard/")
        self.assertIn(protected.status_code, {401, 403})

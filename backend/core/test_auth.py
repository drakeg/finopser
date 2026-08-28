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

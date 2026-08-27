from django.test import SimpleTestCase, TestCase


class FoundationEndpointTests(SimpleTestCase):
    def test_health_endpoint(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_session_is_anonymous_by_default(self):
        response = self.client.get("/api/auth/session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "username": None})

    def test_request_id_is_added(self):
        response = self.client.get("/api/health/", HTTP_X_REQUEST_ID="test-request-id")
        self.assertEqual(response["X-Request-ID"], "test-request-id")


class ReadinessIntegrationTests(TestCase):
    def test_readiness_checks_required_dependencies(self):
        response = self.client.get("/api/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"], {"database": "ok", "redis": "ok"})

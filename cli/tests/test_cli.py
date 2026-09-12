import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from finopser_cli.client import FinopserClient, FinopserClientError
from finopser_cli.main import COMMAND_PATHS, run


class ResponseStub:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FinopserClientTests(unittest.TestCase):
    def test_client_sends_bearer_token_to_read_only_endpoint(self):
        with patch("finopser_cli.client.urlopen", return_value=ResponseStub({"ok": True})) as opener:
            payload = FinopserClient("http://localhost:8000", "finopser_prefix_secret").get(
                "/api/cloud-accounts/"
            )

        self.assertEqual(payload, {"ok": True})
        request = opener.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url, "http://localhost:8000/api/cloud-accounts/")
        self.assertEqual(request.get_header("Authorization"), "Bearer finopser_prefix_secret")

    def test_client_rejects_invalid_url_and_empty_token(self):
        with self.assertRaises(ValueError):
            FinopserClient("localhost:8000", "token")
        with self.assertRaises(ValueError):
            FinopserClient("http://localhost:8000", "")

    def test_http_error_uses_server_detail_without_token(self):
        error = HTTPError(
            "http://localhost:8000/api/resources/",
            401,
            "Unauthorized",
            {},
            io.BytesIO(b'{"detail":"API token does not have the required scope."}'),
        )
        with patch("finopser_cli.client.urlopen", side_effect=error):
            with self.assertRaisesRegex(FinopserClientError, "required scope") as raised:
                FinopserClient("http://localhost:8000", "sensitive-token").get("/api/resources/")
        self.assertNotIn("sensitive-token", str(raised.exception))

    def test_network_error_is_normalized(self):
        with patch("finopser_cli.client.urlopen", side_effect=URLError("connection refused")):
            with self.assertRaisesRegex(FinopserClientError, "Unable to reach Finopser"):
                FinopserClient("http://localhost:8000", "token").get("/api/accounts/")


class CliTests(unittest.TestCase):
    def test_all_supported_commands_map_to_approved_read_only_paths(self):
        self.assertEqual(
            COMMAND_PATHS,
            {
                "dashboard": "/api/dashboard/",
                "accounts": "/api/cloud-accounts/",
                "resources": "/api/resources/",
                "costs": "/api/costs/",
                "compliance": "/api/compliance/findings/",
                "policy-violations": "/api/policy-violations/",
                "recommendations": "/api/recommendations/",
                "reports": "/api/reports/",
            },
        )

    def test_compact_output_is_deterministic_json(self):
        output = io.StringIO()
        with patch("finopser_cli.main.FinopserClient") as client_type:
            client_type.return_value.get.return_value = {"b": 2, "a": 1}
            with redirect_stdout(output):
                code = run(
                    [
                        "--url",
                        "http://localhost:8000",
                        "--token",
                        "token",
                        "--compact",
                        "accounts",
                    ]
                )

        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue(), '{"a":1,"b":2}\n')

    def test_client_failure_returns_nonzero_and_stderr(self):
        stderr = io.StringIO()
        with patch("finopser_cli.main.FinopserClient") as client_type:
            client_type.return_value.get.side_effect = FinopserClientError("request denied")
            with redirect_stderr(stderr):
                code = run(["--url", "http://localhost:8000", "--token", "token", "accounts"])

        self.assertEqual(code, 1)
        self.assertIn("request denied", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

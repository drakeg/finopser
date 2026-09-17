from pathlib import Path
from django.test import SimpleTestCase


class IntegrationDestinationDependencyBoundaryTests(SimpleTestCase):
    def test_destination_api_does_not_import_http_client(self):
        source = Path(__file__).with_name("integration_destination_api.py").read_text()
        self.assertNotIn("import requests", source)
        self.assertNotIn("import httpx", source)
        self.assertNotIn("urllib.request", source)

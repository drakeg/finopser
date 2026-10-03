from django.test import SimpleTestCase

from .providers.registry import AWSFinOpsProvider, get_provider, register_provider


class ProviderRegistryTests(SimpleTestCase):
    def test_aws_provider_is_registered(self):
        self.assertIsInstance(get_provider("aws"), AWSFinOpsProvider)

    def test_provider_lookup_is_normalized(self):
        self.assertIsInstance(get_provider(" AWS "), AWSFinOpsProvider)

    def test_recognized_but_unimplemented_provider_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "Unsupported cloud provider: azure"):
            get_provider("azure")

    def test_duplicate_provider_registration_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "Cloud provider already registered: aws"):
            register_provider("AWS", AWSFinOpsProvider)

    def test_empty_provider_registration_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "Provider name is required"):
            register_provider(" ", AWSFinOpsProvider)

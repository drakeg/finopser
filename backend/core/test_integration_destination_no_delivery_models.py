from django.apps import apps
from django.test import SimpleTestCase


class IntegrationDestinationDeliveryModelBoundaryTests(SimpleTestCase):
    def test_slice_one_does_not_add_delivery_history_model(self):
        model_names = {model.__name__ for model in apps.get_app_config("core").get_models()}
        self.assertNotIn("IntegrationDelivery", model_names)
        self.assertNotIn("WebhookDelivery", model_names)

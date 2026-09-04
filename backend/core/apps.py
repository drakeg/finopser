from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from . import (  # noqa: F401
            account_models,
            automation_models,
            recommendation_models,
            vending_models,
        )

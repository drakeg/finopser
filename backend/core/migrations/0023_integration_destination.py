# Generated for Sprint 24

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0022_service_principal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationDestination",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("destination_type", models.CharField(choices=[("webhook", "Webhook")], default="webhook", max_length=32)),
                ("endpoint_url", models.URLField(max_length=500)),
                ("signing_secret_digest", models.CharField(max_length=64)),
                ("signing_secret_prefix", models.CharField(max_length=16)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("disabled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_integration_destinations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="integration_destinations",
                        to="core.organization",
                    ),
                ),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="integrationdestination",
            constraint=models.UniqueConstraint(
                fields=("organization", "name"),
                name="uniq_integration_destination_org_name",
            ),
        ),
    ]

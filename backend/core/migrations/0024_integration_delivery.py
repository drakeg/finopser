# Generated for Sprint 24 slice 2

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0023_integration_destination")]

    operations = [
        migrations.CreateModel(
            name="IntegrationDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=80)),
                ("event_id", models.CharField(max_length=64)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("succeeded", "Succeeded"), ("failed", "Failed")], default="pending", max_length=16)),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("response_status", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("last_error", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attempted_at", models.DateTimeField(blank=True, null=True)),
                ("destination", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deliveries", to="core.integrationdestination")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="integration_deliveries", to="core.organization")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]

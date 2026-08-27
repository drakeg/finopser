# Generated for finopser Sprint 4.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0003_cloudaccount")]

    operations = [
        migrations.CreateModel(
            name="InventorySync",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("running", "Running"), ("success", "Success"), ("partial", "Partial"), ("failed", "Failed")], default="running", max_length=32)),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("discovered_count", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("updated_count", models.PositiveIntegerField(default=0)),
                ("stale_count", models.PositiveIntegerField(default=0)),
                ("errors", models.JSONField(blank=True, default=list)),
                ("cloud_account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory_syncs", to="core.cloudaccount")),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="CloudResource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=32)),
                ("provider_resource_id", models.CharField(max_length=1024)),
                ("resource_type", models.CharField(db_index=True, max_length=128)),
                ("name", models.CharField(blank=True, max_length=512)),
                ("region", models.CharField(blank=True, db_index=True, max_length=64)),
                ("state", models.CharField(blank=True, db_index=True, max_length=128)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("first_seen", models.DateTimeField(auto_now_add=True)),
                ("last_seen", models.DateTimeField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("tags", models.JSONField(blank=True, default=dict)),
                ("cloud_account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resources", to="core.cloudaccount")),
            ],
            options={"ordering": ["resource_type", "name", "provider_resource_id"]},
        ),
        migrations.AddConstraint(
            model_name="cloudresource",
            constraint=models.UniqueConstraint(fields=("provider", "cloud_account", "provider_resource_id"), name="uniq_cloud_resource_identity"),
        ),
    ]

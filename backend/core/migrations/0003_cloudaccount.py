# Generated for Sprint 3 AWS account onboarding.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_seed_roles")]

    operations = [
        migrations.CreateModel(
            name="CloudAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("aws", "Amazon Web Services")], default="aws", max_length=32)),
                ("name", models.CharField(max_length=200)),
                ("provider_account_id", models.CharField(max_length=64)),
                ("role_arn", models.CharField(max_length=512)),
                ("external_id", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("unvalidated", "Unvalidated"), ("valid", "Valid"), ("invalid", "Invalid")], default="unvalidated", max_length=32)),
                ("last_validated_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cloud_accounts", to="core.organization")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cloud_accounts", to="core.project")),
            ],
        ),
        migrations.AddConstraint(
            model_name="cloudaccount",
            constraint=models.UniqueConstraint(fields=("provider", "provider_account_id"), name="uniq_provider_account_id"),
        ),
    ]

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0009_recommendations"),
    ]

    operations = [
        migrations.CreateModel(
            name="RemediationAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action_key", models.CharField(db_index=True, max_length=100)),
                ("status", models.CharField(choices=[("requested", "Requested"), ("previewed", "Previewed"), ("approved", "Approved"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("stale", "Stale"), ("rejected", "Rejected")], db_index=True, default="requested", max_length=16)),
                ("simulation", models.BooleanField(default=True)),
                ("parameters", models.JSONField(default=dict)),
                ("preview", models.JSONField(blank=True, default=dict)),
                ("evidence_fingerprint", models.CharField(blank=True, max_length=64)),
                ("provider_result", models.JSONField(blank=True, default=dict)),
                ("error", models.CharField(blank=True, max_length=255)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("executed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_remediations", to=settings.AUTH_USER_MODEL)),
                ("cloud_account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="remediation_actions", to="core.cloudaccount")),
                ("executed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="executed_remediations", to=settings.AUTH_USER_MODEL)),
                ("recommendation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="remediation_actions", to="core.recommendation")),
                ("requested_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="requested_remediations", to=settings.AUTH_USER_MODEL)),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="remediation_actions", to="core.cloudresource")),
            ],
            options={"ordering": ["-requested_at", "id"]},
        ),
        migrations.CreateModel(
            name="RemediationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(db_index=True, max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("action", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="core.remediationaction")),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
    ]

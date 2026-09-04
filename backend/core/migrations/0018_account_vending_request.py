import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_enterprise_identity_config"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountVendingRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account_name", models.CharField(max_length=200)),
                ("account_email", models.EmailField(max_length=254)),
                ("environment", models.CharField(choices=[("development", "Development"), ("test", "Test"), ("staging", "Staging"), ("production", "Production"), ("sandbox", "Sandbox"), ("other", "Other")], max_length=32)),
                ("purpose", models.TextField(blank=True)),
                ("baseline_profile", models.CharField(default="standard", max_length=64)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("pending_approval", "Pending approval"), ("approved", "Approved"), ("rejected", "Rejected")], default="draft", max_length=32)),
                ("rejection_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_account_vending_requests", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="account_vending_requests", to="core.organization")),
                ("organization_node", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="account_vending_requests", to="core.organizationnode")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="account_vending_requests", to="core.project")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="account_vending_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="accountvendingrequest",
            constraint=models.UniqueConstraint(fields=("organization", "account_email"), name="uniq_vending_org_account_email"),
        ),
    ]

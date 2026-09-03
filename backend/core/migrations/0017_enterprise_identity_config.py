from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_notification_receipt"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnterpriseIdentityConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=False)),
                ("provider", models.CharField(choices=[("oidc", "OpenID Connect"), ("saml", "SAML 2.0")], default="oidc", max_length=16)),
                ("email_domain", models.CharField(blank=True, db_index=True, max_length=255)),
                ("issuer_url", models.URLField(blank=True, max_length=512)),
                ("client_id", models.CharField(blank=True, max_length=255)),
                ("metadata_url", models.URLField(blank=True, max_length=512)),
                ("entity_id", models.CharField(blank=True, max_length=512)),
                ("secret_reference", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="enterprise_identity", to="core.organization")),
            ],
        ),
        migrations.AddConstraint(
            model_name="enterpriseidentityconfig",
            constraint=models.UniqueConstraint(condition=~models.Q(email_domain=""), fields=("email_domain",), name="uniq_enterprise_identity_email_domain"),
        ),
    ]

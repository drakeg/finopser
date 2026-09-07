import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0018_account_vending_request"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("token_prefix", models.CharField(max_length=24, unique=True)),
                ("token_digest", models.CharField(max_length=64, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_api_credentials",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_credentials",
                        to="core.organization",
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="apicredential",
            constraint=models.UniqueConstraint(
                fields=("organization", "name"),
                name="uniq_api_credential_org_name",
            ),
        ),
    ]

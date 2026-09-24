import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0026_integrationdelivery_channel_and_unique_event"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnterpriseIdentityFlow",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("state_digest", models.CharField(max_length=64, unique=True)),
                ("nonce", models.CharField(max_length=128)),
                ("pkce_verifier", models.CharField(max_length=128)),
                ("redirect_uri", models.URLField(max_length=1024)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "identity_config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="authentication_flows",
                        to="core.enterpriseidentityconfig",
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]

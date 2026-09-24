import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0027_enterprise_identity_flow"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EnterpriseIdentityLink",
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
                ("subject", models.CharField(max_length=255)),
                ("email", models.EmailField(max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_authenticated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "identity_config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="identity_links",
                        to="core.enterpriseidentityconfig",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enterprise_identity_links",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="enterpriseidentitylink",
            constraint=models.UniqueConstraint(
                fields=("identity_config", "subject"),
                name="uniq_enterprise_identity_subject",
            ),
        ),
        migrations.AddConstraint(
            model_name="enterpriseidentitylink",
            constraint=models.UniqueConstraint(
                fields=("identity_config", "user"),
                name="uniq_enterprise_identity_user",
            ),
        ),
    ]

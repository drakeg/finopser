import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0014_billing_event")]

    operations = [
        migrations.CreateModel(
            name="Notification",
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
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("high", "High"),
                            ("critical", "Critical"),
                        ],
                        default="info",
                        max_length=16,
                    ),
                ),
                ("category", models.CharField(db_index=True, max_length=64)),
                ("title", models.CharField(max_length=255)),
                ("detail", models.TextField(blank=True)),
                ("target", models.CharField(blank=True, max_length=100)),
                ("object_type", models.CharField(blank=True, max_length=100)),
                ("object_id", models.CharField(blank=True, max_length=100)),
                ("dedupe_key", models.CharField(max_length=255)),
                ("is_read", models.BooleanField(db_index=True, default=False)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("first_seen", models.DateTimeField(auto_now_add=True)),
                ("last_seen", models.DateTimeField(auto_now=True)),
                ("occurrence_count", models.PositiveIntegerField(default=1)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="core.organization",
                    ),
                ),
            ],
            options={"ordering": ["-last_seen", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.UniqueConstraint(
                fields=("organization", "dedupe_key"),
                name="uniq_notification_org_dedupe",
            ),
        ),
    ]

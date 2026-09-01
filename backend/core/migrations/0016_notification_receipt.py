from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0015_notification"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="notification",
            name="is_read",
        ),
        migrations.RemoveField(
            model_name="notification",
            name="read_at",
        ),
        migrations.CreateModel(
            name="NotificationReceipt",
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
                ("read_at", models.DateTimeField()),
                (
                    "notification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="receipts",
                        to="core.notification",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_receipts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="notificationreceipt",
            constraint=models.UniqueConstraint(
                fields=("notification", "user"),
                name="uniq_notification_user_receipt",
            ),
        ),
    ]

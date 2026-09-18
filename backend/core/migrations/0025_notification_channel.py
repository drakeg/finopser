# Generated for Sprint 25 slice 1

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0024_integration_delivery"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="NotificationChannel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("event_types", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("disabled_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_notification_channels", to=settings.AUTH_USER_MODEL)),
                ("destination", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notification_channels", to="core.integrationdestination")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notification_channels", to="core.organization")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="notificationchannel",
            constraint=models.UniqueConstraint(fields=("organization", "name"), name="uniq_notification_channel_org_name"),
        ),
    ]

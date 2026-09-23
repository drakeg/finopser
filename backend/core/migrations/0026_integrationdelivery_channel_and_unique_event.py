# Generated manually for Sprint 27 notification hardening.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0025_notification_channel"),
    ]

    operations = [
        migrations.AddField(
            model_name="integrationdelivery",
            name="channel",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deliveries",
                to="core.notificationchannel",
            ),
        ),
        migrations.AddConstraint(
            model_name="integrationdelivery",
            constraint=models.UniqueConstraint(
                fields=("organization", "destination", "event_id"),
                name="uniq_integration_delivery_event",
            ),
        ),
    ]

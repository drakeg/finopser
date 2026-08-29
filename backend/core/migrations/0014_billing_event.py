from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("core", "0013_history_organization_ownership")]

    operations = [
        migrations.CreateModel(
            name="BillingEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=32)),
                ("event_id", models.CharField(max_length=255)),
                ("event_type", models.CharField(max_length=128)),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="billing_events",
                        to="core.organization",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="billingevent",
            constraint=models.UniqueConstraint(
                fields=("provider", "event_id"),
                name="uniq_billing_provider_event",
            ),
        ),
    ]

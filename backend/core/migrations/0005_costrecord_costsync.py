import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0004_inventory")]

    operations = [
        migrations.CreateModel(
            name="CostSync",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("status", models.CharField(choices=[("running", "Running"), ("success", "Success"), ("partial", "Partial"), ("failed", "Failed")], default="running", max_length=32)),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("record_count", models.PositiveIntegerField(default=0)),
                ("errors", models.JSONField(blank=True, default=list)),
                ("cloud_account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cost_syncs", to="core.cloudaccount")),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="CostRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=32)),
                ("provider_account_id", models.CharField(max_length=64)),
                ("usage_date", models.DateField(db_index=True)),
                ("service", models.CharField(db_index=True, max_length=255)),
                ("region", models.CharField(blank=True, db_index=True, max_length=64)),
                ("amount", models.DecimalField(decimal_places=8, max_digits=20)),
                ("currency", models.CharField(default="USD", max_length=16)),
                ("updated_at", models.DateTimeField()),
                ("cloud_account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cost_records", to="core.cloudaccount")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cost_records", to="core.project")),
            ],
            options={"ordering": ["usage_date", "service", "region"]},
        ),
        migrations.AddConstraint(
            model_name="costrecord",
            constraint=models.UniqueConstraint(fields=("cloud_account", "usage_date", "service", "region", "currency"), name="uniq_cost_record_dimension"),
        ),
    ]

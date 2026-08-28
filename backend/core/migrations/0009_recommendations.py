import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0008_budget_governance"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendationRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("generated_count", models.PositiveIntegerField(default=0)),
                ("resolved_count", models.PositiveIntegerField(default=0)),
                ("open_count", models.PositiveIntegerField(default=0)),
                ("dismissed_count", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="Recommendation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_key", models.CharField(max_length=255, unique=True)),
                ("source_type", models.CharField(db_index=True, max_length=64)),
                ("category", models.CharField(choices=[("cost", "Cost"), ("governance", "Governance"), ("operations", "Operations")], db_index=True, max_length=32)),
                ("priority", models.CharField(choices=[("critical", "Critical"), ("high", "High"), ("medium", "Medium"), ("low", "Low")], db_index=True, max_length=16)),
                ("status", models.CharField(choices=[("open", "Open"), ("dismissed", "Dismissed"), ("resolved", "Resolved")], db_index=True, default="open", max_length=16)),
                ("title", models.CharField(max_length=255)),
                ("detail", models.TextField()),
                ("action", models.TextField()),
                ("estimated_monthly_savings", models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ("evidence", models.JSONField(blank=True, default=dict)),
                ("first_seen", models.DateTimeField()),
                ("last_seen", models.DateTimeField()),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("dismissed_at", models.DateTimeField(blank=True, null=True)),
                ("cloud_account", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="recommendations", to="core.cloudaccount")),
                ("dismissed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dismissed_recommendations", to=settings.AUTH_USER_MODEL)),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recommendations", to="core.project")),
                ("resource", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recommendations", to="core.cloudresource")),
            ],
            options={"ordering": ["status", "priority", "title"]},
        ),
    ]

from django.conf import settings
from django.db import migrations, models
from django.db.models import deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0030_accountprovisioningexecution"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("report_code", models.CharField(max_length=80)),
                ("cadence", models.CharField(choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")], max_length=16)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("disabled_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(on_delete=deletion.PROTECT, related_name="created_report_schedules", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=deletion.CASCADE, related_name="report_schedules", to="core.organization")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="reportschedule",
            constraint=models.UniqueConstraint(fields=("organization", "name"), name="uniq_report_schedule_org_name"),
        ),
        migrations.CreateModel(
            name="ReportGeneration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("report_code", models.CharField(max_length=80)),
                ("status", models.CharField(choices=[("succeeded", "Succeeded"), ("failed", "Failed")], max_length=16)),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("truncated", models.BooleanField(default=False)),
                ("generated_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=deletion.CASCADE, related_name="report_generations", to="core.organization")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=deletion.SET_NULL, related_name="requested_report_generations", to=settings.AUTH_USER_MODEL)),
                ("schedule", models.ForeignKey(blank=True, null=True, on_delete=deletion.SET_NULL, related_name="generations", to="core.reportschedule")),
            ],
            options={"ordering": ["-generated_at", "-id"]},
        ),
    ]

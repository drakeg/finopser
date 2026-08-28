import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0007_governance_policy"),
    ]

    operations = [
        migrations.CreateModel(
            name="Budget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=20)),
                ("currency", models.CharField(default="USD", max_length=16)),
                ("warning_threshold", models.DecimalField(decimal_places=2, default=80, max_digits=5)),
                ("critical_threshold", models.DecimalField(decimal_places=2, default=90, max_digits=5)),
                ("enabled", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cloud_account", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="budgets", to="core.cloudaccount")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_budgets", to=settings.AUTH_USER_MODEL)),
                ("node", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="budgets", to="core.organizationnode")),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="budgets", to="core.organization")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="budgets", to="core.project")),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="BudgetAlert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.DateField(db_index=True)),
                ("level", models.CharField(choices=[("warning", "Warning"), ("critical", "Critical"), ("exceeded", "Exceeded")], max_length=16)),
                ("status", models.CharField(choices=[("open", "Open"), ("resolved", "Resolved")], db_index=True, default="open", max_length=16)),
                ("actual_amount", models.DecimalField(decimal_places=2, max_digits=20)),
                ("utilization", models.DecimalField(decimal_places=2, max_digits=8)),
                ("first_seen", models.DateTimeField()),
                ("last_seen", models.DateTimeField()),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("budget", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alerts", to="core.budget")),
            ],
            options={"ordering": ["status", "-period", "budget__name", "level"]},
        ),
        migrations.AddConstraint(
            model_name="budgetalert",
            constraint=models.UniqueConstraint(fields=("budget", "period", "level"), name="uniq_budget_alert_period_level"),
        ),
    ]

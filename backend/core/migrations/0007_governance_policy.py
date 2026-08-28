import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_policies(apps, schema_editor):
    policy_model = apps.get_model("core", "GovernancePolicy")
    policies = [
        ("GUARD-EC2-PUBLIC-IP", "Restrict public EC2 IPv4 exposure", "Reports active EC2 instances with a persisted public IPv4 address.", "high", "observe", "aws.ec2.instance", "ec2_public_ipv4"),
        ("GUARD-RDS-PUBLIC", "Restrict public RDS accessibility", "Reports RDS instances whose persisted PubliclyAccessible value is true.", "high", "observe", "aws.rds.db_instance", "rds_public_access"),
        ("GUARD-RDS-ENCRYPTION", "Require RDS storage encryption", "Reports RDS instances whose persisted StorageEncrypted value is false.", "high", "recommend", "aws.rds.db_instance", "rds_storage_encryption"),
    ]
    policy_model.objects.bulk_create([
        policy_model(code=code, name=name, description=description, severity=severity, mode=mode, enabled=True, resource_type=resource_type, rule_key=rule_key)
        for code, name, description, severity, mode, resource_type, rule_key in policies
    ])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0006_compliance"),
    ]

    operations = [
        migrations.CreateModel(
            name="PolicyRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("passed_count", models.PositiveIntegerField(default=0)),
                ("violated_count", models.PositiveIntegerField(default=0)),
                ("unknown_count", models.PositiveIntegerField(default=0)),
                ("resolved_count", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="GovernancePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("severity", models.CharField(choices=[("critical", "Critical"), ("high", "High"), ("medium", "Medium"), ("low", "Low")], max_length=16)),
                ("mode", models.CharField(choices=[("observe", "Observe"), ("recommend", "Recommend")], default="observe", max_length=16)),
                ("enabled", models.BooleanField(db_index=True, default=True)),
                ("resource_type", models.CharField(db_index=True, max_length=128)),
                ("rule_key", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cloud_account", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="governance_policies", to="core.cloudaccount")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_governance_policies", to=settings.AUTH_USER_MODEL)),
                ("node", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="governance_policies", to="core.organizationnode")),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="governance_policies", to="core.organization")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="governance_policies", to="core.project")),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="PolicyViolation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("severity", models.CharField(choices=[("critical", "Critical"), ("high", "High"), ("medium", "Medium"), ("low", "Low")], max_length=16)),
                ("status", models.CharField(choices=[("open", "Open"), ("resolved", "Resolved")], db_index=True, default="open", max_length=16)),
                ("evidence", models.JSONField(blank=True, default=dict)),
                ("first_seen", models.DateTimeField()),
                ("last_seen", models.DateTimeField()),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("cloud_account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="policy_violations", to="core.cloudaccount")),
                ("policy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="violations", to="core.governancepolicy")),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="policy_violations", to="core.cloudresource")),
            ],
            options={"ordering": ["status", "severity", "policy__code", "resource__name"]},
        ),
        migrations.AddConstraint(
            model_name="policyviolation",
            constraint=models.UniqueConstraint(fields=("policy", "resource"), name="uniq_policy_violation_resource"),
        ),
        migrations.RunPython(seed_policies, migrations.RunPython.noop),
    ]

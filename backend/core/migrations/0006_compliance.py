import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_baseline_controls(apps, schema_editor):
    framework_model = apps.get_model("core", "ComplianceFramework")
    control_model = apps.get_model("core", "ComplianceControl")
    framework = framework_model.objects.create(
        code="FINOPSER-AWS-BASELINE",
        name="Finopser AWS Baseline",
        version="1.0",
        description="Initial evidence-backed AWS compliance baseline.",
        enabled=True,
    )
    controls = [
        (
            "AWS-EC2-001",
            "EC2 instances should not have a public IPv4 address",
            "Flags active EC2 instances with a persisted public IPv4 address.",
            "high",
            "aws.ec2.instance",
            "ec2_public_ipv4",
        ),
        (
            "AWS-RDS-001",
            "RDS instances should not be publicly accessible",
            "Flags RDS instances whose persisted PubliclyAccessible value is true.",
            "high",
            "aws.rds.db_instance",
            "rds_public_access",
        ),
        (
            "AWS-RDS-002",
            "RDS storage should be encrypted",
            "Flags RDS instances whose persisted StorageEncrypted value is false.",
            "high",
            "aws.rds.db_instance",
            "rds_storage_encryption",
        ),
    ]
    control_model.objects.bulk_create(
        [
            control_model(
                framework=framework,
                code=code,
                title=title,
                description=description,
                severity=severity,
                resource_type=resource_type,
                check_key=check_key,
            )
            for code, title, description, severity, resource_type, check_key in controls
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0005_costrecord_costsync"),
    ]

    operations = [
        migrations.CreateModel(
            name="ComplianceFramework",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("version", models.CharField(blank=True, max_length=64)),
                ("description", models.TextField(blank=True)),
                ("enabled", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="ComplianceRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("passed_count", models.PositiveIntegerField(default=0)),
                ("failed_count", models.PositiveIntegerField(default=0)),
                ("unknown_count", models.PositiveIntegerField(default=0)),
                ("resolved_count", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="ComplianceControl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("severity", models.CharField(choices=[("critical", "Critical"), ("high", "High"), ("medium", "Medium"), ("low", "Low")], max_length=16)),
                ("resource_type", models.CharField(db_index=True, max_length=128)),
                ("check_key", models.CharField(max_length=100)),
                ("framework", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="controls", to="core.complianceframework")),
            ],
            options={"ordering": ["framework__code", "code"]},
        ),
        migrations.CreateModel(
            name="ComplianceFinding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("severity", models.CharField(choices=[("critical", "Critical"), ("high", "High"), ("medium", "Medium"), ("low", "Low")], max_length=16)),
                ("status", models.CharField(choices=[("open", "Open"), ("resolved", "Resolved"), ("excepted", "Excepted")], db_index=True, default="open", max_length=16)),
                ("evidence", models.JSONField(blank=True, default=dict)),
                ("first_seen", models.DateTimeField()),
                ("last_seen", models.DateTimeField()),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("cloud_account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="compliance_findings", to="core.cloudaccount")),
                ("control", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="findings", to="core.compliancecontrol")),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="compliance_findings", to="core.cloudresource")),
            ],
            options={"ordering": ["status", "severity", "control__code", "resource__name"]},
        ),
        migrations.CreateModel(
            name="ComplianceException",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.TextField()),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cloud_account", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="compliance_exceptions", to="core.cloudaccount")),
                ("control", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="exceptions", to="core.compliancecontrol")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("resource", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="compliance_exceptions", to="core.cloudresource")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="compliancecontrol",
            constraint=models.UniqueConstraint(fields=("framework", "code"), name="uniq_compliance_control_code"),
        ),
        migrations.AddConstraint(
            model_name="compliancefinding",
            constraint=models.UniqueConstraint(fields=("control", "resource"), name="uniq_compliance_finding_control_resource"),
        ),
        migrations.RunPython(seed_baseline_controls, migrations.RunPython.noop),
    ]

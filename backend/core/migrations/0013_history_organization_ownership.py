from django.db import migrations, models
import django.db.models.deletion


def backfill_history_organizations(apps, schema_editor):
    AuditEvent = apps.get_model("core", "AuditEvent")
    ComplianceRun = apps.get_model("core", "ComplianceRun")
    PolicyRun = apps.get_model("core", "PolicyRun")

    for event in AuditEvent.objects.all().iterator():
        organization_id = (event.metadata or {}).get("organization_id")
        if organization_id:
            event.organization_id = organization_id
            event.save(update_fields=["organization"])

    for run_model, action, object_type in (
        (ComplianceRun, "compliance.evaluate", "ComplianceRun"),
        (PolicyRun, "policy.evaluate", "PolicyRun"),
    ):
        for run in run_model.objects.all().iterator():
            event = AuditEvent.objects.filter(
                action=action,
                object_type=object_type,
                object_id=str(run.pk),
            ).order_by("-created_at").first()
            organization_id = None
            if event is not None:
                organization_id = event.organization_id or (event.metadata or {}).get(
                    "organization_id"
                )
            if organization_id:
                run.organization_id = organization_id
                run.save(update_fields=["organization"])


class Migration(migrations.Migration):
    dependencies = [("core", "0012_recommendation_tenant_scope")]

    operations = [
        migrations.AddField(
            model_name="auditevent",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="audit_events",
                to="core.organization",
            ),
        ),
        migrations.AddField(
            model_name="compliancerun",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="compliance_runs",
                to="core.organization",
            ),
        ),
        migrations.AddField(
            model_name="policyrun",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="policy_runs",
                to="core.organization",
            ),
        ),
        migrations.RunPython(backfill_history_organizations, migrations.RunPython.noop),
    ]

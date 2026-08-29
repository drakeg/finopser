from django.db import migrations, models
import django.db.models.deletion


def backfill_recommendation_organizations(apps, schema_editor):
    Recommendation = apps.get_model("core", "Recommendation")
    RecommendationRun = apps.get_model("core", "RecommendationRun")
    AuditEvent = apps.get_model("core", "AuditEvent")

    for recommendation in Recommendation.objects.select_related(
        "cloud_account", "project", "resource__cloud_account"
    ).all():
        organization_id = None
        if recommendation.cloud_account_id:
            organization_id = recommendation.cloud_account.organization_id
        elif recommendation.project_id:
            organization_id = recommendation.project.organization_id
        elif recommendation.resource_id:
            organization_id = recommendation.resource.cloud_account.organization_id
        if organization_id:
            recommendation.organization_id = organization_id
            recommendation.save(update_fields=["organization"])

    for run in RecommendationRun.objects.all():
        event = AuditEvent.objects.filter(
            action="recommendation.generate",
            object_type="RecommendationRun",
            object_id=str(run.id),
        ).order_by("-created_at").first()
        organization_id = (event.metadata or {}).get("organization_id") if event else None
        if organization_id:
            run.organization_id = organization_id
            run.save(update_fields=["organization"])


class Migration(migrations.Migration):
    dependencies = [("core", "0011_accounts_subscriptions_onboarding")]

    operations = [
        migrations.AddField(
            model_name="recommendation",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="recommendations",
                to="core.organization",
            ),
        ),
        migrations.AddField(
            model_name="recommendationrun",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="recommendation_runs",
                to="core.organization",
            ),
        ),
        migrations.AlterField(
            model_name="recommendation",
            name="source_key",
            field=models.CharField(max_length=255),
        ),
        migrations.RunPython(backfill_recommendation_organizations, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="recommendation",
            constraint=models.UniqueConstraint(
                fields=("organization", "source_key"),
                name="unique_recommendation_source_per_org",
            ),
        ),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0010_remediation_actions"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("owner", "Owner"), ("admin", "Administrator"), ("member", "Member"), ("viewer", "Viewer")], default="member", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="core.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_memberships", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("plan", models.CharField(choices=[("free", "Free"), ("pro", "Pro"), ("business", "Business")], default="free", max_length=16)),
                ("status", models.CharField(choices=[("free", "Free"), ("trialing", "Trialing"), ("active", "Active"), ("past_due", "Past due"), ("canceled", "Canceled")], default="free", max_length=16)),
                ("billing_provider", models.CharField(blank=True, max_length=32)),
                ("provider_customer_id", models.CharField(blank=True, max_length=255)),
                ("provider_subscription_id", models.CharField(blank=True, max_length=255)),
                ("current_period_end", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="subscription", to="core.organization")),
            ],
        ),
        migrations.CreateModel(
            name="OnboardingProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("current_step", models.CharField(choices=[("organization", "Create organization"), ("cloud_account", "Connect cloud account"), ("validate", "Validate connection"), ("sync", "Initial sync"), ("complete", "Complete")], default="organization", max_length=32)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="onboarding_profiles", to="core.organization")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="onboarding_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(fields=("user", "organization"), name="uniq_user_organization_membership"),
        ),
    ]

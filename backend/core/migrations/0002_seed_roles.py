from django.db import migrations

ROLE_NAMES = [
    "Platform Administrator",
    "Cloud Administrator",
    "FinOps Analyst",
    "Security / Compliance Engineer",
    "Project Owner",
    "Auditor",
]


def seed_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLE_NAMES:
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length"), ("core", "0001_initial")]
    operations = [migrations.RunPython(seed_roles, migrations.RunPython.noop)]

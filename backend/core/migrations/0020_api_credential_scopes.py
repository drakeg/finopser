from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0019_api_credential")]

    operations = [
        migrations.AddField(
            model_name="apicredential",
            name="scopes",
            field=models.JSONField(default=["accounts:read"]),
            preserve_default=False,
        ),
    ]

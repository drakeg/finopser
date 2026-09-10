from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0020_api_credential_scopes")]

    operations = [
        migrations.AddField(
            model_name="apicredential",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

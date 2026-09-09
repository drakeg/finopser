from django.db import migrations, models

import core.integration_models


class Migration(migrations.Migration):
    dependencies = [("core", "0019_api_credential")]

    operations = [
        migrations.AddField(
            model_name="apicredential",
            name="scopes",
            field=models.JSONField(default=core.integration_models.default_api_credential_scopes),
        ),
    ]

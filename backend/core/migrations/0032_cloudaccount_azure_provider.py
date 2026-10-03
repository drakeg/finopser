from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0031_reportschedule_reportgeneration")]

    operations = [
        migrations.AlterField(
            model_name="cloudaccount",
            name="provider",
            field=models.CharField(choices=[("aws", "Amazon Web Services"), ("azure", "Microsoft Azure")], default="aws", max_length=32),
        ),
    ]

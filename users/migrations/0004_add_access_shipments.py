from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_add_access_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="access_shipments",
            field=models.BooleanField(
                default=False,
                help_text="Can access Shipments section",
            ),
        ),
    ]

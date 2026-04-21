from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_add_access_shipments"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="access_shipments_logistics",
            field=models.BooleanField(
                default=False,
                help_text="Logistics: can add/edit shipments and see unit costs",
            ),
        ),
    ]

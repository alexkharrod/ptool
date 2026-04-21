from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scouting", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="prospect",
            name="prospect_number",
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
    ]

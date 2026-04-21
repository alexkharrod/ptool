from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0026_product_website_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="htscode",
            name="rates_verified_date",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Date rates were last verified against official sources. Leave blank or update when you confirm rates are current.",
            ),
        ),
    ]

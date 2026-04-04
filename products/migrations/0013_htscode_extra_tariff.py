from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0012_htscode_product_hts_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="htscode",
            name="extra_tariff_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Extra/RT tariff rate (additional tariff beyond duty and Section 301)",
                max_digits=6,
            ),
        ),
    ]

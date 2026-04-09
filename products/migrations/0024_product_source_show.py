from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0023_make_product_fields_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="source_show",
            field=models.CharField(
                blank=True,
                max_length=150,
                help_text="Trade show this product was scouted at (set automatically on promotion).",
            ),
        ),
    ]

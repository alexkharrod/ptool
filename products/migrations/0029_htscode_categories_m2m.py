from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0028_add_pad_print"),
    ]

    operations = [
        # Remove the old hardcoded category_hint CharField
        migrations.RemoveField(
            model_name="htscode",
            name="category_hint",
        ),
        # Add M2M to the real Category model
        migrations.AddField(
            model_name="htscode",
            name="categories",
            field=models.ManyToManyField(
                blank=True,
                help_text="Product categories this HTS code applies to (used for auto-suggest on product forms).",
                related_name="hts_codes",
                to="products.category",
            ),
        ),
    ]

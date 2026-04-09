from django.db import migrations, models


SEED_VALUES = {
    "AC": 30,
    "AT": 20,
    "CB": 100,
    "CM": 21,
    "CT": 20,
    "DF": 25,
    "DW": 26,
    "EB": 61,
    "FN": 20,
    "FT": 10,
    "HW": 5,
    "JB": 85,
    "KT": 20,
    "LY": 1901,
    "MA": 20,
    "MG": 11,
    "NFC": 61,
    "OA": 20,
    "PK": 10,
    "RT": 46,
    "SC": 25,
    "SL": 20,
    "SP": 96,
    "ST": 20,
    "TA": 21,
    "TL": 17,
    "TT": 20,
    "UD": 135,
    "UH": 50,
    "WB": 15,
    "WC": 62,
}


def set_seeds(apps, schema_editor):
    Category = apps.get_model("products", "Category")
    for code, seed in SEED_VALUES.items():
        Category.objects.filter(code=code).update(sku_seed=seed)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0021_add_quote_only_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="sku_seed",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Starting number for auto-generated SKUs in this category",
            ),
        ),
        migrations.RunPython(set_seeds, migrations.RunPython.noop),
    ]

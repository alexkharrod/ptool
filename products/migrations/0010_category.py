from django.db import migrations, models


INITIAL_CATEGORIES = [
    "AC", "AT", "CB", "CM", "DW", "EB", "FN", "HW", "JB", "LY",
    "MA", "MG", "MISC", "NFC", "RT", "SC", "SL", "SP", "TA", "TL",
    "TT", "UC", "UD", "UH", "UNCATEGORIZED", "WC",
]


def load_categories(apps, schema_editor):
    Category = apps.get_model("products", "Category")
    for code in INITIAL_CATEGORIES:
        Category.objects.get_or_create(code=code)


def remove_categories(apps, schema_editor):
    Category = apps.get_model("products", "Category")
    Category.objects.filter(code__in=INITIAL_CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0009_merge_product_status_and_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
            ],
            options={
                "verbose_name_plural": "categories",
                "ordering": ["code"],
            },
        ),
        migrations.RunPython(load_categories, remove_categories),
    ]

from django.db import migrations


def add_pad_print(apps, schema_editor):
    ImprintMethod = apps.get_model("products", "ImprintMethod")
    ImprintMethod.objects.get_or_create(
        name="Pad Print (1 color Max)",
        defaults={
            "setup_fee": "50.00",
            "run_charge": "0.00",
            "sort_order": 50,
        },
    )


def remove_pad_print(apps, schema_editor):
    ImprintMethod = apps.get_model("products", "ImprintMethod")
    ImprintMethod.objects.filter(name="Pad Print (1 color Max)").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0027_htscode_rates_verified_date"),
    ]

    operations = [
        migrations.RunPython(add_pad_print, remove_pad_print),
    ]

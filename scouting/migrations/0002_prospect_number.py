from django.db import migrations, models


def backfill_prospect_numbers(apps, schema_editor):
    Prospect = apps.get_model("scouting", "Prospect")
    prospects = Prospect.objects.filter(prospect_number="").order_by("date_added", "pk")
    for i, prospect in enumerate(prospects, start=1):
        prospect.prospect_number = f"PRO-{i:04d}"
        prospect.save(update_fields=["prospect_number"])


class Migration(migrations.Migration):

    dependencies = [
        ("scouting", "0001_initial"),
    ]

    operations = [
        # Step 1: add column with no unique constraint, blank allowed
        migrations.AddField(
            model_name="prospect",
            name="prospect_number",
            field=models.CharField(blank=True, max_length=20, default=""),
            preserve_default=False,
        ),
        # Step 2: fill in PRO-NNNN for every existing row
        migrations.RunPython(backfill_prospect_numbers, migrations.RunPython.noop),
        # Step 3: now that all rows are distinct, add the unique constraint
        migrations.AlterField(
            model_name="prospect",
            name="prospect_number",
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
    ]

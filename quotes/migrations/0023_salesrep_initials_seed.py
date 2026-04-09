from django.db import migrations, models


REPS = [
    ("Alex Harrod",    "AH"),
    ("Kenny Avera",    "KA"),
    ("Peter Marks",    "PM"),
    ("Jake Wilson",    "JW"),
    ("Joey Guerrero",  "JG"),
    ("Sari Waters",    "SW"),
]


def seed_reps(apps, schema_editor):
    SalesRep = apps.get_model("quotes", "SalesRep")
    for full_name, initials in REPS:
        rep = SalesRep.objects.filter(name__iexact=full_name).first()
        if rep:
            rep.initials = initials
            rep.save()
        else:
            if not SalesRep.objects.filter(initials=initials).exists():
                SalesRep.objects.create(name=full_name, initials=initials)


def reverse_seed(apps, schema_editor):
    pass  # leave data in place on rollback


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0022_quote_improvements"),
    ]

    operations = [
        # Add as nullable so existing rows get NULL (not ""), which is safe
        # to have multiple of in a unique index.
        migrations.AddField(
            model_name="salesrep",
            name="initials",
            field=models.CharField(blank=True, null=True, max_length=5, default=None),
            preserve_default=False,
        ),
        # Seed the 6 known reps
        migrations.RunPython(seed_reps, reverse_seed),
        # Now make unique — NULL values are fine; only non-null values must be unique
        migrations.AlterField(
            model_name="salesrep",
            name="initials",
            field=models.CharField(blank=True, null=True, max_length=5, unique=True),
        ),
    ]

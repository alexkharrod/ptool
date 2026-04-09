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
        # Update by name if exists, otherwise create
        rep = SalesRep.objects.filter(name__iexact=full_name).first()
        if rep:
            rep.initials = initials
            rep.save()
        else:
            # Also check by initials to avoid unique collision
            if not SalesRep.objects.filter(initials=initials).exists():
                SalesRep.objects.create(name=full_name, initials=initials)


def reverse_seed(apps, schema_editor):
    pass  # leave data in place on rollback


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0022_quote_improvements"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesrep",
            name="initials",
            field=models.CharField(blank=True, max_length=5, default=""),
            preserve_default=False,
        ),
        # Make initials unique after seeding (can't be unique on AddField with existing rows)
        migrations.RunPython(seed_reps, reverse_seed),
        migrations.AlterField(
            model_name="salesrep",
            name="initials",
            field=models.CharField(blank=True, max_length=5, unique=True),
        ),
    ]

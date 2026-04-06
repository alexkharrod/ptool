"""
Seed the standard ImprintMethod records.

Usage:
    python manage.py seed_imprint_methods
    python manage.py seed_imprint_methods --reset   # delete all and re-seed
"""
from django.core.management.base import BaseCommand

from products.models import ImprintMethod

STANDARD_METHODS = [
    # (name, setup_fee, run_charge, sort_order)
    # setup_fee=None → "assign individually" (Mold Fee)
    ("Spot Color",        35.00,  0.35, 10),
    ("Full Color",        50.00,  0.50, 20),
    ("Step and Repeat",   35.00,  0.35, 30),
    ("Sublimation",       35.00,  0.00, 40),
    ("Mold Fee",          None,   0.00, 50),   # fee assigned per product
]


class Command(BaseCommand):
    help = "Seed standard ImprintMethod records (idempotent — skips existing names)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing ImprintMethod records before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = ImprintMethod.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"  Deleted {deleted} existing method(s)."))

        created = skipped = 0
        for name, setup_fee, run_charge, sort_order in STANDARD_METHODS:
            obj, was_created = ImprintMethod.objects.get_or_create(
                name=name,
                defaults={
                    "setup_fee": setup_fee,
                    "run_charge": run_charge,
                    "sort_order": sort_order,
                },
            )
            if was_created:
                fee_str = f"${setup_fee:.2f}" if setup_fee is not None else "variable"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  CREATED  {name:20s}  setup={fee_str:8s}  run=${run_charge:.2f}"
                    )
                )
                created += 1
            else:
                self.stdout.write(f"  EXISTS   {name}")
                skipped += 1

        self.stdout.write(f"\nDone. Created={created}  Skipped={skipped}")

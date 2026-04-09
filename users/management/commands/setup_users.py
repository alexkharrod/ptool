"""
One-time management command to create initial users and set their access flags.

Usage:
    python manage.py setup_users

This will:
  - Create Tracey Tuggle  (tracey.tuggle@logoincluded.com) — Products
  - Create Peter Marks    (pmarks@logoincluded.com)        — Products + Quotes
  - Update Cindy's access flags                            — Products + Scouting
    (Cindy is found by searching for any non-staff user that is not Tracey or Peter)

All new users are created with must_change_password=True so they'll be
prompted to set their own password on first login.

You supply a temporary password as a command-line argument:
    python manage.py setup_users --password "TemporaryPass123!"

Run this once after deploying the access-flags migration.
"""

from django.core.management.base import BaseCommand, CommandError

from users.models import CustomUser


class Command(BaseCommand):
    help = "Create Tracey and Peter, and update Cindy's access flags."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            required=True,
            help="Temporary password for new accounts (they must change it on first login)",
        )
        parser.add_argument(
            "--cindy-email",
            default=None,
            help="Cindy's email address (auto-detected if omitted — uses any existing non-staff user that isn't Tracey/Peter)",
        )

    def handle(self, *args, **options):
        password = options["password"]
        cindy_email = options.get("cindy_email")

        new_users = [
            {
                "email": "tracey.tuggle@logoincluded.com",
                "first_name": "Tracey",
                "last_name": "Tuggle",
                "access_products": True,
                "access_quotes":   False,
                "access_scouting": False,
            },
            {
                "email": "pmarks@logoincluded.com",
                "first_name": "Peter",
                "last_name": "Marks",
                "access_products": True,
                "access_quotes":   True,
                "access_scouting": False,
            },
        ]

        # ── Create Tracey and Peter ──────────────────────────────────────────
        for spec in new_users:
            email = spec["email"]
            if CustomUser.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f"  Skipping {email} — already exists."))
            else:
                user = CustomUser.objects.create_user(
                    email=email,
                    password=password,
                    first_name=spec["first_name"],
                    last_name=spec["last_name"],
                    access_products=spec["access_products"],
                    access_quotes=spec["access_quotes"],
                    access_scouting=spec["access_scouting"],
                    must_change_password=True,
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  Created {user.get_full_name()} ({email})"
                ))

        # ── Update Cindy's access flags ──────────────────────────────────────
        skip_emails = {u["email"] for u in new_users}

        if cindy_email:
            try:
                cindy = CustomUser.objects.get(email=cindy_email)
            except CustomUser.DoesNotExist:
                raise CommandError(f"No user found with email: {cindy_email}")
        else:
            # Auto-detect: first non-staff user that isn't one of the new ones
            cindy_qs = CustomUser.objects.filter(is_staff=False).exclude(email__in=skip_emails)
            if not cindy_qs.exists():
                self.stdout.write(self.style.WARNING("  Could not auto-detect Cindy — no eligible user found."))
                return
            if cindy_qs.count() > 1:
                emails = ", ".join(cindy_qs.values_list("email", flat=True))
                self.stdout.write(self.style.WARNING(
                    f"  Multiple non-staff users found ({emails}). "
                    f"Re-run with --cindy-email <email> to target a specific user."
                ))
                return
            cindy = cindy_qs.first()

        cindy.access_products = True
        cindy.access_scouting = True
        cindy.access_quotes   = False
        cindy.save(update_fields=["access_products", "access_scouting", "access_quotes"])
        self.stdout.write(self.style.SUCCESS(
            f"  Updated {cindy.get_full_name()} ({cindy.email}) → products + scouting"
        ))

        self.stdout.write(self.style.SUCCESS("\nDone! Run 'python manage.py migrate' if you haven't already."))

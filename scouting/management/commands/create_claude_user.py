"""
Creates a limited claude user with scouting-only permissions.
Run from the ptool project root:

    python manage.py create_claude_user --password yourpasswordhere

"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from scouting.models import Prospect

User = get_user_model()

CLAUDE_EMAIL = "claude@logoinluded.com"


class Command(BaseCommand):
    help = "Create a limited claude user with scouting add/view permissions only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help="Password for the claude user",
        )

    def handle(self, *args, **options):
        password = options["password"]

        if User.objects.filter(email=CLAUDE_EMAIL).exists():
            self.stdout.write(self.style.WARNING(f"{CLAUDE_EMAIL} already exists — updating password and permissions."))
            user = User.objects.get(email=CLAUDE_EMAIL)
            user.set_password(password)
        else:
            user = User(
                email=CLAUDE_EMAIL,
                first_name="Claude",
                last_name="AI",
                is_staff=False,
                is_superuser=False,
            )
            user.set_password(password)

        user.save()

        # Grant only: add prospect, view prospect
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Prospect)
        permissions = Permission.objects.filter(content_type=ct, codename__in=["add_prospect", "view_prospect", "delete_prospect"])
        user.user_permissions.set(permissions)
        user.save()

        granted = [p.codename for p in permissions]
        self.stdout.write(self.style.SUCCESS(
            f"✓ User {CLAUDE_EMAIL} ready. Permissions: {', '.join(granted)}"
        ))

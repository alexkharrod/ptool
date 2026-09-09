"""
Management command: audit_bluetooth

Lists every non-retail product whose website_description or website_keywords
contains the word "Bluetooth" (any capitalisation).

Optionally auto-fixes them by replacing every occurrence with "wireless".

Usage:
    python manage.py audit_bluetooth            # list violations only
    python manage.py audit_bluetooth --fix      # list AND auto-fix in-place
    python manage.py audit_bluetooth --fix --dry-run  # show what --fix would change
"""

import re

from django.core.management.base import BaseCommand

from products.models import Product

_BT_RE = re.compile(r'\bBluetooth\b', re.IGNORECASE)


def _has_bluetooth(text):
    return bool(text and _BT_RE.search(text))


def _fix(text):
    if not text:
        return text
    return _BT_RE.sub('wireless', text)


class Command(BaseCommand):
    help = "Audit (and optionally fix) non-retail products that say 'Bluetooth'"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true',
            help='Replace every "Bluetooth" occurrence with "wireless" and save',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='With --fix: show what would change without saving',
        )

    def handle(self, *args, **options):
        do_fix = options['fix']
        dry_run = options['dry_run']

        # Only non-retail products (retail may legitimately say Bluetooth)
        non_retail = Product.objects.exclude(sourcing='retail').exclude(sku__istartswith='RT')

        violations = [
            p for p in non_retail.only(
                'sku', 'name', 'sourcing', 'website_description', 'website_keywords'
            )
            if _has_bluetooth(p.website_description) or _has_bluetooth(p.website_keywords)
        ]

        if not violations:
            self.stdout.write(self.style.SUCCESS('No violations found — all clear!'))
            return

        self.stdout.write(self.style.WARNING(
            f'\nFound {len(violations)} non-retail product(s) containing "Bluetooth":\n'
        ))

        header = f"{'SKU':<12} {'Product Name':<45} {'In Desc':>7}  {'In KW':>5}"
        self.stdout.write(header)
        self.stdout.write('─' * len(header))

        for p in violations:
            in_desc = _has_bluetooth(p.website_description)
            in_kw   = _has_bluetooth(p.website_keywords)
            self.stdout.write(
                f"{p.sku:<12} {p.name[:45]:<45} {'YES' if in_desc else '':>7}  {'YES' if in_kw else '':>5}"
            )

        if do_fix:
            if dry_run:
                self.stdout.write(self.style.WARNING(
                    '\nDRY RUN — the following changes would be saved:\n'
                ))
                for p in violations:
                    if _has_bluetooth(p.website_description):
                        fixed = _fix(p.website_description)
                        self.stdout.write(f'  {p.sku} description: ...{p.website_description[:80]}...')
                        self.stdout.write(f'           → ...{fixed[:80]}...\n')
                    if _has_bluetooth(p.website_keywords):
                        self.stdout.write(f'  {p.sku} keywords: {p.website_keywords}')
                        self.stdout.write(f'          → {_fix(p.website_keywords)}\n')
            else:
                fixed_count = 0
                for p in violations:
                    updated = []
                    if _has_bluetooth(p.website_description):
                        p.website_description = _fix(p.website_description)
                        updated.append('description')
                    if _has_bluetooth(p.website_keywords):
                        p.website_keywords = _fix(p.website_keywords)
                        updated.append('keywords')
                    if updated:
                        p.save(update_fields=['website_description', 'website_keywords'])
                        self.stdout.write(self.style.SUCCESS(
                            f'  Fixed {p.sku} ({", ".join(updated)})'
                        ))
                        fixed_count += 1
                self.stdout.write(self.style.SUCCESS(f'\nFixed {fixed_count} product(s).'))
        else:
            self.stdout.write(self.style.WARNING(
                '\nRe-run with --fix to automatically replace "Bluetooth" → "wireless" in all of the above.'
            ))

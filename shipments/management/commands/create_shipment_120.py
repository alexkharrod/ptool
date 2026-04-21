"""
One-time management command: creates Shipment #120 with all 12 line items
parsed from the Bluefin packing list / commercial invoice (April 2026).

Run once:
    python manage.py create_shipment_120
    python manage.py create_shipment_120 --dry-run
"""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from shipments.models import Shipment, ShipmentItem


ITEMS = [
    # (po_number, sku, description, cartons, qty, nw_kg, gw_kg, dimensions_cm, cbm, unit_cost_usd)
    ("81300", "20-3008-1085", "AD Player", 20,  200,  Decimal("280.00"),  Decimal("318.00"),  "42×36×39.5",       Decimal("1.1945"), Decimal("46.00")),
    ("81301", "20-3018-1012", "AD Player", 10,   10,  Decimal("90.00"),   Decimal("100.00"),  "62×12.5×43",       Decimal("0.3333"), Decimal("79.00")),
    ("81382", "20-3018-1070", "AD Player",  1,    4,  Decimal("29.00"),   Decimal("30.30"),   "62.4×48.4×45",     Decimal("0.1359"), Decimal("79.00")),
    ("81382", "20-3018-1070", "AD Player",  1,    1,  Decimal("6.00"),    Decimal("7.20"),    "60.4×10.6×43.4",   Decimal("0.0278"), Decimal("79.00")),
    ("81472", "20-3018-0025", "AD Player",  6,    6,  Decimal("84.00"),   Decimal("99.00"),   "81×15×81",         Decimal("0.5905"), Decimal("80.00")),
    ("81304", "20-3018-1038", "AD Player", 13,   13,  Decimal("377.00"),  Decimal("408.20"),  "119.6×17.6×84.1",  Decimal("2.2986"), Decimal("158.00")),
    ("81304", "20-3018-0002", "AD Player", 48,   48,  Decimal("960.00"),  Decimal("1012.80"), "109.4×16.2×72.6",  Decimal("6.1760"), Decimal("158.00")),
    ("81304", "20-3018-1004", "AD Player", 78,   78,  Decimal("2925.00"), Decimal("3595.80"), "146.8×17.2×96.9",  Decimal("19.0842"), Decimal("228.00")),
    ("81304", "20-3018-0004", "AD Player", 42,   42,  Decimal("1344.00"), Decimal("1423.80"), "145.5×16.2×94",    Decimal("9.3058"), Decimal("228.00")),
    ("81453", "CB62",         "USB Data Cable with Connectors",  29, 5133, Decimal("391.50"), Decimal("420.50"), "40×30×30",        Decimal("1.0440"), Decimal("0.2100")),
    ("81456", "WC57",         "Wireless Mobile Phone Charger",   40, 2000, Decimal("156.00"), Decimal("196.00"), "50×23×13.5",      Decimal("0.6210"), Decimal("1.3000")),
    ("81099", "SP66",         "Speaker for Mobile Devices",      40, 2000, Decimal("320.00"), Decimal("360.00"), "34.5×34.5×21.5",  Decimal("1.0236"), Decimal("1.5000")),
]


class Command(BaseCommand):
    help = "Create Shipment #120 (Bluefin, Ocean, DANUBE 21E, Apr-May 2026) with 12 line items"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without saving anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if Shipment.objects.filter(shipment_number=120).exists():
            raise CommandError("Shipment #120 already exists. Aborting.")

        self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}Creating Shipment #120...")

        shipment_data = dict(
            shipment_number=120,
            mode=Shipment.MODE_OCEAN,
            carrier="ZIM",
            vessel="DANUBE 21E",
            tracking_number="ZIMUSHH32120468",
            etd="2026-04-22",
            eta_port="2026-05-05",
            port_of_loading="Shenzhen, China",
            status="In Transit",
            po_numbers="81300, 81301, 81382, 81472, 81304, 81453, 81456, 81099",
            total_cartons=328,
            total_pieces=9535,
            total_nw_kg=Decimal("6962.50"),
            total_gw_kg=Decimal("7971.60"),
            total_cbm=Decimal("41.8352"),
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("  Shipment header:"))
            for k, v in shipment_data.items():
                self.stdout.write(f"    {k}: {v}")
            self.stdout.write(self.style.WARNING(f"  Items: {len(ITEMS)} line items"))
            for i, item in enumerate(ITEMS, 1):
                self.stdout.write(f"    {i:2d}. PO {item[0]}  {item[1]:18s}  {item[4]:5d} pcs  ${item[9]}")
            self.stdout.write(self.style.SUCCESS("Dry run complete — nothing saved."))
            return

        shipment = Shipment.objects.create(**shipment_data)

        for (po, sku, desc, cartons, qty, nw, gw, dims, cbm, cost) in ITEMS:
            ShipmentItem.objects.create(
                shipment=shipment,
                po_number=po,
                sku=sku,
                description=desc,
                cartons=cartons,
                qty=qty,
                nw_kg=nw,
                gw_kg=gw,
                dimensions_cm=dims,
                cbm=cbm,
                unit_cost_usd=cost,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Shipment #{shipment.shipment_number} created (pk={shipment.pk}) "
                f"with {len(ITEMS)} line items."
            )
        )

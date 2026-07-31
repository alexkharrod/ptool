"""
One-time command to seed shipment #138 (ocean, AGS, Long Beach).

Source: "Shipment 138 PL.xlsx" — ocean packing list, 7 line items, no CI yet
so unit costs are left blank.

Usage:
    python manage.py create_shipment_138
    python manage.py create_shipment_138 --dry-run
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from shipments.models import Shipment, ShipmentItem

SHIPMENT = {
    "shipment_number": 138,
    "mode": "Ocean",
    "status": "In Transit",
    "carrier": "AGS",
    "port_of_loading": "Shenzhen, China",
    "port_of_arrival": "LB",
    "etd": "2026-07-30",
    "eta_port": "2026-08-18",
    "eta_warehouse": "2026-08-31",
    "po_numbers": "82154, 82138, 82156, 82166, 82066, 82096, 81956",
    "total_cartons": 179,
    "total_pieces": 3786,
    "total_nw_kg": Decimal("1849.60"),
    "total_gw_kg": Decimal("2061.70"),
    "total_cbm": Decimal("7.4900"),
    "notes": (
        "65 CTNS = 2 pallets (125*100*113 cm / 237*90*183 cm); "
        "114 CTNS = 2 pallets (165*105*146 cm x2). "
        "TA14 and SP96 for LI stock. Shipper: LogoIncluded, Inc."
    ),
}

ITEMS = [
    # po_number, sku, description, cartons, qty, nw_kg, gw_kg, cbm, dims
    ("82154", "20-3008-1264", "AD PLAYER",          10,   10, "30.00",   "42.00",   "0.4000", "42.4×30.6×31"),
    ("82138", "20-3018-1035", "AD PLAYER",          20,   20, "72.00",   "94.00",   "0.7500", "31.8×26.2×45"),
    ("82156", "20-3018-0026", "AD PLAYER",           1,    2, "12.00",   "13.10",   "0.0700", "54×23.5×54.7"),
    ("82166", "20-3018-0005", "AD PLAYER",          26,   26, "130.00",  "169.00",  "0.6500", "85.6×10.8×27"),
    ("82066", "20-3018-0067", "AD PLAYER",           8,    8, "240.00",  "264.00",  "2.3000", "236×21.8×55.8"),
    ("82096", "TA14",         "USB Charge Adapter", 18, 1800, "252.00",  "270.00",  "0.7100", "40.5×31.5×31"),
    ("81956", "SP96",         "Wireless Speaker",   96, 1920, "1113.60", "1209.60", "2.6100", "41×33.8×25.5"),
]


class Command(BaseCommand):
    help = "Seed shipment #138 (ocean / AGS / Long Beach) with its 7 packing list items"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Show what would be created without saving.")

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        num = SHIPMENT["shipment_number"]

        if Shipment.objects.filter(shipment_number=num).exists():
            self.stdout.write(self.style.WARNING(
                f"Shipment #{num} already exists — nothing to do."
            ))
            return

        if dry_run:
            self.stdout.write(f"DRY RUN — would create shipment #{num}:")
            for row in ITEMS:
                self.stdout.write(f"  {row[0]}  {row[1]:<14} {row[2]:<20} "
                                  f"{row[3]:>4} ctns  {row[4]:>5} pcs")
            self.stdout.write(
                f"  Totals: {SHIPMENT['total_cartons']} ctns, "
                f"{SHIPMENT['total_pieces']} pcs, "
                f"NW {SHIPMENT['total_nw_kg']}, GW {SHIPMENT['total_gw_kg']}, "
                f"CBM {SHIPMENT['total_cbm']}"
            )
            transaction.set_rollback(True)
            return

        shipment = Shipment.objects.create(**SHIPMENT)

        for po, sku, desc, ctns, qty, nw, gw, cbm, dims in ITEMS:
            ShipmentItem.objects.create(
                shipment=shipment,
                po_number=po,
                sku=sku,
                description=desc,
                cartons=ctns,
                qty=qty,
                nw_kg=Decimal(nw),
                gw_kg=Decimal(gw),
                cbm=Decimal(cbm),
                dimensions_cm=dims,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Created shipment #{num} with {len(ITEMS)} items "
            f"({SHIPMENT['total_cartons']} cartons, {SHIPMENT['total_pieces']} pcs)."
        ))

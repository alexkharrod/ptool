"""
One-time script to add Shenzhen Moldull prospects.
Run from the ptool project root:

    python add_moldull_prospects.py

"""
import os, sys, django

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from scouting.models import Prospect

items = [
    dict(
        show_name="Shenzhen Moldull",
        vendor_name="Shenzhen Moldull",
        product_name="Voice Recorder",
        description="Imprintable flat shell voice recorder. Dark grey housing with small LCD display, record button, and controls.",
        unit_cost="~$50",
        notes="MOQ 1,000 units for imprintable flat shell version.",
        status="Spotted",
    ),
    dict(
        show_name="Shenzhen Moldull",
        vendor_name="Shenzhen Moldull",
        product_name="Sleep Earbuds",
        description="Sleep earbuds.",
        unit_cost="~$12",
        notes="MOQ 3,000 units.",
        status="Spotted",
    ),
]

for data in items:
    p = Prospect(**data)
    p.save()
    print(f"✓ Created: [{p.pk}] {p}")
    print(f"  Add image at: /scouting/{p.pk}/edit/\n")

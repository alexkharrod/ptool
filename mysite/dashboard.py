"""
Staff home page: what needs attention right now, pulled from data the app
already holds. Pure queries — nothing here writes.

Thresholds live at the top so they're easy to tune.
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from products.models import Product
from quotes.models import CustomerQuote
from scouting.models import Prospect
from shipments.models import Shipment

ARRIVING_WINDOW_DAYS = 7      # "arriving soon" = ETA warehouse within this many days
STALE_QUOTE_DAYS = 14         # a sent quote with no change for this long is worth a follow-up
STALE_PROSPECT_DAYS = 30      # sample ordered / evaluating for this long without a decision
LIST_LIMIT = 8                # rows shown per card; the card links to the full list

OPEN_SHIPMENT_STATUSES = ["Ordered", "In Transit", "Arrived Port", "In Customs", "Out for Delivery"]


def _days_ago(d, today):
    return (today - d).days if d else None


def build_dashboard(today=None):
    today = today or timezone.localdate()
    soon = today + timedelta(days=ARRIVING_WINDOW_DAYS)

    # ── Shipments ────────────────────────────────────────────────────────
    open_shipments = Shipment.objects.filter(status__in=OPEN_SHIPMENT_STATUSES)
    overdue = list(
        open_shipments.filter(eta_warehouse__lt=today).order_by("eta_warehouse")[:LIST_LIMIT]
    )
    for s in overdue:
        s.days_late = _days_ago(s.eta_warehouse, today)
    arriving = list(
        open_shipments.filter(eta_warehouse__gte=today, eta_warehouse__lte=soon)
        .order_by("eta_warehouse")[:LIST_LIMIT]
    )
    for s in arriving:
        s.days_out = (s.eta_warehouse - today).days
    in_customs = list(open_shipments.filter(status="In Customs").order_by("eta_port")[:LIST_LIMIT])
    no_eta = open_shipments.filter(eta_warehouse__isnull=True).count()

    # ── Quotes ───────────────────────────────────────────────────────────
    stale_cutoff = today - timedelta(days=STALE_QUOTE_DAYS)
    stale_quotes = list(
        CustomerQuote.objects.filter(status="sent", date__lte=stale_cutoff)
        .select_related("rep").order_by("date")[:LIST_LIMIT]
    )
    for q in stale_quotes:
        q.days_old = _days_ago(q.date, today)
    stale_quote_count = CustomerQuote.objects.filter(status="sent", date__lte=stale_cutoff).count()
    draft_count = CustomerQuote.objects.filter(status="draft").count()

    # ── Scouting ─────────────────────────────────────────────────────────
    prospect_cutoff = timezone.now() - timedelta(days=STALE_PROSPECT_DAYS)
    deciding = list(
        Prospect.objects.filter(status__in=["Sample Ordered", "Evaluating"])
        .order_by("date_updated")[:LIST_LIMIT]
    )
    for p in deciding:
        p.days_waiting = (timezone.now() - p.date_updated).days
        p.is_stale = p.date_updated <= prospect_cutoff
    deciding_count = Prospect.objects.filter(status__in=["Sample Ordered", "Evaluating"]).count()
    needs_details_count = (
        Prospect.objects.filter(Prospect.needs_details_q())
        .exclude(promoted=True).exclude(status__in=["Rejected", "Adding"]).count()
    )

    # ── Products — launch checklist ──────────────────────────────────────
    open_products = Product.objects.filter(status="Open")
    checklist = {
        "npds_not_qb": open_products.filter(npds_done=True, qb_added=False),
        "no_npds": open_products.filter(npds_done=False),
        "no_image": open_products.filter(image="").filter(Q(image_url="") | Q(image_url__isnull=True)),
        "no_hts": open_products.filter(hts_code__isnull=True),
        "published_no_url": Product.objects.filter(status="Published").filter(Q(website_url="") | Q(website_url__isnull=True)),
    }
    checklist_rows = [
        ("NPDS done, not in QuickBooks", checklist["npds_not_qb"], "?status=Open"),
        ("Open, no NPDS yet", checklist["no_npds"], "?status=Open"),
        ("Open, no HTS code", checklist["no_hts"], "?status=Open"),
        ("Open, no image", checklist["no_image"], "?status=Open"),
        ("Published, no website URL", checklist["published_no_url"], "?status=Published"),
    ]
    checklist_rows = [
        {"label": label, "count": qs.count(), "sample": list(qs.order_by("sku")[:LIST_LIMIT]), "filter": flt}
        for label, qs, flt in checklist_rows
    ]

    return {
        "today": today,
        "shipments": {
            "open_count": open_shipments.count(),
            "overdue": overdue,
            "arriving": arriving,
            "in_customs": in_customs,
            "no_eta": no_eta,
            "window_days": ARRIVING_WINDOW_DAYS,
        },
        "quotes": {
            "stale": stale_quotes,
            "stale_count": stale_quote_count,
            "stale_days": STALE_QUOTE_DAYS,
            "draft_count": draft_count,
        },
        "scouting": {
            "deciding": deciding,
            "deciding_count": deciding_count,
            "needs_details_count": needs_details_count,
            "stale_days": STALE_PROSPECT_DAYS,
        },
        "products": {
            "open_count": open_products.count(),
            "checklist": checklist_rows,
        },
    }

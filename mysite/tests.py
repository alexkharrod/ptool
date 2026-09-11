from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from mysite.dashboard import ARRIVING_WINDOW_DAYS, STALE_QUOTE_DAYS, build_dashboard
from products.models import HtsCode, Product
from quotes.models import CustomerQuote
from scouting.models import Prospect
from shipments.models import Shipment

User = get_user_model()
PW = "testpass-123456"
TODAY = date(2026, 9, 11)


class DashboardQueryTests(TestCase):
    def test_shipments_bucketed_by_eta(self):
        Shipment.objects.create(shipment_number=1, status="In Transit", eta_warehouse=TODAY - timedelta(days=3))
        Shipment.objects.create(shipment_number=2, status="In Transit", eta_warehouse=TODAY)
        Shipment.objects.create(shipment_number=3, status="In Transit", eta_warehouse=TODAY + timedelta(days=ARRIVING_WINDOW_DAYS))
        Shipment.objects.create(shipment_number=4, status="In Transit", eta_warehouse=TODAY + timedelta(days=ARRIVING_WINDOW_DAYS + 1))
        Shipment.objects.create(shipment_number=5, status="Delivered", eta_warehouse=TODAY - timedelta(days=10))
        Shipment.objects.create(shipment_number=6, status="In Customs")
        d = build_dashboard(today=TODAY)["shipments"]
        self.assertEqual([s.shipment_number for s in d["overdue"]], [1])
        self.assertEqual(d["overdue"][0].days_late, 3)
        self.assertEqual([s.shipment_number for s in d["arriving"]], [2, 3])
        self.assertEqual(d["arriving"][0].days_out, 0)
        self.assertEqual([s.shipment_number for s in d["in_customs"]], [6])
        self.assertEqual(d["no_eta"], 1)
        self.assertEqual(d["open_count"], 5)  # delivered excluded

    def test_stale_quotes(self):
        CustomerQuote.objects.create(customer_name="Old", status="sent", date=TODAY - timedelta(days=STALE_QUOTE_DAYS))
        CustomerQuote.objects.create(customer_name="Fresh", status="sent", date=TODAY - timedelta(days=STALE_QUOTE_DAYS - 1))
        CustomerQuote.objects.create(customer_name="Draft", status="draft", date=TODAY - timedelta(days=60))
        d = build_dashboard(today=TODAY)["quotes"]
        self.assertEqual([q.customer_name for q in d["stale"]], ["Old"])
        self.assertEqual(d["stale"][0].days_old, STALE_QUOTE_DAYS)
        self.assertEqual(d["stale_count"], 1)
        self.assertEqual(d["draft_count"], 1)

    def test_scouting_buckets(self):
        Prospect.objects.create(show_name="s", vendor_name="v", product_name="Sample", status="Sample Ordered")
        Prospect.objects.create(show_name="s", vendor_name="v", product_name="Eval", status="Evaluating")
        Prospect.objects.create(show_name="s", vendor_name="v", product_name="Spotted", status="Spotted")
        Prospect.objects.create(show_name="s", vendor_name="v", product_name="Rejected no cost", status="Rejected")
        d = build_dashboard(today=TODAY)["scouting"]
        self.assertEqual({p.product_name for p in d["deciding"]}, {"Sample", "Eval"})
        self.assertEqual(d["deciding_count"], 2)
        # Spotted/Sample/Eval all lack cost etc.; Rejected excluded
        self.assertEqual(d["needs_details_count"], 3)

    def test_product_checklist(self):
        hts = HtsCode.objects.create(code="8517.62", description="x")
        Product.objects.create(sku="A1", vendor="v", status="Open", npds_done=True, qb_added=False, hts_code=hts, image_url="a.png")
        Product.objects.create(sku="A2", vendor="v", status="Open", npds_done=True, qb_added=True, hts_code=hts, image_url="a.png")
        Product.objects.create(sku="A3", vendor="v", status="Published", website_url="")
        Product.objects.create(sku="A4", vendor="v", status="Published", website_url="https://x")
        rows = {r["label"]: r for r in build_dashboard(today=TODAY)["products"]["checklist"]}
        self.assertEqual(rows["NPDS done, not in QuickBooks"]["count"], 1)
        self.assertEqual(rows["NPDS done, not in QuickBooks"]["sample"][0].sku, "A1")
        self.assertEqual(rows["Open, no NPDS yet"]["count"], 0)
        self.assertEqual(rows["Open, no HTS code"]["count"], 0)
        self.assertEqual(rows["Open, no image"]["count"], 0)
        self.assertEqual(rows["Published, no website URL"]["count"], 1)


class HomePageTests(TestCase):
    def test_staff_sees_dashboard(self):
        u = User.objects.create_user(email="s@t.com", password=PW)
        u.is_staff = True
        u.save()
        Shipment.objects.create(shipment_number=9, status="In Transit", eta_warehouse=date.today() - timedelta(days=2))
        self.client.login(email="s@t.com", password=PW)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Past ETA")
        self.assertContains(r, "#9")
        self.assertContains(r, "Product launch checklist")

    def test_non_staff_still_redirected_to_their_section(self):
        u = User.objects.create_user(email="q@t.com", password=PW)
        u.access_quotes = True
        u.save()
        self.client.login(email="q@t.com", password=PW)
        r = self.client.get("/")
        self.assertRedirects(r, "/quotes/cq/", fetch_redirect_response=False)

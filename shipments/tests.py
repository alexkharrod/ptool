from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Shipment, ShipmentItem

User = get_user_model()
PW = "testpass-123456"


def make_user(email, **flags):
    user = User.objects.create_user(email=email, password=PW)
    for k, v in flags.items():
        setattr(user, k, v)
    user.save()
    return user


def edit_post_data(shipment, item, include_cost=True):
    """Minimal valid POST for the edit page with one existing line item."""
    data = {
        "shipment_number": shipment.shipment_number,
        "mode": "Ocean",
        "status": "Ordered",
        "port_of_loading": "Shenzhen, China",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "1",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-id": str(item.pk),
        "items-0-sku": item.sku,
    }
    if include_cost:
        data["items-0-unit_cost_usd"] = str(item.unit_cost_usd)
    return data


class ShipmentAccessTests(TestCase):
    def setUp(self):
        self.viewer = make_user("viewer@t.com", access_shipments=True)
        self.logistics = make_user("logi@t.com", access_shipments_logistics=True)
        self.shipment = Shipment.objects.create(shipment_number=500, mode="Ocean")
        self.item = ShipmentItem.objects.create(
            shipment=self.shipment, sku="AB1", unit_cost_usd=Decimal("1.2345")
        )

    # ── view-only ──────────────────────────────────────────────────────────

    def test_viewer_can_see_list_and_detail(self):
        self.client.login(email="viewer@t.com", password=PW)
        self.assertEqual(self.client.get("/shipments/").status_code, 200)
        self.assertEqual(self.client.get(f"/shipments/{self.shipment.pk}/").status_code, 200)

    def test_viewer_never_sees_unit_cost(self):
        self.client.login(email="viewer@t.com", password=PW)
        r = self.client.get(f"/shipments/{self.shipment.pk}/")
        self.assertNotContains(r, "1.2345")
        self.assertNotContains(r, "Unit Cost")

    def test_viewer_list_has_no_edit_controls(self):
        self.client.login(email="viewer@t.com", password=PW)
        r = self.client.get("/shipments/")
        self.assertNotContains(r, "/shipments/add/")
        self.assertNotContains(r, f"/shipments/{self.shipment.pk}/edit/")
        self.assertNotContains(r, "data-pk=")  # no status dropdowns rendered

    def test_viewer_cannot_open_add_or_edit(self):
        self.client.login(email="viewer@t.com", password=PW)
        self.assertEqual(self.client.get("/shipments/add/").status_code, 302)
        self.assertEqual(self.client.get(f"/shipments/{self.shipment.pk}/edit/").status_code, 302)

    def test_viewer_edit_post_is_rejected_and_cost_untouched(self):
        """Regression: view-only users used to be able to POST an edit, and because
        their form omitted unit_cost_usd the save wiped every unit cost to NULL."""
        self.client.login(email="viewer@t.com", password=PW)
        r = self.client.post(
            f"/shipments/{self.shipment.pk}/edit/",
            edit_post_data(self.shipment, self.item, include_cost=False),
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/")
        self.item.refresh_from_db()
        self.assertEqual(self.item.unit_cost_usd, Decimal("1.2345"))

    def test_viewer_cannot_change_status(self):
        self.client.login(email="viewer@t.com", password=PW)
        r = self.client.post(
            f"/shipments/{self.shipment.pk}/update-status/",
            '{"status": "Delivered"}', content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, "Ordered")

    def test_viewer_cannot_upload_or_delete_docs_or_parse(self):
        self.client.login(email="viewer@t.com", password=PW)
        pk = self.shipment.pk
        self.assertEqual(self.client.post(f"/shipments/{pk}/upload-doc/").status_code, 302)
        self.assertEqual(self.client.post(f"/shipments/{pk}/delete-doc/1/").status_code, 302)
        self.assertEqual(self.client.post("/shipments/parse-doc/").status_code, 302)

    # ── logistics ──────────────────────────────────────────────────────────

    def test_logistics_sees_unit_cost_on_detail(self):
        """Regression: the detail view never passed can_edit, so unit costs and the
        Edit button were hidden from everyone — staff included."""
        self.client.login(email="logi@t.com", password=PW)
        r = self.client.get(f"/shipments/{self.shipment.pk}/")
        self.assertContains(r, "1.2345")
        self.assertContains(r, f"/shipments/{self.shipment.pk}/edit/")

    def test_logistics_edit_preserves_unit_cost(self):
        self.client.login(email="logi@t.com", password=PW)
        r = self.client.post(
            f"/shipments/{self.shipment.pk}/edit/",
            edit_post_data(self.shipment, self.item, include_cost=True),
        )
        self.assertRedirects(r, f"/shipments/{self.shipment.pk}/", fetch_redirect_response=False)
        self.item.refresh_from_db()
        self.assertEqual(self.item.unit_cost_usd, Decimal("1.2345"))

    def test_logistics_can_change_status(self):
        self.client.login(email="logi@t.com", password=PW)
        r = self.client.post(
            f"/shipments/{self.shipment.pk}/update-status/",
            '{"status": "Delivered"}', content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, "Delivered")

    def test_logistics_can_add_shipment(self):
        self.client.login(email="logi@t.com", password=PW)
        r = self.client.post("/shipments/add/", {
            "shipment_number": "501",
            "mode": "Air",
            "status": "Ordered",
            "port_of_loading": "Shenzhen, China",
            "items-TOTAL_FORMS": "0",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Shipment.objects.filter(shipment_number=501).exists())

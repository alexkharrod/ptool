from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Prospect
from .views import PAGE_SIZE

User = get_user_model()
PW = "testpass-123456"


def make_prospect(i, **kw):
    fields = dict(
        show_name="Test Expo", vendor_name=f"Vendor {i}", product_name=f"Widget {i}",
        unit_cost="$1.00", lead_time="30 days", vendor_contact="Someone",
    )
    fields.update(kw)
    return Prospect.objects.create(**fields)


class ScoutingBase(TestCase):
    def setUp(self):
        user = User.objects.create_user(email="scout@t.com", password=PW)
        user.access_scouting = True
        user.save()
        self.client.login(email="scout@t.com", password=PW)


class ListTests(ScoutingBase):
    def test_list_is_paginated(self):
        for i in range(PAGE_SIZE + 6):
            make_prospect(i)
        r = self.client.get(reverse("scouting_list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["prospects"]), PAGE_SIZE)
        self.assertEqual(r.context["total_count"], PAGE_SIZE + 6)
        self.assertContains(r, "page 1 of 2")
        r2 = self.client.get(reverse("scouting_list") + "?page=2")
        self.assertEqual(len(r2.context["prospects"]), 6)

    def test_pagination_links_keep_filters(self):
        for i in range(PAGE_SIZE + 1):
            make_prospect(i, show_name="PPAI")
        r = self.client.get(reverse("scouting_list") + "?show=PPAI&page=1")
        self.assertContains(r, "?show=PPAI&amp;page=2")

    def test_needs_details_filter(self):
        complete = make_prospect(1)
        no_cost = make_prospect(2, unit_cost="")
        no_lead = make_prospect(3, lead_time="")
        no_contact = make_prospect(4, vendor_contact="")
        promoted = make_prospect(5, unit_cost="", promoted=True, promoted_sku="AB1")
        r = self.client.get(reverse("scouting_list") + "?needs=1")
        pks = {p.pk for p in r.context["prospects"]}
        self.assertEqual(pks, {no_cost.pk, no_lead.pk, no_contact.pk})
        self.assertNotIn(complete.pk, pks)
        self.assertNotIn(promoted.pk, pks, "promoted prospects are done — don't nag about them")

    def test_needs_details_badge_on_card(self):
        make_prospect(1, unit_cost="", lead_time="")
        r = self.client.get(reverse("scouting_list"))
        self.assertContains(r, "Needs cost, lead time")

    def test_complete_prospect_has_no_badge(self):
        make_prospect(1)
        r = self.client.get(reverse("scouting_list"))
        self.assertNotContains(r, "badge bg-warning")


class ModelTests(TestCase):
    def test_needs_details_property(self):
        self.assertFalse(make_prospect(1).needs_details)
        p = make_prospect(2, lead_time="", vendor_contact="")
        self.assertTrue(p.needs_details)
        self.assertEqual(p.missing_details, ["lead time", "contact"])

    def test_prospect_number_increments(self):
        a = make_prospect(1)
        b = make_prospect(2)
        self.assertEqual(a.prospect_number, "PRO-0001")
        self.assertEqual(b.prospect_number, "PRO-0002")


class AddTests(ScoutingBase):
    def test_add_page_renders(self):
        r = self.client.get(reverse("scouting_add"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="photo-drop"')
        self.assertContains(r, "Scan Card")
        # No active show → the details section is open so show_name is visible
        self.assertContains(r, 'class="collapse show" id="more-details"')

    def test_add_prefills_show_from_session(self):
        self.client.post(reverse("set_active_show"), {"show_name": "PPAI Expo", "show_date": "2026-01-13"})
        r = self.client.get(reverse("scouting_add"))
        self.assertEqual(r.context["form"].initial["show_name"], "PPAI Expo")
        # Active show → details collapsed
        self.assertContains(r, 'class="collapse " id="more-details"')

    def test_async_add_returns_json_with_number(self):
        r = self.client.post(
            reverse("scouting_add"),
            {"show_name": "PPAI", "vendor_name": "Acme", "product_name": "Gizmo", "status": "Spotted"},
            HTTP_X_ASYNC_SUBMIT="1",
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["prospect_number"], "PRO-0001")
        self.assertEqual(data["product_name"], "Gizmo")
        self.assertEqual(data["vendor_name"], "Acme")
        self.assertTrue(Prospect.objects.filter(pk=data["pk"]).exists())

    def test_async_add_missing_required_returns_400(self):
        r = self.client.post(
            reverse("scouting_add"),
            {"show_name": "PPAI", "product_name": "Gizmo", "status": "Spotted"},
            HTTP_X_ASYNC_SUBMIT="1",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("vendor_name", r.json()["errors"])
        self.assertEqual(Prospect.objects.count(), 0)

    def test_quick_capture_needs_only_photo_name_vendor(self):
        """Cost, lead time and contact are optional on the floor; they show up in Needs details."""
        r = self.client.post(
            reverse("scouting_add"),
            {"show_name": "PPAI", "vendor_name": "Acme", "product_name": "Gizmo", "status": "Spotted"},
            HTTP_X_ASYNC_SUBMIT="1",
        )
        p = Prospect.objects.get(pk=r.json()["pk"])
        self.assertTrue(p.needs_details)
        r = self.client.get(reverse("scouting_list") + "?needs=1")
        self.assertContains(r, "Gizmo")

    def test_non_async_add_redirects_to_detail(self):
        r = self.client.post(
            reverse("scouting_add"),
            {"show_name": "PPAI", "vendor_name": "Acme", "product_name": "Gizmo", "status": "Spotted"},
        )
        p = Prospect.objects.get()
        self.assertRedirects(r, reverse("scouting_detail", args=[p.pk]))

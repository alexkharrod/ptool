from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Product, Vendor

User = get_user_model()
PW = "testpass-123456"


def make_user(email, **flags):
    user = User.objects.create_user(email=email, password=PW)
    for k, v in flags.items():
        setattr(user, k, v)
    user.save()
    return user


class VendorModelTests(TestCase):
    def test_create_vendor(self):
        v = Vendor.objects.create(name="Test Vendor")
        self.assertEqual(str(v), "Test Vendor")
        self.assertEqual(v.country, "CN")  # default

    def test_vendor_unique_name(self):
        Vendor.objects.create(name="DT")
        with self.assertRaises(Exception):
            Vendor.objects.create(name="DT")

    def test_vendor_ordering(self):
        Vendor.objects.create(name="Zebra")
        Vendor.objects.create(name="Alpha")
        Vendor.objects.create(name="Midway")
        names = list(Vendor.objects.values_list("name", flat=True))
        self.assertEqual(names, sorted(names))


class VendorViewTests(TestCase):
    """Vendor management lives under Admin and is staff-only."""

    def setUp(self):
        self.client = Client()
        self.user = make_user("alex@test.com", is_staff=True)
        self.client.login(email="alex@test.com", password=PW)

    def test_vendor_list_renders(self):
        Vendor.objects.create(name="RSH")
        response = self.client.get(reverse("vendor_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RSH")

    def test_vendor_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("vendor_list"))
        self.assertRedirects(response, f"/login/?next={reverse('vendor_list')}", fetch_redirect_response=False)

    def test_add_vendor(self):
        response = self.client.post(reverse("vendor_add"), {
            "name": "New Vendor",
            "country": "CN",
        })
        self.assertRedirects(response, reverse("vendor_list"))
        self.assertTrue(Vendor.objects.filter(name="New Vendor").exists())

    def test_add_vendor_duplicate_blocked(self):
        Vendor.objects.create(name="Existing")
        response = self.client.post(reverse("vendor_add"), {
            "name": "Existing",
            "country": "CN",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(Vendor.objects.filter(name="Existing").count(), 1)

    def test_add_vendor_duplicate_case_insensitive(self):
        Vendor.objects.create(name="goodwin")
        response = self.client.post(reverse("vendor_add"), {
            "name": "GOODWIN",
            "country": "CN",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")

    def test_add_vendor_blank_name_blocked(self):
        response = self.client.post(reverse("vendor_add"), {"name": "", "country": "CN"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "required")

    def test_edit_vendor(self):
        vendor = Vendor.objects.create(name="Old Name")
        response = self.client.post(reverse("vendor_edit", args=[vendor.pk]), {
            "name": "New Name",
            "country": "CN",
        })
        self.assertRedirects(response, reverse("vendor_list"))
        vendor.refresh_from_db()
        self.assertEqual(vendor.name, "New Name")

    def test_edit_vendor_duplicate_blocked(self):
        v1 = Vendor.objects.create(name="Alpha")
        Vendor.objects.create(name="Beta")
        response = self.client.post(reverse("vendor_edit", args=[v1.pk]), {
            "name": "Beta",
            "country": "CN",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")

    def test_edit_vendor_same_name_allowed(self):
        """Saving a vendor with its own name should not trigger duplicate error."""
        vendor = Vendor.objects.create(name="RSH")
        response = self.client.post(reverse("vendor_edit", args=[vendor.pk]), {
            "name": "RSH",
            "country": "TW",
        })
        self.assertRedirects(response, reverse("vendor_list"))
        vendor.refresh_from_db()
        self.assertEqual(vendor.country, "TW")


class AccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        make_user("products@test.com", access_products=True)
        make_user("scouting@test.com", access_scouting=True)

    def test_scouting_user_blocked_from_products(self):
        self.client.login(email="scouting@test.com", password=PW)
        response = self.client.get("/products/")
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)

    def test_scouting_user_blocked_from_quotes(self):
        self.client.login(email="scouting@test.com", password=PW)
        response = self.client.get("/quotes/cq/")
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)

    def test_products_user_can_access_products(self):
        self.client.login(email="products@test.com", password=PW)
        response = self.client.get("/products/")
        self.assertEqual(response.status_code, 200)

    def test_products_user_blocked_from_staff_admin_pages(self):
        self.client.login(email="products@test.com", password=PW)
        for name in ("vendor_list", "hts_list", "category_list", "report_index"):
            response = self.client.get(reverse(name))
            self.assertRedirects(response, reverse("home"), fetch_redirect_response=False, msg_prefix=name)


class BulkUpdateTests(TestCase):
    def setUp(self):
        self.client = Client()
        make_user("staff@test.com", is_staff=True)
        self.client.login(email="staff@test.com", password=PW)

    def test_bulk_publish_stamps_date_published(self):
        """Regression: bulk update used queryset.update(), bypassing Product.save(),
        so bulk-published products never got a date_published."""
        p1 = Product.objects.create(sku="BU1", vendor="v")
        p2 = Product.objects.create(sku="BU2", vendor="v")
        response = self.client.post(reverse("bulk_update_products"), {
            "product_ids": [p1.pk, p2.pk],
            "bulk_status": "Published",
        })
        self.assertEqual(response.status_code, 302)
        for p in (p1, p2):
            p.refresh_from_db()
            self.assertEqual(p.status, "Published")
            self.assertIsNotNone(p.date_published, p.sku)

    def test_bulk_republish_keeps_original_date(self):
        p = Product.objects.create(sku="BU3", vendor="v", status="Published")
        first = p.date_published
        self.assertIsNotNone(first)
        self.client.post(reverse("bulk_update_products"), {"product_ids": [p.pk], "bulk_status": "Open"})
        self.client.post(reverse("bulk_update_products"), {"product_ids": [p.pk], "bulk_status": "Published"})
        p.refresh_from_db()
        self.assertEqual(p.date_published, first)

    def test_bulk_update_shows_message(self):
        p = Product.objects.create(sku="BU4", vendor="v")
        response = self.client.post(reverse("bulk_update_products"), {
            "product_ids": [p.pk], "bulk_status": "Canceled",
        }, follow=True)
        self.assertContains(response, "1 product(s) updated to Canceled")

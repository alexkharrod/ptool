from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Vendor

User = get_user_model()


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
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="alex", password="testpass")
        self.client.login(username="alex", password="testpass")

    def test_vendor_list_renders(self):
        Vendor.objects.create(name="RSH")
        response = self.client.get(reverse("vendor_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RSH")

    def test_vendor_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("vendor_list"))
        self.assertRedirects(response, f"/login/?next={reverse('vendor_list')}")

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
        self.regular_user = User.objects.create_user(username="alex", password="pass")
        self.scouting_user = User.objects.create_user(
            username="china", password="pass", scouting_only=True
        )

    def test_scouting_only_blocked_from_products(self):
        self.client.login(username="china", password="pass")
        response = self.client.get("/products/")
        self.assertRedirects(response, reverse("scouting_list"))

    def test_scouting_only_blocked_from_quotes(self):
        self.client.login(username="china", password="pass")
        response = self.client.get("/quotes/")
        self.assertRedirects(response, reverse("scouting_list"))

    def test_regular_user_can_access_products(self):
        self.client.login(username="alex", password="pass")
        response = self.client.get("/products/")
        self.assertEqual(response.status_code, 200)

    def test_must_change_password_redirects(self):
        User.objects.create_user(
            username="newuser", password="pass", must_change_password=True
        )
        self.client.login(username="newuser", password="pass")
        response = self.client.get("/products/")
        self.assertRedirects(response, reverse("change_password"))

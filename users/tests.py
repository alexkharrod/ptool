"""
Access-control tests.

The important one is `UrlSweepTests`: it walks every URL pattern in the project
and checks that a logged-in user with no access flags cannot reach anything under
/products/, /quotes/, /scouting/ or /shipments/. If someone adds a view and forgets
`@section_required`, this fails.
"""

import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver

from users.decorators import SECTIONS, section_required, user_has_section

User = get_user_model()
PW = "testpass-123456"

SECTION_PREFIXES = {
    "/products/": "products",
    "/quotes/": "quotes",
    "/scouting/": "scouting",
    "/shipments/": "shipments",
}

# Any int converter in a URL gets this value — the decorator runs before the
# view looks the object up, so it doesn't matter that nothing exists.
DUMMY_PK = 1


def _walk(patterns, prefix=""):
    """Yield (path, callback) for every leaf URL pattern."""
    for p in patterns:
        if isinstance(p, URLResolver):
            yield from _walk(p.url_patterns, prefix + str(p.pattern))
        elif isinstance(p, URLPattern):
            yield prefix + str(p.pattern), p.callback


def _fill(path):
    """Turn 'products/edit/<int:pk>/' into '/products/edit/1/'."""
    return "/" + re.sub(r"<[^>]+>", str(DUMMY_PK), path).lstrip("/")


def section_urls():
    """All (url, section, callback) tuples under the four section prefixes."""
    out = []
    for path, callback in _walk(get_resolver().url_patterns):
        url = _fill(path)
        for prefix, section in SECTION_PREFIXES.items():
            if url.startswith(prefix):
                out.append((url, section, callback))
    return out


def make_user(email, **flags):
    user = User.objects.create_user(email=email, password=PW)
    for k, v in flags.items():
        setattr(user, k, v)
    user.save()
    return user


class DecoratorTests(TestCase):
    def test_staff_passes_every_section(self):
        staff = make_user("staff@t.com", is_staff=True)
        for section in SECTIONS:
            self.assertTrue(user_has_section(staff, section), section)

    def test_flag_grants_only_its_section(self):
        u = make_user("q@t.com", access_quotes=True)
        self.assertTrue(user_has_section(u, "quotes"))
        for section in ("products", "scouting", "shipments", "shipments_logistics", "staff"):
            self.assertFalse(user_has_section(u, section), section)

    def test_logistics_flag_implies_shipments_view(self):
        u = make_user("l@t.com", access_shipments_logistics=True)
        self.assertTrue(user_has_section(u, "shipments"))
        self.assertTrue(user_has_section(u, "shipments_logistics"))

    def test_view_only_shipments_flag_does_not_grant_logistics(self):
        u = make_user("v@t.com", access_shipments=True)
        self.assertTrue(user_has_section(u, "shipments"))
        self.assertFalse(user_has_section(u, "shipments_logistics"))

    def test_unknown_section_rejected_at_import_time(self):
        with self.assertRaises(ValueError):
            section_required("nope")

    def test_json_request_gets_403_not_redirect(self):
        make_user("v@t.com", access_shipments=True)
        self.client.login(email="v@t.com", password=PW)
        r = self.client.post(
            "/shipments/1/update-status/", '{"status": "Delivered"}', content_type="application/json"
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["ok"], False)


class UrlSweepTests(TestCase):
    """Every section URL must be closed to anonymous users and to users without the flag."""

    def test_every_section_view_is_decorated(self):
        missing = [url for url, _, cb in section_urls() if not getattr(cb, "section", None)]
        self.assertEqual(missing, [], f"Views without @section_required: {missing}")

    def test_decorator_section_matches_url_prefix(self):
        wrong = []
        for url, section, cb in section_urls():
            declared = getattr(cb, "section", None)
            ok = declared == section or declared == "staff" or (
                section == "shipments" and declared == "shipments_logistics"
            )
            if not ok:
                wrong.append((url, declared))
        self.assertEqual(wrong, [], f"Section mismatch: {wrong}")

    def test_anonymous_is_sent_to_login(self):
        for url, _, _ in section_urls():
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertTrue(r["Location"].startswith("/login/"), (url, r["Location"]))

    def test_user_without_flags_is_blocked_everywhere(self):
        make_user("noflags@t.com")
        self.client.login(email="noflags@t.com", password=PW)
        for url, _, _ in section_urls():
            r = self.client.get(url)
            self.assertIn(r.status_code, (302, 403), (url, r.status_code))
            if r.status_code == 302:
                self.assertEqual(r["Location"], "/", url)

    def test_staff_only_urls_blocked_for_full_access_non_staff(self):
        make_user(
            "power@t.com",
            access_products=True, access_quotes=True, access_scouting=True,
            access_shipments_logistics=True,
        )
        self.client.login(email="power@t.com", password=PW)
        staff_urls = [url for url, _, cb in section_urls() if getattr(cb, "section", None) == "staff"]
        self.assertTrue(staff_urls, "expected some staff-only URLs")
        for url in staff_urls:
            r = self.client.get(url)
            self.assertIn(r.status_code, (302, 403), (url, r.status_code))


class MiddlewareTests(TestCase):
    def test_must_change_password_redirects(self):
        make_user("new@t.com", access_products=True, must_change_password=True)
        self.client.login(email="new@t.com", password=PW)
        r = self.client.get("/products/")
        self.assertRedirects(r, "/users/change-password/", fetch_redirect_response=False)

    def test_non_staff_blocked_from_django_admin(self):
        make_user("u@t.com", access_products=True)
        self.client.login(email="u@t.com", password=PW)
        r = self.client.get("/admin/")
        self.assertRedirects(r, "/", fetch_redirect_response=False)

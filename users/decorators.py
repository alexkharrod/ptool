"""
Section access control — the single place that decides who may hit a view.

Usage:
    @section_required("products")
    def products(request): ...

    @section_required("shipments_logistics")
    def shipment_edit(request, pk): ...

Every section name maps to a `can_access_*` property on CustomUser (or `is_staff`
for "staff"), so the rules live on the user model and nowhere else. Staff always
pass. Anonymous users are sent to the login page; logged-in users without the flag
are sent home — or get a JSON 403 if the request looks like an AJAX call, so fetch()
callers see a real error instead of a redirected HTML page.

`users/tests.py` walks every URL in the project and checks that each one is
protected, so a view that forgets this decorator fails the test suite.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect

SECTIONS = {
    "products": "can_access_products",
    "quotes": "can_access_quotes",
    "scouting": "can_access_scouting",
    "shipments": "can_access_shipments",
    "shipments_logistics": "can_access_shipments_logistics",
    "staff": "is_staff",
}


def user_has_section(user, section):
    """True if `user` may access `section`. Staff always pass."""
    attr = SECTIONS[section]
    return bool(getattr(user, "is_staff", False) or getattr(user, attr, False))


def _wants_json(request):
    """Best guess at whether the caller is fetch()/XHR rather than a browser navigation."""
    accept = request.headers.get("Accept", "")
    return (
        request.content_type == "application/json"
        or "application/json" in accept
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.headers.get("X-Async-Submit") == "1"
    )


def section_required(section):
    if section not in SECTIONS:
        raise ValueError(f"Unknown section {section!r}; expected one of {sorted(SECTIONS)}")

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not user_has_section(request.user, section):
                if _wants_json(request):
                    return JsonResponse({"ok": False, "error": "Access denied"}, status=403)
                return redirect("home")
            return view_func(request, *args, **kwargs)

        _wrapped.section = section  # inspected by the URL sweep test
        return _wrapped

    return decorator

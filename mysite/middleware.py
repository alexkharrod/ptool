from django.shortcuts import redirect

# URLs a must-change-password user can still visit
_PASSWORD_EXEMPT = ["/users/change-password/", "/login/", "/logout/", "/sw.js", "/static/"]


class PtoolAccessMiddleware:
    """
    Forces a password change when `must_change_password` is set.

    Section access (products / quotes / scouting / shipments) is NOT enforced here.
    Each view carries `@section_required(...)` from `users/decorators.py`, and
    `users/tests.py` sweeps every URL to make sure none is left unprotected.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            if getattr(user, "must_change_password", False) and not any(
                request.path.startswith(u) for u in _PASSWORD_EXEMPT
            ):
                return redirect("change_password")

            # Django admin is staff-only; send non-staff home instead of to the admin login
            if request.path.startswith("/admin/") and not user.is_staff:
                return redirect("home")

        return self.get_response(request)

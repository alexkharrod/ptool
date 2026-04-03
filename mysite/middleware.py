from django.shortcuts import redirect


# URLs a must-change-password user can still visit
_PASSWORD_EXEMPT = ["/users/change-password/", "/login/", "/logout/", "/sw.js", "/static/"]

# URL prefixes a scouting-only user is NOT allowed to visit
_SCOUTING_BLOCKED = ["/products/", "/quotes/", "/admin/"]


class PtoolAccessMiddleware:
    """
    Two access rules applied after authentication:
    1. must_change_password  → redirect to change-password page until they set one.
    2. scouting_only         → redirect away from products/quotes to scouting.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            # Rule 1: forced password change
            if getattr(user, "must_change_password", False) and not any(
                request.path.startswith(u) for u in _PASSWORD_EXEMPT
            ):
                return redirect("change_password")

            # Rule 2: scouting-only access
            if getattr(user, "scouting_only", False) and any(
                request.path.startswith(u) for u in _SCOUTING_BLOCKED
            ):
                return redirect("scouting_list")

        return self.get_response(request)

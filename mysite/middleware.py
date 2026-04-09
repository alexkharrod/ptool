from django.shortcuts import redirect

# URLs a must-change-password user can still visit
_PASSWORD_EXEMPT = ["/users/change-password/", "/login/", "/logout/", "/sw.js", "/static/"]


class PtoolAccessMiddleware:
    """
    Two access rules applied after authentication:
    1. must_change_password  → redirect to change-password page until they set one.
    2. Section access flags  → staff bypass everything; non-staff are blocked from
       sections where their access_products / access_quotes / access_scouting is False.
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

            # Rule 2: section access control (staff always bypass)
            if not user.is_staff:
                if request.path.startswith("/products/") and not user.access_products:
                    return redirect("home")
                if request.path.startswith("/quotes/") and not user.access_quotes:
                    return redirect("home")
                if request.path.startswith("/scouting/") and not user.access_scouting:
                    return redirect("home")
                if request.path.startswith("/admin/"):
                    return redirect("home")

        return self.get_response(request)

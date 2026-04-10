from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import TemplateView


def service_worker(request):
    import os
    sw_path = os.path.join(settings.BASE_DIR, "static", "sw.js")
    with open(sw_path, "r") as f:
        content = f.read()
    return HttpResponse(content, content_type="application/javascript")


@login_required
def home(request):
    user = request.user
    # Staff see the full dashboard
    if user.is_staff:
        from django.shortcuts import render
        return render(request, "index.html")
    # Non-staff: route to their first accessible section
    if user.access_products:
        return redirect("products")
    if user.access_quotes:
        return redirect("quotes")
    if user.access_scouting:
        return redirect("scouting_list")
    if user.access_shipments:
        return redirect("shipment_list")
    # No access flags set yet — show a holding page
    from django.shortcuts import render
    return render(request, "no_access.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("products/", include("products.urls")),
    path("quotes/", include("quotes.urls")),
    path("users/", include("users.urls")),
    path("scouting/", include("scouting.urls")),
    path("shipments/", include("shipments.urls")),
    path(
        "login/",
        LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("sw.js", service_worker, name="service_worker"),
]

# Serve uploaded media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

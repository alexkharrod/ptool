from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import TemplateView


def service_worker(request):
    import os
    sw_path = os.path.join(settings.BASE_DIR, "static", "sw.js")
    with open(sw_path, "r") as f:
        content = f.read()
    return HttpResponse(content, content_type="application/javascript")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", login_required(TemplateView.as_view(template_name="index.html")), name="home"),
    path("products/", include("products.urls")),
    path("quotes/", include("quotes.urls")),
    path("users/", include("users.urls")),
    path("scouting/", include("scouting.urls")),
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

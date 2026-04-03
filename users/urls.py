from django.urls import path

from . import views

# urls for logout app
urlpatterns = [
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password, name="change_password"),
]

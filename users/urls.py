from django.urls import path

from . import views

urlpatterns = [
    path("logout/",           views.logout_view,        name="logout"),
    path("change-password/",  views.change_password,    name="change_password"),

    # User management (staff only)
    path("manage/",                views.user_manage,        name="user_manage"),
    path("manage/create/",         views.user_create,        name="user_create"),
    path("manage/<int:pk>/edit/",  views.user_edit,          name="user_edit"),
    path("manage/toggle/<int:pk>/", views.user_toggle_access, name="user_toggle_access"),
]

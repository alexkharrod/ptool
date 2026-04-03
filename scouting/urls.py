from django.urls import path

from . import views

urlpatterns = [
    path("", views.scouting_list, name="scouting_list"),
    path("add/", views.scouting_add, name="scouting_add"),
    path("scan-card/", views.scan_business_card, name="scan_business_card"),
    path("<int:pk>/", views.scouting_detail, name="scouting_detail"),
    path("<int:pk>/edit/", views.scouting_edit, name="scouting_edit"),
    path("<int:pk>/promote/", views.scouting_promote, name="scouting_promote"),
]

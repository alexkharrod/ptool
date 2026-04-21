from django.urls import path

from . import views

urlpatterns = [
    path("", views.shipment_list, name="shipment_list"),
    path("add/", views.shipment_add, name="shipment_add"),
    path("<int:pk>/", views.shipment_detail, name="shipment_detail"),
    path("<int:pk>/edit/", views.shipment_edit, name="shipment_edit"),
    path("<int:pk>/upload-doc/", views.shipment_upload_doc, name="shipment_upload_doc"),
    path("<int:pk>/delete-doc/<int:doc_pk>/", views.shipment_delete_doc, name="shipment_delete_doc"),
    path("<int:pk>/update-status/", views.shipment_update_status, name="shipment_update_status"),
    path("parse-doc/", views.shipment_parse_doc, name="shipment_parse_doc"),
]

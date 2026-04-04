from django.urls import path

from . import views

# urls for product app
urlpatterns = [
    path("", views.products, name="products"),
    path("bulk-update/", views.bulk_update_products, name="bulk_update_products"),
    path("add_product/", views.add_product, name="add_product"),
    path("edit/<int:pk>/", views.edit_product, name="edit_product"),
    path("view/<int:pk>/", views.view_product, name="view_product"),
    path("npds/<int:product_id>/pdf/", views.npds, name="npds"),
    path("toggle-flag/<int:pk>/", views.toggle_product_flag, name="toggle_product_flag"),
    # Vendor management
    path("vendors/", views.vendor_list, name="vendor_list"),
    path("vendors/add/", views.vendor_add, name="vendor_add"),
    path("vendors/<int:pk>/edit/", views.vendor_edit, name="vendor_edit"),
]

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
    path("view/<int:pk>/generate-description/", views.generate_description, name="generate_description"),
    path("view/<int:pk>/generate-keywords/", views.generate_keywords, name="generate_keywords"),
    path("view/<int:pk>/web-content/", views.product_web_content, name="product_web_content"),
    # HTS code management
    path("hts/", views.hts_list, name="hts_list"),
    path("hts/add/", views.hts_add, name="hts_add"),
    path("hts/<int:pk>/edit/", views.hts_edit, name="hts_edit"),
    path("hts/suggest/", views.hts_suggest, name="hts_suggest"),
    # Vendor management
    path("vendors/", views.vendor_list, name="vendor_list"),
    path("vendors/add/", views.vendor_add, name="vendor_add"),
    path("vendors/<int:pk>/edit/", views.vendor_edit, name="vendor_edit"),
    # Category management
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_add, name="category_add"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
]

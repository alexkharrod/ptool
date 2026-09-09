from django.urls import path

from . import views

# urls for quotes app
urlpatterns = [
    # ── New customer quote system ─────────────────────────────────────────────
    path("cq/", views.cq_list, name="cq_list"),
    path("cq/new/", views.cq_create, name="cq_create"),
    path("cq/<int:pk>/edit/", views.cq_edit, name="cq_edit"),
    path("cq/<int:pk>/view/", views.cq_view, name="cq_view"),
    path("cq/<int:pk>/pdf/", views.cq_pdf, name="cq_pdf"),
    path("cq/<int:quote_pk>/item-add/", views.cq_item_add, name="cq_item_add"),
    path("cq/item/<int:item_pk>/save/", views.cq_item_save, name="cq_item_save"),
    path("cq/item/<int:item_pk>/delete/", views.cq_item_delete, name="cq_item_delete"),
    path("cq/product-search/", views.cq_product_search, name="cq_product_search"),
    path("cq/rep-add/", views.cq_rep_add, name="cq_rep_add"),
    path("cq/<int:pk>/delete/", views.cq_delete, name="cq_delete"),
]

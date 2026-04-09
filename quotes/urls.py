from django.urls import path

from . import views

# urls for quotes app
urlpatterns = [
    # ── Legacy quote system (kept for existing records) ──────────────────────
    path("create-quote/", views.create_quote, name="create_quote"),
    path("quotes/", views.quotes, name="quotes"),
    path("bulk-update/", views.bulk_update_quotes, name="bulk_update_quotes"),
    path("view-quote/<int:pk>/", views.view_quote, name="view_quote"),
    path("quote/<int:quote_id>/pdf/", views.quote_pdf, name="quote_pdf"),
    path("edit-quote/<int:pk>/", views.edit_quote, name="edit_quote"),
    path("quote/<int:pk>/update-status/", views.update_quote_status, name="update_quote_status"),

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
]

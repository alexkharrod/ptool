from django.urls import path

from . import views

# urls for quotes app
urlpatterns = [
    path("create-quote/", views.create_quote, name="create_quote"),
    path("quotes/", views.quotes, name="quotes"),
    path("bulk-update/", views.bulk_update_quotes, name="bulk_update_quotes"),
    path("view-quote/<int:pk>/", views.view_quote, name="view_quote"),
    path("quote/<int:quote_id>/pdf/", views.quote_pdf, name="quote_pdf"),
    path("edit-quote/<int:pk>/", views.edit_quote, name="edit_quote"),
    path("quote/<int:pk>/update-status/", views.update_quote_status, name="update_quote_status"),
]

"""URL configuration for the opt-in front end, included by the host at a prefix of its choice."""

from django.urls import path

from . import views
from .catalogue import catalogue

app_name = "literature"

urlpatterns = [
    # The one route whose view a project chooses (``LITERATURE["CATALOGUE_VIEW"]``).
    # Routes share one namespace, so the choice is made behind the name.
    path("", catalogue, name="item-list"),
    path("add/", views.ItemCreateView.as_view(), name="item-create"),
    path("import/", views.ItemImportView.as_view(), name="item-import"),
    # A GET rebuilds the report from the staged file, so reloading imports nothing.
    path(
        "import/preview/",
        views.ItemImportPreviewView.as_view(),
        name="item-import-preview",
    ),
    path(
        "import/restart/",
        views.ItemImportRestartView.as_view(),
        name="item-import-restart",
    ),
    # A route of its own, so only the staged file's token says which upload this POST means.
    path(
        "import/confirm/",
        views.ItemImportConfirmView.as_view(),
        name="item-import-confirm",
    ),
    path(
        "autocomplete/",
        views.ReferenceAutocompleteView.as_view(),
        name="item-autocomplete",
    ),
    path("<int:pk>/", views.ItemDetailView.as_view(), name="item-detail"),
    path("<int:pk>/update/", views.ItemUpdateView.as_view(), name="item-update"),
    path("<int:pk>/delete/", views.ItemDeleteView.as_view(), name="item-delete"),
    path(
        "contributors/<int:pk>/",
        views.ContributorDetailView.as_view(),
        name="contributor-detail",
    ),
]

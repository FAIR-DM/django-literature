"""URL configuration for the opt-in front end.

Nothing is mounted automatically — the host includes this module at whatever
prefix it chooses.

Routes were filled in incrementally, one class per story: ``ItemListView``
and ``ContributorDetailView`` by FS-006 (#55), ``ItemCreateView``,
``ItemUpdateView`` and ``ItemDeleteView`` by FS-008 (#74), the import routes
by FS-011 (#103). The relative import below reaches only within
``literature.ui`` itself, so it carries none of the import-time risk an
absolute ``literature.*`` import would (see ``literature/ui/apps.py``).
Routing is this app's contract and is owned once, here.
"""

from django.urls import path

from . import views
from .catalogue import catalogue

app_name = "literature"

urlpatterns = [
    # The one route whose view is a project's to choose: the table by
    # default, the card list or a subclass of either through
    # ``LITERATURE["CATALOGUE_VIEW"]``. Every other route in this app is
    # fixed, and all of them share this module's one namespace, so the
    # choice is made behind the name rather than by overriding the route.
    path("", catalogue, name="item-list"),
    path("add/", views.ItemCreateView.as_view(), name="item-create"),
    path("import/", views.ItemImportView.as_view(), name="item-import"),
    # The preview's own address — a GET here rebuilds the report from the
    # staged file every time, so reloading it is harmless and imports
    # nothing.
    path(
        "import/preview/",
        views.ItemImportPreviewView.as_view(),
        name="item-import-preview",
    ),
    # Discards the staged file and returns to an empty form.
    path(
        "import/restart/",
        views.ItemImportRestartView.as_view(),
        name="item-import-restart",
    ),
    # The preview's own confirm control — a distinct route, not a second
    # branch on "import/", so the staged file's token and format are the
    # only thing that ever says which upload this POST means.
    path(
        "import/confirm/",
        views.ItemImportConfirmView.as_view(),
        name="item-import-confirm",
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

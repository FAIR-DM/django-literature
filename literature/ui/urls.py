"""URL configuration for the opt-in front end.

Nothing is mounted automatically — the host includes this module at whatever
prefix it chooses.

The three routes bind to a placeholder view rather than importing
``literature.ui.views``: that module is filled in incrementally, one class
per story (``ItemListView`` by US-1, ``ItemDetailView`` by US-2,
``ContributorDetailView`` by US-4), and none of them exist yet in the
foundational phase this module ships in. Routing is this app's contract
(FR-003, FR-019, FR-032) and is owned once, here; each story swaps its own
placeholder for the real view when it lands.
"""

from django.urls import path
from django.views.generic import View

app_name = "literature"

urlpatterns = [
    path("", View.as_view(), name="item-list"),
    path("<int:pk>/", View.as_view(), name="item-detail"),
    path("contributors/<int:pk>/", View.as_view(), name="contributor-detail"),
]

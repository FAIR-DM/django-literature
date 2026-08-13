"""URL configuration for the opt-in front end.

Nothing is mounted automatically — the host includes this module at whatever
prefix it chooses.

Routes were filled in incrementally, one class per story (``ItemListView`` by
US-1, ``ItemDetailView`` by US-2, ``ContributorDetailView`` by US-4,
``ItemCreateView`` by US-1 again). The relative import below reaches only
within ``literature.ui`` itself, so it carries none of the import-time risk
an absolute ``literature.*`` import would (see ``literature/ui/apps.py``).
Routing is this app's contract (FR-003, FR-019, FR-032) and is owned once,
here.

``item-update`` and ``item-delete`` are not registered yet — ``ItemUpdateView``
and ``ItemDeleteView`` are separate stories' own tasks; each adds its own
route alongside its view, the same way this one does.
"""

from django.urls import path

from . import views

app_name = "literature"

urlpatterns = [
    path("", views.ItemListView.as_view(), name="item-list"),
    path("add/", views.ItemCreateView.as_view(), name="item-create"),
    path("<int:pk>/", views.ItemDetailView.as_view(), name="item-detail"),
    path("contributors/<int:pk>/", views.ContributorDetailView.as_view(), name="contributor-detail"),
]

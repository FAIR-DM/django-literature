"""URL configuration for the opt-in front end.

Nothing is mounted automatically — the host includes this module at whatever
prefix it chooses.

Routes were filled in incrementally, one class per story (``ItemListView`` by
US-1, ``ItemDetailView`` by US-2, ``ContributorDetailView`` by US-4,
``ItemCreateView`` by US-1 again, ``ItemUpdateView`` by US-2 again,
``ItemDeleteView`` by US-3). The relative import below reaches only within
``literature.ui`` itself, so it carries none of the import-time risk an
absolute ``literature.*`` import would (see ``literature/ui/apps.py``).
Routing is this app's contract (FR-003, FR-019, FR-032) and is owned once,
here.
"""

from django.urls import path

from . import views

app_name = "literature"

urlpatterns = [
    path("", views.ItemTableView.as_view(), name="item-list"),
    path("add/", views.ItemCreateView.as_view(), name="item-create"),
    path("<int:pk>/", views.ItemDetailView.as_view(), name="item-detail"),
    path("<int:pk>/update/", views.ItemUpdateView.as_view(), name="item-update"),
    path("<int:pk>/delete/", views.ItemDeleteView.as_view(), name="item-delete"),
    path("contributors/<int:pk>/", views.ContributorDetailView.as_view(), name="contributor-detail"),
]

"""URL configuration for the opt-in front end.

Nothing is mounted automatically — the host includes this module at whatever
prefix it chooses.

Routes are filled in incrementally, one class per story (``ItemListView`` by
US-1, ``ItemDetailView`` by US-2, ``ContributorDetailView`` by US-4); a route
whose view does not exist yet binds to a placeholder. The relative import
below reaches only within ``literature.ui`` itself, so it carries none of the
import-time risk an absolute ``literature.*`` import would (see
``literature/ui/apps.py``). Routing is this app's contract (FR-003, FR-019,
FR-032) and is owned once, here; each story swaps its own placeholder for the
real view when it lands.
"""

from django.urls import path
from django.views.generic import View

from . import views

app_name = "literature"

urlpatterns = [
    path("", views.ItemListView.as_view(), name="item-list"),
    path("<int:pk>/", views.ItemDetailView.as_view(), name="item-detail"),
    path("contributors/<int:pk>/", View.as_view(), name="contributor-detail"),
]

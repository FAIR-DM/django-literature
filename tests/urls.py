"""URL configuration for the literature test suite."""

from django.urls import include, path

from literature.ui.views import ItemListView

urlpatterns = [
    path("catalogue/", include("literature.ui.urls")),
    # The catalogue route above now serves the table (plan.md D-1, T010).
    # The card view stays a routable public class with no change of its
    # own, and this is the honest test of FR-022: it exercises the exact
    # routing change the documentation tells a project to make (plan.md
    # D-11, research R10).
    path("catalogue/cards/", ItemListView.as_view(), name="item-list-cards"),
]

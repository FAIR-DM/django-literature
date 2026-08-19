"""URL configuration for the literature test suite."""

from django.urls import include, path

from literature.ui.views import ItemListView

urlpatterns = [
    path("catalogue/", include("literature.ui.urls")),
    # The catalogue route above serves whichever view is configured, the
    # table by default (plan.md D-1, T010). This second route pins the card
    # view directly, so the list behaviour both presentations owe can be
    # asserted against each of them in one parametrized test without
    # re-reading the setting. Choosing the card list the way a project
    # actually does — LITERATURE["CATALOGUE_VIEW"] — is asserted against the
    # real catalogue route in tests/test_ui/test_catalogue.py.
    path("catalogue/cards/", ItemListView.as_view(), name="item-list-cards"),
]

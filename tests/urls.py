"""URL configuration for the literature test suite."""

from django.urls import include, path

from literature.ui.views import ItemListView

urlpatterns = [
    path("catalogue/", include("literature.ui.urls")),
    # Pins the card view directly, so shared list behaviour can be tested
    # against both presentations without re-reading LITERATURE["CATALOGUE_VIEW"]
    # (FS-009). That setting itself is covered in tests/test_ui/test_catalogue.py.
    path("catalogue/cards/", ItemListView.as_view(), name="item-list-cards"),
]

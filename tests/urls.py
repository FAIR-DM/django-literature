"""URL configuration for the literature test suite."""

from django.urls import include, path

urlpatterns = [
    path("catalogue/", include("literature.ui.urls")),
]

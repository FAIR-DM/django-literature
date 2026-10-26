"""A URL configuration that mounts the front end somewhere other than ``catalogue/``."""

from django.urls import include, path

urlpatterns = [
    path("refs/", include("literature.ui.urls")),
]

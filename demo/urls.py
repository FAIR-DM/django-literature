"""URL configuration for the demo project."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("catalogue/", include("literature.ui.urls")),
    # django-mvp's mobile footer menu declares a "home" item pointing at a view named
    # "home" (mvp/menus.py:146), and the shell renders that menu on every page. Without
    # a route of that name, django-flex-menus writes a reversal failure to stderr on
    # every render and serves a dead Home button, and the demo's own root address —
    # the first thing anyone opening a server tries — returns 404 (decisions.md D9).
    path("", RedirectView.as_view(pattern_name="literature:item-list"), name="home"),
]

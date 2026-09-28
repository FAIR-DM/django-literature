"""URL configuration for the demo project."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("catalogue/", include("literature.ui.urls")),
    # django-mvp's mobile footer menu (rendered on every page) points at a view named
    # "home" (mvp/menus.py:146); without this route every render logs a reversal
    # failure and the demo's own root address 404s (FS-007).
    path("", RedirectView.as_view(pattern_name="literature:item-list"), name="home"),
]

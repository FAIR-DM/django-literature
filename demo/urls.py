"""URL configuration for the demo project."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("catalogue/", include("literature.ui.urls")),
    # django-mvp's mobile footer menu points at a view named "home"; without it every
    # render logs a reversal failure and the root address 404s (FS-007).
    path("", RedirectView.as_view(pattern_name="literature:item-list"), name="home"),
]

if settings.LIVE_RELOAD:
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]

"""Which view serves the catalogue route, and how a project changes it.

The route is ``literature:item-list`` and it serves the table (FR-021). A
project that prefers the card presentation names ``ItemListView`` under the
namespaced ``LITERATURE`` setting the package already uses for its format
registry::

    LITERATURE = {"CATALOGUE_VIEW": "literature.ui.views.ItemListView"}

A dotted path rather than a two-value switch, for the same reason
``BIB_FORMATS`` takes one: a project that has subclassed either view to add
a column or change a page size can name its own class and keep every other
route, breadcrumb and redirect pointing at ``literature:item-list``
unchanged.

Resolved per request rather than at import time. Every route in this app is
registered through one ``include()`` under one namespace, so a second
``include()`` overriding a single route breaks ``reverse()`` for the rest of
them — the route has to stay where it is and choose its view behind the
name. Reading the setting when the request arrives is also what makes the
choice testable with ``override_settings`` and independent of whether the
host's ``urls.py`` imported this module before or after it configured
settings.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

#: Served with no configuration (FR-021).
DEFAULT_CATALOGUE_VIEW = "literature.ui.views.ItemTableView"


def catalogue_view_class():
    """The view class the catalogue route serves.

    Raises :class:`~django.core.exceptions.ImproperlyConfigured`, naming the
    setting, for a path that does not import or that imports to something
    which cannot serve a request — checked here rather than surfacing later
    as a raw ``AttributeError`` from inside URL resolution, a long way from
    the setting that caused it. Same grounds as
    ``literature.importers.config``, which validates the shape of the
    ``LITERATURE`` dict identically.
    """
    configured = getattr(settings, "LITERATURE", {})
    if not isinstance(configured, dict):
        raise ImproperlyConfigured(
            _("LITERATURE must be a dict, not {actual} — the catalogue view goes under a 'CATALOGUE_VIEW' key.").format(
                actual=type(configured).__name__
            )
        )
    path = configured.get("CATALOGUE_VIEW", DEFAULT_CATALOGUE_VIEW)
    if not isinstance(path, str):
        raise ImproperlyConfigured(
            _("LITERATURE['CATALOGUE_VIEW'] must be a dotted path to a view class, not {actual}: {value!r}").format(
                actual=type(path).__name__, value=path
            )
        )
    try:
        view_class = import_string(path)
    except ImportError as exc:
        raise ImproperlyConfigured(
            _("'{path}' in LITERATURE['CATALOGUE_VIEW'] could not be imported: {error}").format(path=path, error=exc)
        ) from exc
    if not (isinstance(view_class, type) and hasattr(view_class, "as_view")):
        raise ImproperlyConfigured(
            _("'{path}' in LITERATURE['CATALOGUE_VIEW'] is not a class-based view.").format(path=path)
        )
    return view_class


def catalogue(request, *args, **kwargs):
    """Serve the catalogue route through whichever view is configured."""
    return catalogue_view_class().as_view()(request, *args, **kwargs)

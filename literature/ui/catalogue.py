"""Which view serves the catalogue route, and how a project changes it."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

#: Served with no configuration.
DEFAULT_CATALOGUE_VIEW = "literature.ui.views.ItemTableView"


def catalogue_view_class():
    """Return the view class the catalogue route serves (FS-009, #87).

    The route is ``literature:item-list`` and serves the table by default. A
    project names ``ItemListView`` or a subclass of either view as a dotted
    path under ``LITERATURE["CATALOGUE_VIEW"]``::

        LITERATURE = {"CATALOGUE_VIEW": "literature.ui.views.ItemListView"}

    The setting is read per request, not at import time. All routes share one
    ``include()`` and namespace, so overriding one route would break
    ``reverse()`` for the rest; the view is chosen behind the name instead,
    which also keeps it testable with ``override_settings``.

    Returns:
        The configured view class, or the table view when none is configured.

    Raises:
        ImproperlyConfigured: ``LITERATURE`` is not a dict, or the path is not
            a string, does not import, or is not a class-based view. Raised
            here so the setting is named, not as an ``AttributeError`` from
            inside URL resolution.
    """
    configured = getattr(settings, "LITERATURE", {})
    if not isinstance(configured, dict):
        raise ImproperlyConfigured(
            _(
                "LITERATURE must be a dict, not {actual} — the catalogue view goes under a 'CATALOGUE_VIEW' key."
            ).format(actual=type(configured).__name__)
        )
    path = configured.get("CATALOGUE_VIEW", DEFAULT_CATALOGUE_VIEW)
    if not isinstance(path, str):
        raise ImproperlyConfigured(
            _(
                "LITERATURE['CATALOGUE_VIEW'] must be a dotted path to a view class, not {actual}: {value!r}"
            ).format(actual=type(path).__name__, value=path)
        )
    try:
        view_class = import_string(path)
    except ImportError as exc:
        raise ImproperlyConfigured(
            _(
                "'{path}' in LITERATURE['CATALOGUE_VIEW'] could not be imported: {error}"
            ).format(path=path, error=exc)
        ) from exc
    if not (isinstance(view_class, type) and hasattr(view_class, "as_view")):
        raise ImproperlyConfigured(
            _(
                "'{path}' in LITERATURE['CATALOGUE_VIEW'] is not a class-based view."
            ).format(path=path)
        )
    return view_class


def catalogue(request, *args, **kwargs):
    """Serve the catalogue route through whichever view is configured.

    Args:
        request: The incoming request.
        *args: Positional URL arguments, passed to the view.
        **kwargs: Keyword URL arguments, passed to the view.

    Returns:
        The configured view's response.
    """
    return catalogue_view_class().as_view()(request, *args, **kwargs)

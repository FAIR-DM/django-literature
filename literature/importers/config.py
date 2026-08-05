"""The formats an installation can read, declared in Django settings.

See contracts/importers.md "The registry" and data-model.md "The registry".
``LITERATURE = {"BIB_FORMATS": [...]}`` lists dotted import paths, one
namespaced setting per the family convention (``EASY_ICONS`` in
django-easy-icons, not a flat ``LITERATURE_BIB_FORMATS`` key). Resolved on
first read and cached — not at import time, so nothing here runs before the
app registry is ready, and not per call, so enumerating twice does not
re-import every configured module.
"""

from types import MappingProxyType
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from literature.importers.base import BibFormat
from literature.importers.exceptions import UnknownFormat

#: The formats this package ships, so the built-in behaviour needs no
#: configuration (Article X, FR-003). BibTeX landed with #22; RIS with #23.
DEFAULTS: tuple[str, ...] = (
    "literature.importers.bibtex.BibTeXFormat",
    "literature.importers.ris.RISFormat",
)

_cache: MappingProxyType[str, type[BibFormat]] | None = None


def _resolve() -> dict[str, type[BibFormat]]:
    """Import every path in ``LITERATURE["BIB_FORMATS"]`` and key it by name.

    Raises :class:`~django.core.exceptions.ImproperlyConfigured`, naming the
    offending entry, for a path that does not import, or that imports to
    something which is not a usable ``BibFormat`` subclass — checked here
    rather than left to fail later as a raw ``TypeError`` or ``AttributeError``
    from inside somebody's import run, a long way from the setting that
    caused it. The shape of the setting itself is checked on the same
    grounds: most Django list settings are bare lists, so writing
    ``LITERATURE = [...]`` or ``{"BIB_FORMATS": "one.path"}`` is a plausible
    slip, and neither should surface as a raw ``AttributeError`` or as a
    complaint about a one-character import path.
    """
    configured = getattr(settings, "LITERATURE", {})
    if not isinstance(configured, dict):
        raise ImproperlyConfigured(
            _("LITERATURE must be a dict, not {actual} — the format list goes under a 'BIB_FORMATS' key.").format(
                actual=type(configured).__name__
            )
        )
    paths = configured.get("BIB_FORMATS", DEFAULTS)
    if isinstance(paths, str | bytes) or not isinstance(paths, list | tuple):
        raise ImproperlyConfigured(
            _("LITERATURE['BIB_FORMATS'] must be a list of dotted paths, not {actual}: {value!r}").format(
                actual=type(paths).__name__, value=paths
            )
        )
    resolved: dict[str, type[BibFormat]] = {}
    for path in paths:
        try:
            format_class = import_string(path)
        except ImportError as exc:
            raise ImproperlyConfigured(
                _("'{path}' in LITERATURE['BIB_FORMATS'] could not be imported: {error}").format(path=path, error=exc)
            ) from exc
        if not (isinstance(format_class, type) and issubclass(format_class, BibFormat)):
            raise ImproperlyConfigured(
                _("'{path}' in LITERATURE['BIB_FORMATS'] is not a BibFormat subclass.").format(path=path)
            )
        missing = sorted(format_class.__abstractmethods__)
        if missing:
            raise ImproperlyConfigured(
                _("'{path}' in LITERATURE['BIB_FORMATS'] does not implement {missing} and cannot be used.").format(
                    path=path, missing=", ".join(missing)
                )
            )
        name = getattr(format_class, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise ImproperlyConfigured(
                _("'{path}' in LITERATURE['BIB_FORMATS'] must set a non-empty 'name'.").format(path=path)
            )
        resolved[name] = format_class
    return resolved


def available_formats() -> MappingProxyType[str, type[BibFormat]]:
    """The configured set, keyed by name — enumerable without knowing what is
    in it (FR-017). Read-only: nothing but a setting change can alter it.
    """
    global _cache
    if _cache is None:
        _cache = MappingProxyType(_resolve())
    return _cache


def get_format(name: str) -> type[BibFormat]:
    """Return the format configured under ``name``.

    Raises :class:`~literature.importers.exceptions.UnknownFormat`, naming
    the formats that *are* configured (FR-019).
    """
    formats = available_formats()
    try:
        return formats[name]
    except KeyError:
        raise UnknownFormat(name, available=formats.keys()) from None


def _reset_cache_on_setting_change(*, setting: str, **kwargs: Any) -> None:
    """Drop the cached mapping when ``LITERATURE`` changes.

    Without this, ``override_settings``/the ``settings`` fixture would leak
    one test's configured formats into the next: the cache is module-level
    state, and nothing else would ever invalidate it.
    """
    if setting == "LITERATURE":
        global _cache
        _cache = None


setting_changed.connect(_reset_cache_on_setting_change)

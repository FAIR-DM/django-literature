"""The formats an installation can read, declared in Django settings.

``LITERATURE = {"BIB_FORMATS": [...]}`` lists dotted import paths. The list is
resolved on first read and cached: not at import time, so nothing here runs
before the app registry is ready, and not per call, so enumerating twice does
not re-import every configured module.
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
#: configuration.
DEFAULTS: tuple[str, ...] = (
    "literature.importers.bibtex.BibTeXFormat",
    "literature.importers.ris.RISFormat",
)

_cache: MappingProxyType[str, type[BibFormat]] | None = None


def _resolve() -> dict[str, type[BibFormat]]:
    """Import every path in ``LITERATURE["BIB_FORMATS"]`` and key it by name.

    Everything is checked here, so a bad setting fails naming the offending
    entry rather than as a raw ``TypeError`` or ``AttributeError`` deep inside
    somebody's import run. That includes the setting's own shape: most Django
    list settings are bare lists, so ``LITERATURE = [...]`` or
    ``{"BIB_FORMATS": "one.path"}`` is a plausible slip.

    Returns:
        Each configured format class, keyed by its ``name``.

    Raises:
        ImproperlyConfigured: The setting is the wrong shape, or a path does
            not import to a concrete ``BibFormat`` subclass with a ``name``.
    """
    configured = getattr(settings, "LITERATURE", {})
    if not isinstance(configured, dict):
        raise ImproperlyConfigured(
            _(
                "LITERATURE must be a dict, not {actual} — the format list goes under a 'BIB_FORMATS' key."
            ).format(actual=type(configured).__name__)
        )
    paths = configured.get("BIB_FORMATS", DEFAULTS)
    if isinstance(paths, str | bytes) or not isinstance(paths, list | tuple):
        raise ImproperlyConfigured(
            _(
                "LITERATURE['BIB_FORMATS'] must be a list of dotted paths, not {actual}: {value!r}"
            ).format(actual=type(paths).__name__, value=paths)
        )
    resolved: dict[str, type[BibFormat]] = {}
    for path in paths:
        try:
            format_class = import_string(path)
        except ImportError as exc:
            raise ImproperlyConfigured(
                _(
                    "'{path}' in LITERATURE['BIB_FORMATS'] could not be imported: {error}"
                ).format(path=path, error=exc)
            ) from exc
        if not (isinstance(format_class, type) and issubclass(format_class, BibFormat)):
            raise ImproperlyConfigured(
                _(
                    "'{path}' in LITERATURE['BIB_FORMATS'] is not a BibFormat subclass."
                ).format(path=path)
            )
        missing = sorted(format_class.__abstractmethods__)
        if missing:
            raise ImproperlyConfigured(
                _(
                    "'{path}' in LITERATURE['BIB_FORMATS'] does not implement {missing} and cannot be used."
                ).format(path=path, missing=", ".join(missing))
            )
        name = getattr(format_class, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise ImproperlyConfigured(
                _(
                    "'{path}' in LITERATURE['BIB_FORMATS'] must set a non-empty 'name'."
                ).format(path=path)
            )
        resolved[name] = format_class
    return resolved


def available_formats() -> MappingProxyType[str, type[BibFormat]]:
    """Return every configured format, keyed by name.

    Read-only: nothing but a setting change can alter it.

    Returns:
        A read-only mapping of name to format class.
    """
    global _cache
    if _cache is None:
        _cache = MappingProxyType(_resolve())
    return _cache


def get_format(name: str) -> type[BibFormat]:
    """Return the format configured under ``name``.

    Args:
        name: The format's registered name, such as ``"bibtex"``.

    Returns:
        The format class.

    Raises:
        UnknownFormat: Nothing is configured under ``name``. The message names
            the formats that are.
    """
    formats = available_formats()
    try:
        return formats[name]
    except KeyError:
        raise UnknownFormat(name, available=formats.keys()) from None


def _reset_cache_on_setting_change(*, setting: str, **kwargs: Any) -> None:
    """Drop the cached mapping when ``LITERATURE`` changes.

    Without this, ``override_settings`` would leak one test's configured
    formats into the next, since nothing else invalidates the module-level
    cache.

    Args:
        setting: The name of the setting that changed.
        **kwargs: The rest of the ``setting_changed`` signal's arguments.
    """
    if setting == "LITERATURE":
        global _cache
        _cache = None


setting_changed.connect(_reset_cache_on_setting_change)

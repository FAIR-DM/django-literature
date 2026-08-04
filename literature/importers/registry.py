"""The format registry: named formats a caller can use without knowing them.

See contracts/importers.md "The registry" and data-model.md "The registry".
Module-level state, populated only by explicit registration — empty until a
real format registers itself (data-model.md: "Empty until #22").
"""

from types import MappingProxyType

from django.utils.translation import gettext_lazy as _

from literature.importers.base import BibFormat
from literature.importers.exceptions import FormatAlreadyRegistered, UnknownFormat

_registry: dict[str, type[BibFormat]] = {}


def register(format_class: type[BibFormat]) -> type[BibFormat]:
    """Register ``format_class`` under its ``name``. Returns it, so it can sit
    above a class as a decorator.

    Raises :class:`~literature.importers.exceptions.FormatAlreadyRegistered`
    rather than replacing an existing entry (FR-020) — silently shadowing
    another package's format is the kind of failure that surfaces days later
    as "the wrong parser ran".

    Raises ``TypeError`` for anything that is not a ``BibFormat`` subclass with a
    name (contracts/importers.md: the contract raises for programmer error,
    "an unregistered format name, or something that is not a ``BibFormat``").
    Checked here rather than left to fail later, because the alternative is an
    ``AttributeError`` from inside somebody's import run, a long way from the
    registration that caused it.
    """
    if not (isinstance(format_class, type) and issubclass(format_class, BibFormat)):
        raise TypeError(f"{format_class!r} is not a BibFormat subclass")
    name = getattr(format_class, "name", None)
    if not isinstance(name, str) or not name.strip():
        raise TypeError(f"{format_class.__name__} must set a non-empty 'name' before it can be registered")
    missing = sorted(getattr(format_class, "__abstractmethods__", ()))
    if missing:
        raise TypeError(
            f"{format_class.__name__} does not implement {', '.join(missing)} and cannot be registered as a format"
        )
    if name in _registry:
        raise FormatAlreadyRegistered(_("A format is already registered under '{name}'.").format(name=name))
    _registry[name] = format_class
    return format_class


def get_format(name: str) -> type[BibFormat]:
    """Return the format registered under ``name``.

    Raises :class:`~literature.importers.exceptions.UnknownFormat`, naming
    the formats that *are* registered (FR-019).
    """
    try:
        return _registry[name]
    except KeyError:
        raise UnknownFormat(name, available=_registry.keys()) from None


def available_formats() -> MappingProxyType[str, type[BibFormat]]:
    """The registered set, keyed by name — enumerable without knowing what is
    in it (FR-017). Read-only: only :func:`register` mutates the registry.
    """
    return MappingProxyType(_registry)

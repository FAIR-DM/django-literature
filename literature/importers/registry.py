"""The format registry: named formats a caller can use without knowing them.

See contracts/importers.md "The registry" and data-model.md "The registry".
Module-level state, populated only by explicit registration — empty until a
real format registers itself (data-model.md: "Empty until #22").
"""

from types import MappingProxyType

from django.utils.translation import gettext_lazy as _

from literature.importers.base import Format
from literature.importers.exceptions import FormatAlreadyRegistered, UnknownFormat

_registry: dict[str, type[Format]] = {}


def register(format_class: type[Format]) -> type[Format]:
    """Register ``format_class`` under its ``name``. Returns it, so it can sit
    above a class as a decorator.

    Raises :class:`~literature.importers.exceptions.FormatAlreadyRegistered`
    rather than replacing an existing entry (FR-020) — silently shadowing
    another package's format is the kind of failure that surfaces days later
    as "the wrong parser ran".
    """
    name = format_class.name
    if name in _registry:
        raise FormatAlreadyRegistered(_("A format is already registered under '{name}'.").format(name=name))
    _registry[name] = format_class
    return format_class


def get_format(name: str) -> type[Format]:
    """Return the format registered under ``name``.

    Raises :class:`~literature.importers.exceptions.UnknownFormat`, naming
    the formats that *are* registered (FR-019).
    """
    try:
        return _registry[name]
    except KeyError:
        raise UnknownFormat(name, available=_registry.keys()) from None


def available_formats() -> MappingProxyType[str, type[Format]]:
    """The registered set, keyed by name — enumerable without knowing what is
    in it (FR-017). Read-only: only :func:`register` mutates the registry.
    """
    return MappingProxyType(_registry)

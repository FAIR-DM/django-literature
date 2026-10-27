"""Reading bibliographic files into the catalogue: the import contract's public names (FS-003)."""

# Re-exported here so callers never import a submodule. ``literature/__init__.py`` stays
# empty: it loads before the app registry is ready, and a re-export reaching the models
# would raise AppRegistryNotReady at startup.

from literature.importers.base import BibFormat
from literature.importers.bibtex import BibTeXFormat
from literature.importers.config import available_formats, get_format
from literature.importers.exceptions import (
    EntryError,
    ImporterError,
    ParseError,
    SkipEntry,
    UnknownFormat,
)
from literature.importers.results import EntryResult, ImportResult, Outcome
from literature.importers.ris import RISEntry, RISFormat, RISParser

__all__ = [
    "BibFormat",
    "BibTeXFormat",
    "EntryError",
    "EntryResult",
    "ImportResult",
    "ImporterError",
    "Outcome",
    "ParseError",
    "RISEntry",
    "RISFormat",
    "RISParser",
    "SkipEntry",
    "UnknownFormat",
    "available_formats",
    "get_format",
]

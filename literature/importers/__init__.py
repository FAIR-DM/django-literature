"""Reading bibliographic files into the catalogue.

``import_file`` is a method on every :class:`~literature.importers.base.BibFormat`,
so running one starts from the format itself:

.. code-block:: python

    from literature.importers import get_format

    with open("library.bib") as handle:
        result = get_format("bibtex")().import_file(handle)

    for entry in result.failed:
        print(entry.index, entry.handle, entry.reason)

Every public name in this contract is reached from here, so a caller never has
to import a submodule (research.md R3 — ``literature/__init__.py`` stays empty,
because a Django app's top-level ``__init__`` is imported before the app
registry is populated and re-exporting anything that reaches the models would
raise ``AppRegistryNotReady`` at startup).

Ships with BibTeX (:class:`~literature.importers.bibtex.BibTeXFormat`) and RIS
(:class:`~literature.importers.ris.RISFormat`). Which formats an installation
can read is declared in the ``LITERATURE`` setting — see
:mod:`literature.importers.config`.

See ``specs/003-import-contract/contracts/importers.md`` for the full contract.
"""

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

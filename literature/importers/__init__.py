"""Reading bibliographic files into the catalogue.

One call, four fixed stages, one result:

.. code-block:: python

    from literature.importers import import_file

    with open("library.bib") as handle:
        result = import_file(handle, format="bibtex")

    for entry in result.failed:
        print(entry.index, entry.handle, entry.reason)

Every public name in this contract is reached from here, so a caller never has
to import a submodule (research.md R3 — ``literature/__init__.py`` stays empty,
because a Django app's top-level ``__init__`` is imported before the app
registry is populated and re-exporting anything that reaches the models would
raise ``AppRegistryNotReady`` at startup).

Ships with no format of its own: BibTeX and RIS arrive later. A format is only
registered once the module defining it has been imported, so a package adding
one imports it from here or from its app's ``ready()`` — see
:mod:`literature.importers.registry`.

See ``specs/003-import-contract/contracts/importers.md`` for the full contract.
"""

from literature.importers.base import Format
from literature.importers.exceptions import (
    EntryError,
    FormatAlreadyRegistered,
    ImporterError,
    ParseError,
    SkipEntry,
    UnknownFormat,
)
from literature.importers.registry import available_formats, get_format, register
from literature.importers.results import EntryResult, ImportResult, Outcome
from literature.importers.runner import import_file

__all__ = [
    "EntryError",
    "EntryResult",
    "Format",
    "FormatAlreadyRegistered",
    "ImportResult",
    "ImporterError",
    "Outcome",
    "ParseError",
    "SkipEntry",
    "UnknownFormat",
    "available_formats",
    "get_format",
    "import_file",
    "register",
]

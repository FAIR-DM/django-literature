"""Exceptions used by the import contract.

Two audiences, deliberately separated:

- ``SkipEntry``, ``EntryError`` and ``ParseError`` are how a format talks to the
  runner about one entry or one file. The runner turns each into an outcome, and
  none of them reaches the caller of :func:`~literature.importers.import_file`.
- ``UnknownFormat`` and ``FormatAlreadyRegistered`` are programmer error rather
  than anything to do with file content, so they do reach the caller.

Keeping them in one hierarchy but on separate branches is what stops a caller's
``except`` clause around an import from swallowing an entry-level signal.
"""

from django.utils.translation import gettext_lazy as _


class ImporterError(Exception):
    """Root of every exception raised by the import contract."""


# --------------------------------------------------------------------------
# A format's vocabulary — handled by the runner, never seen by a caller
# --------------------------------------------------------------------------


class SkipEntry(ImporterError):
    """This element is recognised but is not a bibliographic record.

    Raised from a format's ``to_csl_json`` for things like a BibTeX ``@comment``
    or an RIS header line. Nothing is stored and nothing is wrong, so the entry
    is reported as skipped rather than failed. The message is optional, since
    skipping is not an error that needs explaining.
    """


class EntryError(ImporterError):
    """This entry cannot be imported, for the reason given.

    Raised from a format's ``parse`` or ``to_csl_json``. The message becomes the
    entry result's reason, so it is read by whoever has to fix the source file
    and should say what is wrong with the entry.
    """


class ParseError(ImporterError):
    """The file cannot be read at all.

    Raised from a format's ``parse`` when nothing useful can be recovered — the
    file is not in this format, is truncated beyond recovery, or is in an
    unreadable encoding. The runner reports it as a single failed entry rather
    than letting it escape.
    """


# --------------------------------------------------------------------------
# The caller's problem — these propagate
# --------------------------------------------------------------------------


class UnknownFormat(ImporterError):
    """No format is registered under the requested name.

    The message names the formats that *are* registered, because the useful
    reply to "bibtex is not a format" is the list of things that are.
    """

    def __init__(self, name, available=()):
        self.name = name
        self.available = sorted(available)
        if self.available:
            message = _("No import format named '{name}'. Registered formats: {available}.").format(
                name=name,
                available=", ".join(self.available),
            )
        else:
            message = _("No import format named '{name}'. No import formats are registered.").format(name=name)
        super().__init__(message)


class FormatAlreadyRegistered(ImporterError):
    """Something is already registered under that name.

    Registration fails rather than replacing the existing entry: silently
    shadowing another package's format surfaces days later as "the wrong parser
    ran", which is far harder to diagnose than an error at import time.
    """

"""Exceptions used by the import contract.

Two audiences, deliberately separated:

- ``SkipEntry``, ``EntryError`` and ``ParseError`` are how a format talks to its
  own workflow methods about one entry or one file. ``import_entry`` and
  ``import_entries`` (base.py) turn each into an outcome, and none of them
  reaches the caller of :meth:`~literature.importers.base.BibFormat.import_file`.
- ``UnknownFormat`` is programmer error rather than anything to do with file
  content, so it does reach the caller.

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
    """No format is configured under the requested name.

    The message names the formats that *are* configured, because the useful
    reply to "bibtex is not a format" is the list of things that are.
    """

    def __init__(self, name, available=()):
        self.name = name
        self.available = sorted(available)
        if self.available:
            message = _("No import format named '{name}'. Configured formats: {available}.").format(
                name=name,
                available=", ".join(self.available),
            )
        else:
            message = _("No import format named '{name}'. No import formats are configured.").format(name=name)
        super().__init__(message)

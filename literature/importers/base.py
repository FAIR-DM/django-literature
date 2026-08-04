"""The format contract: what a bibliographic file syntax plugs in as, and the
workflow it gets for free.

See contracts/importers.md for the full contract. A format supplies only the
file-to-entries and entry-to-CSL-JSON stages (FR-003); everything else —
looping over entries, storing one, and building the report — is provided by
this class as ordinary, overridable methods. A format that implements only
the two required stages gets correct behaviour; a format with an unusual
need is free to replace any of the others. Nothing here tries to prevent
that: the maintainer's ruling was that this base class only has to get the
job done when its instructions are followed, not police what a subclass
chooses to do with them.
"""

import abc
import contextlib
import logging
from collections.abc import Iterator
from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import router, transaction
from django.utils.functional import Promise
from django.utils.translation import gettext as _

from literature.converters import from_csl_json
from literature.importers.exceptions import SkipEntry
from literature.importers.results import EntryResult, ImportResult, Outcome

logger = logging.getLogger(__name__)


def _reason_for(exc: Exception) -> str:
    """The message to put in front of whoever has to fix the source file.

    Three things go wrong if this is left as ``str(exc)``:

    - ``str(ValidationError)`` is the ``repr`` of its internal list or dict, so
      a reader gets ``["Unknown CSL JSON item type: 'thesis'"]`` — brackets,
      quotes and all — rather than the sentence inside it.
    - An exception raised with no message at all gives the empty string, and an
      entry reported as failed with nothing to act on is the silent drop this
      contract exists to remove.
    - An exception that is not part of the contract's vocabulary says nothing
      about itself unless its type is named.
    """
    from literature.importers.exceptions import EntryError, ParseError

    text = "; ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
    text = text.strip()
    if text and isinstance(exc, EntryError | ParseError | ValidationError):
        return text
    if text:
        # Not part of the contract's vocabulary: a format's own bug, or a
        # shape of CSL JSON the conversion could not handle. Name the type,
        # since that is the only lead whoever reads the report has.
        return _("{error}: {message}").format(error=type(exc).__name__, message=text)
    return _("{error} (no further detail)").format(error=type(exc).__name__)


class BibFormat(abc.ABC):
    """A plug-in for one bibliographic file syntax, such as BibTeX or RIS.

    Named under :attr:`name` and reachable through
    :func:`~literature.importers.config.get_format` once listed in the
    ``LITERATURE`` setting. A subclass supplies :meth:`parse` and
    :meth:`to_csl_json`, and optionally :meth:`handle_for`; every other
    method here drives the workflow those two stages plug into, and is free
    to be overridden by a format with an unusual need (FR-003).
    """

    #: The name a caller runs an import under, and the key the ``LITERATURE``
    #: setting resolves. Machine-facing, so never translated.
    name: ClassVar[str]

    #: The human-readable label. Widened to accept a lazy string 2026-08-04,
    #: when the first concrete format (#22) tried to translate its own label
    #: and mypy refused: ``ClassVar[str]`` forbade exactly the
    #: ``gettext_lazy`` that Article VIII makes non-negotiable, and that
    #: ``Outcome`` already uses for its own labels. A type widening only —
    #: nothing about the contract's behaviour changes.
    label: ClassVar[str | Promise]

    @abc.abstractmethod
    def parse(self, file) -> Iterator[Any]:
        """Yield this file's raw entries one at a time.

        An iterator, not a list — FR-024 depends on it, and returning a
        list would quietly make one-at-a-time consumption unmeetable from
        outside the format.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def to_csl_json(self, raw: Any) -> dict[str, Any]:
        """Turn one raw entry into a CSL JSON dict.

        Raise :class:`~literature.importers.exceptions.SkipEntry` for an
        element the format recognises but that is not a bibliographic
        record, or :class:`~literature.importers.exceptions.EntryError` for
        one that is bad. A :class:`~django.core.exceptions.ValidationError`
        may also be left to escape, whether raised directly or by way of
        ``from_csl_json`` once :meth:`import_entry` calls it with the
        returned dict.
        """
        raise NotImplementedError

    def handle_for(self, raw: Any) -> str | None:
        """The source's own name for this entry, where the syntax has one.

        A BibTeX cite key, an RIS record number. ``None`` by default,
        since not every syntax has one and requiring it would push formats
        into inventing identifiers.
        """
        return None

    def import_file(self, file, *, dry_run: bool = False) -> ImportResult:
        """Import every entry this format finds in ``file`` into the catalogue.

        The one documented way to run an import (FR-001), identical for
        every format unless a subclass chooses to override a step. Opens
        the outer dry-run transaction and drives the rest of the workflow
        through :meth:`import_entries` and :meth:`get_result`.

        Args:
            file: An open file object, or anything with a ``read()``. Never
                opened as a path — passed straight through to :meth:`parse`
                (FR-023).
            dry_run: Run every stage and report every outcome, then leave
                the catalogue exactly as it was (FR-015). Same code path as
                a real run, wrapped in one outer ``transaction.atomic()``
                that is rolled back at the end (research.md R2).

        Returns:
            One :class:`~literature.importers.results.EntryResult` per
            entry this format found, in source order (FR-007).

        Never raises for bad file content: a file that cannot be parsed at
        all comes back as an
        :class:`~literature.importers.results.ImportResult` whose single
        entry failed, with the parser's reason (FR-014).
        """
        from literature.models import Item

        # Every transaction below names the alias the models are actually
        # written on. This package is a reusable app, so a project's
        # ``DATABASE_ROUTERS`` may send ``Item`` somewhere other than
        # ``default`` — and an unqualified ``transaction.atomic()`` would
        # then open a transaction on an idle connection while the writes
        # committed on another, which makes a dry run store rows and report
        # that it stored nothing.
        using = router.db_for_write(Item)

        # The outer transaction exists only for a dry run (contracts/importers.md
        # step 2). Everything below it is the same code that runs in earnest —
        # nothing branches on ``dry_run`` except this wrapper and what
        # ``entry_created`` hands back (data-model.md: a dry run's rows do not
        # survive the rollback, so returning one would look saved and not be).
        outer_transaction = transaction.atomic(using=using) if dry_run else contextlib.nullcontext()

        with outer_transaction:
            entries = self.import_entries(self._parsed(file), dry_run=dry_run)
            if dry_run:
                transaction.set_rollback(True, using=using)

        return self.get_result(entries, dry_run=dry_run)

    def _parsed(self, file) -> Iterator[Any]:
        """Hand ``parse`` its file from inside the loop that protects it.

        ``parse`` is documented as returning an iterator, and a generator
        function does not run a line of its body until it is first iterated —
        so a generator implementation raises inside ``import_entries``'s
        ``try`` and is reported. But most third-party bibliography parsers
        read the whole file up front, and a ``parse`` written around one
        raises the moment it is *called*. Called directly from
        ``import_file`` that lands outside every ``try`` in this class and
        escapes to the caller, against FR-014. Yielding through this
        generator defers the call to the first ``next()``, so both shapes of
        ``parse`` report an unreadable file the same way.
        """
        yield from self.parse(file)

    def import_entries(self, entries: Iterator[Any], *, dry_run: bool) -> list[EntryResult]:
        """Import each raw entry ``parse`` produced, consuming it one at a time.

        Assigns each entry its zero-based index (FR-009) and delegates the
        rest to :meth:`import_entry`. A failure raised by the iterator
        itself — rather than by anything done to one entry — ends the
        file: the entries already recovered are kept, and the failure is
        recorded against the index the generator stopped at (FR-014).
        """
        results: list[EntryResult] = []
        index = 0
        try:
            for raw in entries:
                entry_index = index
                index += 1
                results.append(self.import_entry(raw, entry_index, dry_run=dry_run))
        except SkipEntry:
            # Out of contract — ``SkipEntry`` belongs to ``to_csl_json`` — but
            # a format recognising a trailing non-record while reading is
            # asking for the same thing, and the alternative is filing a
            # deliberate signal as a failure.
            results.append(self.entry_skipped(index=index, handle=None))
        except Exception as exc:
            # A format may report the file as unreadable (``ParseError``),
            # report that the *next* entry is bad before converting it
            # (``EntryError``), or simply have a bug. Either way the
            # generator is finished, so the failure is filed at the index
            # it stopped at.
            logger.warning("Parsing failed at entry %s", index, exc_info=True)
            results.append(self.entry_failed(index=index, handle=None, reason=_reason_for(exc)))
        return results

    def import_entry(self, raw: Any, index: int, *, dry_run: bool) -> EntryResult:
        """Import one raw entry: its handle, its conversion, and its own savepoint.

        Never raises. Anything ``handle_for``, :meth:`to_csl_json`, or the
        stage that stores the entry raises becomes this entry's outcome —
        never a whole-file failure, and never an exception the caller has
        to catch (FR-012, FR-013, FR-023).
        """
        from literature.models import Item

        # ``handle_for`` reads the same untrusted content as ``to_csl_json``
        # (FR-023), but it is only how an entry is *named*. Its own block, so
        # an entry whose handle cannot be read is still converted and stored
        # — reported without a handle rather than turned into a failure, or
        # worse, into whatever outcome the exception it raised happens to mean.
        try:
            handle = self.handle_for(raw)
        except Exception:
            logger.warning("Entry %s: could not read its handle", index, exc_info=True)
            handle = None

        try:
            csl_json = self.to_csl_json(raw)
        except SkipEntry:
            return self.entry_skipped(index=index, handle=handle)
        except Exception as exc:
            # Deliberately every exception, not the contract's three. A
            # format is third-party code reading untrusted content, and
            # ``from_csl_json`` below is not defensive about the *shape* of
            # the CSL JSON it is handed. Narrowing this to the documented
            # types means a malformed entry escapes the workflow entirely,
            # taking the report for every entry with it and leaving the ones
            # already stored committed — the one failure FR-013, FR-014 and
            # FR-023 exist to rule out.
            logger.warning("Entry %s could not be converted", index, exc_info=True)
            return self.entry_failed(index=index, handle=handle, reason=_reason_for(exc))

        using = router.db_for_write(Item)
        try:
            # A savepoint per entry (research.md R2): the exception is
            # caught outside this block, which is what lets the run
            # continue after a database-level failure rather than
            # poisoning the whole transaction. Nested inside the outer
            # dry-run transaction, this savepoint behaves the same way.
            with transaction.atomic(using=using):
                item = from_csl_json(csl_json)
        except Exception as exc:
            logger.warning("Entry %s could not be stored", index, exc_info=True)
            return self.entry_failed(index=index, handle=handle, reason=_reason_for(exc))

        return self.entry_created(index=index, handle=handle, item=item, dry_run=dry_run)

    def get_result(self, entries: list[EntryResult], *, dry_run: bool) -> ImportResult:
        """Build the :class:`~literature.importers.results.ImportResult` for a run.

        The single place a subclass can reshape what a run reports —
        filtering, reordering, or annotating ``entries`` — without touching
        how any individual entry was imported.
        """
        return ImportResult(entries=entries, dry_run=dry_run, format_name=self.name)

    def entry_created(self, *, index: int, handle: str | None, item: Any, dry_run: bool) -> EntryResult:
        """Report one entry as stored.

        ``item`` is dropped on a dry run: its rows live inside a transaction
        that is about to be rolled back, so handing it back would look saved
        and not be (data-model.md).
        """
        return EntryResult(outcome=Outcome.CREATED, index=index, handle=handle, item=None if dry_run else item)

    def entry_skipped(self, *, index: int, handle: str | None) -> EntryResult:
        """Report one entry as recognised but not a bibliographic record."""
        return EntryResult(outcome=Outcome.SKIPPED, index=index, handle=handle)

    def entry_failed(self, *, index: int, handle: str | None, reason: str) -> EntryResult:
        """Report one entry as unable to be stored, with the reason why."""
        return EntryResult(outcome=Outcome.FAILED, index=index, handle=handle, reason=reason)

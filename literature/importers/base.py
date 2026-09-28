"""The base class every bibliographic file format plugs in as.

A format supplies only the file-to-entries and entry-to-CSL-JSON stages. Looping
over entries, storing each one and building the report are ordinary, overridable
methods here, so a format with an unusual need may replace any of them. The base
class does not police what a subclass does with them. The full contract is
``specs/003-import-contract/contracts/importers.md``.
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
    """Return the message to show whoever has to fix the source file.

    Plain ``str(exc)`` goes wrong in three ways:

    - ``str(ValidationError)`` is the ``repr`` of its internal list or dict,
      brackets and quotes included, rather than the sentence inside it.
    - An exception raised with no message gives the empty string, and a failed
      entry with nothing to act on is the silent drop the contract rules out.
    - An exception outside the contract's vocabulary says nothing about itself
      unless its type is named.

    Args:
        exc: The exception an entry or the file failed with.

    Returns:
        A non-empty, human-readable reason.
    """
    from literature.importers.exceptions import EntryError, ParseError

    text = "; ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
    text = text.strip()
    if text and isinstance(exc, EntryError | ParseError | ValidationError):
        return text
    if text:
        # Outside the contract's vocabulary, the type name is the only lead the
        # reader of the report has.
        return _("{error}: {message}").format(error=type(exc).__name__, message=text)
    return _("{error} (no further detail)").format(error=type(exc).__name__)


def _skip_reason(exc: SkipEntry) -> str | None:
    """Return what a format said it skipped, if it said anything.

    Unlike :func:`_reason_for`, a message-less ``SkipEntry`` stays ``None``:
    skipping is not a failure that needs explaining.

    Args:
        exc: The ``SkipEntry`` the format raised.

    Returns:
        The stripped message, or ``None`` when there is none.
    """
    text = str(exc).strip()
    return text or None


class BibFormat(abc.ABC):
    """A plug-in for one bibliographic file syntax, such as BibTeX or RIS.

    Named under :attr:`name` and reachable through
    :func:`~literature.importers.config.get_format` once listed in the
    ``LITERATURE`` setting. A subclass supplies :meth:`parse` and
    :meth:`to_csl_json`, and optionally :meth:`handle_for`. Every other method
    drives the workflow those stages plug into and may be overridden.
    """

    #: The name a caller runs an import under, and the key the ``LITERATURE``
    #: setting resolves. Machine-facing, so never translated.
    name: ClassVar[str]

    #: The human-readable label, which may be a lazy translation.
    label: ClassVar[str | Promise]

    @abc.abstractmethod
    def parse(self, file) -> Iterator[Any]:
        """Yield the raw entries in ``file``, one at a time, in source order.

        ``file`` is the handle passed to :meth:`import_file`. An iterator, not a
        list, so a caller can consume entries without the whole file being
        converted first. Each entry is in whatever shape :meth:`to_csl_json`
        accepts. Raise :class:`~literature.importers.exceptions.ParseError` for
        a file that cannot be read at all.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def to_csl_json(self, raw: Any) -> dict[str, Any]:
        """Turn one raw entry into a CSL JSON dict.

        An implementation raises
        :class:`~literature.importers.exceptions.SkipEntry` for an element that
        is recognised but is not a bibliographic record, and
        :class:`~literature.importers.exceptions.EntryError` for an entry that
        is bad. A :class:`~django.core.exceptions.ValidationError` may also
        escape, whether raised here or by ``from_csl_json`` once
        :meth:`import_entry` stores the returned dict.

        Args:
            raw: One entry :meth:`parse` yielded.

        Returns:
            The entry as CSL JSON.

        Raises:
            NotImplementedError: The format does not implement this stage.
        """
        raise NotImplementedError

    def handle_for(self, raw: Any) -> str | None:
        """Return the source's own name for this entry, where the syntax has one.

        A BibTeX cite key, an RIS record number. Not every syntax has one, and
        requiring it would push formats into inventing identifiers.

        Args:
            raw: One entry :meth:`parse` yielded.

        Returns:
            The handle, or ``None`` by default.
        """
        return None

    def import_file(self, file: Any, *, dry_run: bool = False) -> ImportResult:
        """Import every entry this format finds in ``file`` into the catalogue.

        The one documented way to run an import, identical for every format
        unless a subclass overrides a step. Never raises for bad file content: a
        file that cannot be parsed at all comes back as a result whose single
        entry failed, with the parser's reason.

        Args:
            file: An open file object in text or binary mode, or anything with a
                ``read()`` returning ``str`` or ``bytes``. Never opened as a path
                and never decoded here, since decoding is the format's job
                (ADR-0012).
            dry_run: Run every stage and report every outcome, then roll the
                catalogue back to exactly how it was.

        Returns:
            The run's report, with one entry result per entry this format
            found, in source order.
        """
        from literature.models import Item

        # A project's DATABASE_ROUTERS may send Item away from ``default``; an
        # unqualified atomic() would then roll back an idle connection while the
        # writes committed elsewhere, so a dry run would store rows.
        using = router.db_for_write(Item)

        # The outer transaction exists only for a dry run. Nothing else branches
        # on ``dry_run``, so a dry run exercises exactly the real code path.
        outer_transaction = (
            transaction.atomic(using=using) if dry_run else contextlib.nullcontext()
        )

        with outer_transaction:
            entries = self.import_entries(self._parsed(file), dry_run=dry_run)
            if dry_run:
                transaction.set_rollback(True, using=using)

        return self.get_result(entries, dry_run=dry_run)

    def _parsed(self, file) -> Iterator[Any]:
        """Defer calling ``parse`` until the loop that reports its failures.

        A ``parse`` built on a third-party parser that reads the whole file up
        front raises the moment it is called, not when first iterated. Called
        directly from :meth:`import_file`, that would escape to the caller.
        Yielding through this generator moves the call inside
        :meth:`import_entries`'s ``try``, so an unreadable file is reported the
        same way whichever shape ``parse`` has.
        """
        yield from self.parse(file)

    def import_entries(
        self, entries: Iterator[Any], *, dry_run: bool
    ) -> list[EntryResult]:
        """Import each raw entry, consuming the iterator one entry at a time.

        Assigns each entry its zero-based index and delegates the rest to
        :meth:`import_entry`. A failure raised by the iterator itself ends the
        file: the entries already recovered are kept, and the failure is
        recorded against the index the iterator stopped at.

        Args:
            entries: The raw entries, as :meth:`parse` yields them.
            dry_run: Whether this is a dry run.

        Returns:
            One result per entry, in source order.
        """
        results: list[EntryResult] = []
        index = 0
        try:
            for raw in entries:
                entry_index = index
                index += 1
                results.append(self.import_entry(raw, entry_index, dry_run=dry_run))
        except SkipEntry as exc:
            # Out of contract, since SkipEntry belongs to to_csl_json, but a format
            # recognising a trailing non-record while reading means the same thing.
            results.append(
                self.entry_skipped(index=index, handle=None, reason=_skip_reason(exc))
            )
        except Exception as exc:
            logger.warning("Parsing failed at entry %s", index, exc_info=True)
            results.append(
                self.entry_failed(index=index, handle=None, reason=_reason_for(exc))
            )
        return results

    def import_entry(self, raw: Any, index: int, *, dry_run: bool) -> EntryResult:
        """Import one raw entry inside its own savepoint.

        Never raises. Anything :meth:`handle_for`, :meth:`to_csl_json` or the
        storing stage raises becomes this entry's outcome, never a whole-file
        failure and never an exception the caller has to catch.

        Args:
            raw: One entry :meth:`parse` yielded.
            index: The entry's zero-based position in the file.
            dry_run: Whether this is a dry run.

        Returns:
            The entry's result.
        """
        from literature.models import Item

        # The handle only names the entry, so an unreadable one is reported as
        # missing rather than failing an entry that would otherwise store.
        try:
            handle = self.handle_for(raw)
        except Exception:
            logger.warning("Entry %s: could not read its handle", index, exc_info=True)
            handle = None

        try:
            csl_json = self.to_csl_json(raw)
        except SkipEntry as exc:
            return self.entry_skipped(
                index=index, handle=handle, reason=_skip_reason(exc)
            )
        except Exception as exc:
            # Every exception, not just the contract's: a format is third-party
            # code reading untrusted content, and one escape would lose the report
            # for the whole file while leaving earlier entries committed.
            logger.warning("Entry %s could not be converted", index, exc_info=True)
            return self.entry_failed(
                index=index, handle=handle, reason=_reason_for(exc)
            )

        using = router.db_for_write(Item)
        try:
            # A savepoint per entry lets the run continue after a database error
            # instead of poisoning the whole transaction.
            with transaction.atomic(using=using):
                item = from_csl_json(csl_json)
        except Exception as exc:
            logger.warning("Entry %s could not be stored", index, exc_info=True)
            return self.entry_failed(
                index=index, handle=handle, reason=_reason_for(exc)
            )

        return self.entry_created(
            index=index, handle=handle, item=item, dry_run=dry_run
        )

    def get_result(self, entries: list[EntryResult], *, dry_run: bool) -> ImportResult:
        """Build the :class:`~literature.importers.results.ImportResult` for a run.

        The one place a subclass can filter, reorder or annotate ``entries``
        without touching how any single entry was imported.

        Args:
            entries: Every entry's result, in source order.
            dry_run: Whether this is a dry run.

        Returns:
            The run's report.
        """
        return ImportResult(entries=entries, dry_run=dry_run, format_name=self.name)

    def entry_created(
        self, *, index: int, handle: str | None, item: Any, dry_run: bool
    ) -> EntryResult:
        """Report one entry as stored.

        Args:
            index: The entry's zero-based position in the file.
            handle: The entry's handle, if it has one.
            item: The stored ``Item``. Dropped from the report on a dry run,
                since its rows are about to be rolled back.
            dry_run: Whether this is a dry run.

        Returns:
            A ``CREATED`` result.
        """
        return EntryResult(
            outcome=Outcome.CREATED,
            index=index,
            handle=handle,
            item=None if dry_run else item,
        )

    def entry_skipped(
        self, *, index: int, handle: str | None, reason: str | None = None
    ) -> EntryResult:
        """Report one entry as recognised but not a bibliographic record.

        Args:
            index: The entry's zero-based position in the file.
            handle: The entry's handle, if it has one.
            reason: What was skipped, when the format knows. Optional, so a
                format is never required to invent one.

        Returns:
            A ``SKIPPED`` result.
        """
        return EntryResult(
            outcome=Outcome.SKIPPED, index=index, handle=handle, reason=reason
        )

    def entry_failed(
        self, *, index: int, handle: str | None, reason: str
    ) -> EntryResult:
        """Report one entry as unable to be stored, with the reason why.

        Args:
            index: The entry's zero-based position in the file.
            handle: The entry's handle, if it has one.
            reason: Why the entry failed, for whoever fixes the source file.

        Returns:
            A ``FAILED`` result.
        """
        return EntryResult(
            outcome=Outcome.FAILED, index=index, handle=handle, reason=reason
        )

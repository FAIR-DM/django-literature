"""The import workflow: one call, four fixed stages, one result.

See contracts/importers.md for the full contract. ``format`` may be a
``Format`` subclass or the registered name of one — a name is resolved
through :func:`~literature.importers.registry.get_format` (FR-018), whose
``UnknownFormat`` is programmer error and is left to propagate rather than
becoming a failed entry (FR-019, contracts/importers.md "Exceptions").
"""

import contextlib
import logging

from django.core.exceptions import ValidationError
from django.db import router, transaction
from django.utils.translation import gettext as _

from literature.converters import from_csl_json
from literature.importers.base import Format
from literature.importers.exceptions import EntryError, ParseError, SkipEntry
from literature.importers.registry import get_format
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


def import_file(
    file,
    format: type[Format] | str,  # noqa: A002 -- contracts/importers.md names it `format`
    *,
    dry_run: bool = False,
) -> ImportResult:
    """Import every entry ``format`` finds in ``file`` into the catalogue.

    Args:
        file: An open file object, or anything with a ``read()``. Never
            opened as a path — passed straight through to ``format.parse``
            (FR-023).
        format: A ``Format`` subclass, or the registered name of one
            (FR-018). A name is resolved through
            :func:`~literature.importers.registry.get_format`, which raises
            ``UnknownFormat`` for a name that is not registered (FR-019).
            The runner instantiates whichever class it ends up with.
        dry_run: Run every stage and report every outcome, then leave the
            catalogue exactly as it was (FR-015). Same code path as a real
            run, wrapped in one outer ``transaction.atomic()`` that is
            rolled back at the end (research.md R2).

    Returns:
        One :class:`~literature.importers.results.EntryResult` per entry
        ``format`` found, in source order (FR-007).

    Never raises for bad file content: a file that cannot be parsed at all
    comes back as an :class:`~literature.importers.results.ImportResult`
    whose single entry failed, with the parser's reason (FR-014). Does
    raise for programmer error — an unregistered format name reaches the
    caller as ``UnknownFormat`` rather than becoming a failed entry.
    """
    from literature.models import Item

    format_name = format if isinstance(format, str) else None
    format_class = get_format(format) if isinstance(format, str) else format
    fmt = format_class()
    entries: list[EntryResult] = []
    index = 0

    # Every transaction below names the alias the models are actually written
    # on. This package is a reusable app, so a project's ``DATABASE_ROUTERS``
    # may send ``Item`` somewhere other than ``default`` — and an unqualified
    # ``transaction.atomic()`` would then open a transaction on an idle
    # connection while the writes committed on another, which makes a dry run
    # store rows and report that it stored nothing.
    using = router.db_for_write(Item)

    # The outer transaction exists only for a dry run (contracts/importers.md
    # step 2). Everything below it is the same code that runs in earnest —
    # nothing branches on ``dry_run`` except this wrapper and the ``item``
    # each created entry carries (data-model.md: a dry run's rows do not
    # survive the rollback, so handing one back would look saved and not be).
    outer_transaction = transaction.atomic(using=using) if dry_run else contextlib.nullcontext()

    with outer_transaction:
        try:
            for raw in fmt.parse(file):
                entry_index = index
                index += 1

                # ``handle_for`` reads the same untrusted content as
                # ``to_csl_json`` (FR-023), but it is only how an entry is
                # *named*. Its own block, so an entry whose handle cannot be
                # read is still converted and stored — reported without a
                # handle rather than turned into a failure, or worse, into
                # whatever outcome the exception it raised happens to mean.
                try:
                    handle = fmt.handle_for(raw)
                except Exception:
                    logger.warning("Entry %s: could not read its handle", entry_index, exc_info=True)
                    handle = None

                try:
                    csl_json = fmt.to_csl_json(raw)
                except SkipEntry:
                    entries.append(EntryResult(outcome=Outcome.SKIPPED, index=entry_index, handle=handle))
                    continue
                except Exception as exc:
                    # Deliberately every exception, not the contract's three.
                    # A format is third-party code reading untrusted content,
                    # and ``from_csl_json`` below is not defensive about the
                    # *shape* of the CSL JSON it is handed. Narrowing this to
                    # the documented types means a malformed entry escapes
                    # ``import_file`` entirely, taking the report for every
                    # entry with it and leaving the ones already stored
                    # committed — the one failure FR-013, FR-014 and FR-023
                    # exist to rule out.
                    logger.warning("Entry %s could not be converted", entry_index, exc_info=True)
                    entries.append(
                        EntryResult(outcome=Outcome.FAILED, index=entry_index, handle=handle, reason=_reason_for(exc))
                    )
                    continue

                try:
                    # A savepoint per entry (research.md R2): the exception is
                    # caught outside this block, which is what lets the run
                    # continue after a database-level failure rather than
                    # poisoning the whole transaction. Nested inside the outer
                    # dry-run transaction, this savepoint behaves the same way.
                    with transaction.atomic(using=using):
                        item = from_csl_json(csl_json)
                except Exception as exc:
                    logger.warning("Entry %s could not be stored", entry_index, exc_info=True)
                    entries.append(
                        EntryResult(outcome=Outcome.FAILED, index=entry_index, handle=handle, reason=_reason_for(exc))
                    )
                    continue

                entries.append(
                    EntryResult(
                        outcome=Outcome.CREATED,
                        index=entry_index,
                        handle=handle,
                        item=None if dry_run else item,
                    )
                )
        except SkipEntry:
            # Out of contract — ``SkipEntry`` belongs to ``to_csl_json`` — but
            # a format recognising a trailing non-record while reading is
            # asking for the same thing, and the alternative is filing a
            # deliberate signal as a failure.
            entries.append(EntryResult(outcome=Outcome.SKIPPED, index=index))
        except Exception as exc:
            # Raised by the generator itself rather than by anything done to
            # one entry, so it ends the file: a format may report the file as
            # unreadable (``ParseError``), report that the *next* entry is bad
            # before converting it (``EntryError``), or simply have a bug. The
            # entries already recovered are kept, and the failure is recorded
            # against the index the generator stopped at.
            logger.warning("Parsing failed at entry %s", index, exc_info=True)
            entries.append(EntryResult(outcome=Outcome.FAILED, index=index, reason=_reason_for(exc)))

        if dry_run:
            transaction.set_rollback(True, using=using)

    return ImportResult(entries=entries, dry_run=dry_run, format_name=format_name)

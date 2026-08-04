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
from django.db import transaction
from django.db.utils import IntegrityError

from literature.converters import from_csl_json
from literature.importers.base import Format
from literature.importers.exceptions import EntryError, ParseError, SkipEntry
from literature.importers.registry import get_format
from literature.importers.results import EntryResult, ImportResult, Outcome

logger = logging.getLogger(__name__)


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
    format_name = format if isinstance(format, str) else None
    format_class = get_format(format) if isinstance(format, str) else format
    fmt = format_class()
    entries: list[EntryResult] = []
    index = 0

    # The outer transaction exists only for a dry run (contracts/importers.md
    # step 2). Everything below it is the same code that runs in earnest —
    # nothing branches on ``dry_run`` except this wrapper and the ``item``
    # each created entry carries (data-model.md: a dry run's rows do not
    # survive the rollback, so handing one back would look saved and not be).
    outer_transaction = transaction.atomic() if dry_run else contextlib.nullcontext()

    with outer_transaction:
        try:
            for raw in fmt.parse(file):
                entry_index = index
                index += 1
                handle = None

                try:
                    # ``handle_for`` reads the same untrusted content as
                    # ``to_csl_json`` (FR-023), so it is inside the block that
                    # turns a bad entry into a result. An entry whose handle
                    # cannot be read is still reported, just without one.
                    handle = fmt.handle_for(raw)
                    csl_json = fmt.to_csl_json(raw)
                except SkipEntry:
                    entries.append(EntryResult(outcome=Outcome.SKIPPED, index=entry_index, handle=handle))
                    continue
                except (EntryError, ValidationError) as exc:
                    logger.warning("Entry %s could not be converted: %s", entry_index, exc)
                    entries.append(
                        EntryResult(outcome=Outcome.FAILED, index=entry_index, handle=handle, reason=str(exc))
                    )
                    continue

                try:
                    # A savepoint per entry (research.md R2): the exception is
                    # caught outside this block, which is what lets the run
                    # continue after a database-level failure rather than
                    # poisoning the whole transaction. Nested inside the outer
                    # dry-run transaction, this savepoint behaves the same way.
                    with transaction.atomic():
                        item = from_csl_json(csl_json)
                except (ValidationError, IntegrityError) as exc:
                    logger.warning("Entry %s could not be stored: %s", entry_index, exc)
                    entries.append(
                        EntryResult(outcome=Outcome.FAILED, index=entry_index, handle=handle, reason=str(exc))
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
        except (ParseError, EntryError) as exc:
            # A format may also raise ``EntryError`` from ``parse`` when it can
            # see that an entry is bad before it is converted (exceptions.py,
            # contracts/importers.md). Either way the generator is finished, so
            # the failure is recorded against the next index and the entries
            # already recovered are kept.
            logger.warning("Parsing failed at entry %s: %s", index, exc)
            entries.append(EntryResult(outcome=Outcome.FAILED, index=index, reason=str(exc)))

        if dry_run:
            transaction.set_rollback(True)

    return ImportResult(entries=entries, dry_run=dry_run, format_name=format_name)

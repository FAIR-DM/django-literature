"""The import workflow: one call, four fixed stages, one result.

See contracts/importers.md for the full contract. ``dry_run`` and the
``format: str`` registry lookup are not implemented here — they belong to
US2 and US3 respectively (plan.md, tasks.md T015 and T018).
"""

import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError

from literature.converters import from_csl_json
from literature.importers.base import Format
from literature.importers.exceptions import EntryError, ParseError, SkipEntry
from literature.importers.results import EntryResult, ImportResult, Outcome

logger = logging.getLogger(__name__)


def import_file(file, format: type[Format]) -> ImportResult:  # noqa: A002 -- contracts/importers.md names it `format`
    """Import every entry ``format`` finds in ``file`` into the catalogue.

    Args:
        file: An open file object, or anything with a ``read()``. Never
            opened as a path — passed straight through to ``format.parse``
            (FR-023).
        format: A ``Format`` subclass. The runner instantiates it.

    Returns:
        One :class:`~literature.importers.results.EntryResult` per entry
        ``format`` found, in source order (FR-007).

    Never raises for bad file content: a file that cannot be parsed at all
    comes back as an :class:`~literature.importers.results.ImportResult`
    whose single entry failed, with the parser's reason (FR-014).
    """
    fmt = format()
    entries: list[EntryResult] = []
    index = 0

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
                entries.append(EntryResult(outcome=Outcome.FAILED, index=entry_index, handle=handle, reason=str(exc)))
                continue

            try:
                # A savepoint per entry (research.md R2): the exception is
                # caught outside this block, which is what lets the run
                # continue after a database-level failure rather than
                # poisoning the whole transaction.
                with transaction.atomic():
                    item = from_csl_json(csl_json)
            except (ValidationError, IntegrityError) as exc:
                logger.warning("Entry %s could not be stored: %s", entry_index, exc)
                entries.append(EntryResult(outcome=Outcome.FAILED, index=entry_index, handle=handle, reason=str(exc)))
                continue

            entries.append(EntryResult(outcome=Outcome.CREATED, index=entry_index, handle=handle, item=item))
    except (ParseError, EntryError) as exc:
        # A format may also raise ``EntryError`` from ``parse`` when it can
        # see that an entry is bad before it is converted (exceptions.py,
        # contracts/importers.md). Either way the generator is finished, so
        # the failure is recorded against the next index and the entries
        # already recovered are kept.
        logger.warning("Parsing failed at entry %s: %s", index, exc)
        entries.append(EntryResult(outcome=Outcome.FAILED, index=index, reason=str(exc)))

    return ImportResult(entries=entries)

"""The import report: turning one ``ImportResult`` into what a page renders (US-1).

New module rather than an addition to ``forms.py``, ``tables.py`` or
``views.py`` (plan.md "The three seams worth naming before implementation"):
a presentation row built from an ``ImportResult`` is neither a view nor a
form, and Article XV wants the row-building grouped on a class rather than
scattered across module functions. Its mirror test is
``tests/test_ui/test_importing.py``.
"""

from dataclasses import dataclass
from typing import cast

from django.urls import reverse

from literature.importers.results import EntryResult, ImportResult, Outcome
from literature.models import Item


@dataclass(frozen=True)
class ImportReportRow:
    """One rendered row of an import report.

    Args:
        position: The entry's place in the source file, counted from one
            (FR-... — the report counts from one, the contract counts from
            zero, decisions.md D3).
        outcome: Carried straight through from the ``EntryResult``.
        citation_key: The source's own handle for the entry, or ``None`` —
            never invented for an entry whose source carried none (AS-10).
        reason: Why the entry failed, or ``None`` for anything that did not.
        item_url: The created reference's own page, or ``None`` for an entry
            that created nothing.
    """

    position: int
    outcome: Outcome
    citation_key: str | None
    reason: str | None
    item_url: str | None


class ImportReport:
    """The front end's own rendering of one ``ImportResult`` (CONTEXT.md).

    Wraps the result and exposes ``rows`` in source order, plus the same
    counts the result already carries — this class adds no counting or
    ordering logic of its own.
    """

    def __init__(self, result: ImportResult):
        self.result = result

    @property
    def rows(self) -> list[ImportReportRow]:
        return [self._row(entry) for entry in self.result]

    def _row(self, entry: EntryResult) -> ImportReportRow:
        # EntryResult.item is typed as bare ``object`` (contracts/importers.md):
        # the import contract makes no promise about what a format stores, only
        # that a real run's created entry carries the object it made. This
        # front end is written against ``BibFormat``'s own guarantee that the
        # stored object is always an ``Item`` (literature/importers/base.py
        # entry_created()), so the cast documents that guarantee rather than
        # narrowing the contract's own, deliberately looser, type.
        item_url = None
        if entry.item is not None:
            item_url = reverse("literature:item-detail", kwargs={"pk": cast(Item, entry.item).pk})
        return ImportReportRow(
            position=entry.index + 1,
            outcome=entry.outcome,
            citation_key=entry.handle,
            reason=entry.reason,
            item_url=item_url,
        )

    @property
    def created(self) -> int:
        return len(self.result.created)

    @property
    def skipped(self) -> int:
        return len(self.result.skipped)

    @property
    def failed(self) -> int:
        return len(self.result.failed)

    @property
    def total(self) -> int:
        return len(self.result)

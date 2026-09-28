"""The import report: turning one ``ImportResult`` into what a page renders.

New module rather than an addition to ``forms.py``, ``tables.py`` or
``views.py``: a presentation row built from an ``ImportResult`` is neither a
view nor a form, and Article XIV wants the row-building grouped on a class
rather than scattered across module functions (FS-011, #103). Its mirror
test is ``tests/test_ui/test_importing.py``.
"""

from dataclasses import dataclass
from typing import cast

from django.urls import reverse

from literature.importers.results import EntryResult, ImportResult, Outcome
from literature.models import Item


@dataclass(frozen=True)
class ImportReportRow:
    """One rendered row of an import report.

    Attributes:
        position: The entry's place in the source file, counted from one —
            the report counts from one, the import contract counts from
            zero.
        outcome: Carried straight through from the ``EntryResult``.
        citation_key: The source's own handle for the entry, or ``None`` —
            never invented for an entry whose source carried none.
        reason: Why the entry failed, or what was recognised and set aside
            for one that was skipped, or ``None`` where neither applies.
        item_url: The created reference's own page, or ``None`` for an entry
            that created nothing.
    """

    position: int
    outcome: Outcome
    citation_key: str | None
    reason: str | None
    item_url: str | None


class ImportReport:
    """The front end's own rendering of one ``ImportResult``.

    Wraps the result and exposes ``rows`` in source order, plus the same
    counts the result already carries — this class adds no counting or
    ordering logic of its own.

    Args:
        result: The import run to render.
    """

    def __init__(self, result: ImportResult):
        self.result = result

    @property
    def rows(self) -> list[ImportReportRow]:
        """Every entry the source file held, as one row each, in source order."""
        return [self._row(entry) for entry in self.result]

    def _row(self, entry: EntryResult) -> ImportReportRow:
        # entry.item is untyped by the import contract
        # (specs/003-import-contract/contracts/importers.md); the cast
        # documents BibFormat's own guarantee that a created entry's item is
        # always an Item, without narrowing the contract's looser type.
        item_url = None
        if entry.item is not None:
            item_url = reverse(
                "literature:item-detail", kwargs={"pk": cast(Item, entry.item).pk}
            )
        return ImportReportRow(
            position=entry.index + 1,
            outcome=entry.outcome,
            citation_key=entry.handle,
            reason=entry.reason,
            item_url=item_url,
        )

    @property
    def created(self) -> int:
        """How many entries created a reference."""
        return len(self.result.created)

    @property
    def skipped(self) -> int:
        """How many entries were recognised and set aside."""
        return len(self.result.skipped)

    @property
    def failed(self) -> int:
        """How many entries failed."""
        return len(self.result.failed)

    @property
    def total(self) -> int:
        """How many entries the source file held."""
        return len(self.result)

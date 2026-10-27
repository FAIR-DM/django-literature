"""The import report: turning one ``ImportResult`` into what a page renders (FS-011, #103)."""

from dataclasses import dataclass
from typing import cast

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
        """Build the report row for one entry result.

        Args:
            entry: The entry result to render.

        Returns:
            The row, with a link to the created reference when there is one.
        """
        # The import contract leaves ``entry.item`` untyped; a created entry's item is always an Item.
        item_url = None
        if entry.item is not None:
            item_url = cast(Item, entry.item).get_absolute_url()
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

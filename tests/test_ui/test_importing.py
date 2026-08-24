"""Tests for ``literature/ui/importing.py`` — the import report adapter (US-1).

``ImportReport`` is the front end's own rendering of an ``ImportResult``
(CONTEXT.md "import result / entry result"); it adds no reporting logic of
its own beyond turning each ``EntryResult`` into a row a template can
render.
"""

import pytest
from django.urls import reverse

from literature.importers.results import EntryResult, ImportResult, Outcome
from literature.ui.importing import ImportReport, ImportReportRow
from tests.factories import ItemFactory


@pytest.mark.django_db
class TestImportReport:
    def test_one_row_per_entry_in_source_order(self):
        result = ImportResult(
            entries=[
                EntryResult(outcome=Outcome.SKIPPED, index=0),
                EntryResult(outcome=Outcome.SKIPPED, index=1),
                EntryResult(outcome=Outcome.SKIPPED, index=2),
            ]
        )
        rows = ImportReport(result).rows
        assert [row.position for row in rows] == [1, 2, 3]

    def test_position_is_the_entrys_index_plus_one(self):
        result = ImportResult(entries=[EntryResult(outcome=Outcome.SKIPPED, index=4)])
        row = ImportReport(result).rows[0]
        assert row.position == 5

    def test_outcome_is_carried_through_unchanged(self):
        result = ImportResult(
            entries=[
                EntryResult(outcome=Outcome.CREATED, index=0, item=ItemFactory()),
                EntryResult(outcome=Outcome.SKIPPED, index=1),
                EntryResult(outcome=Outcome.FAILED, index=2, reason="a reason"),
            ]
        )
        rows = ImportReport(result).rows
        assert [row.outcome for row in rows] == [Outcome.CREATED, Outcome.SKIPPED, Outcome.FAILED]

    def test_citation_key_present_where_the_entry_has_a_handle(self):
        result = ImportResult(entries=[EntryResult(outcome=Outcome.SKIPPED, index=0, handle="Doe2024")])
        row = ImportReport(result).rows[0]
        assert row.citation_key == "Doe2024"

    def test_citation_key_absent_where_the_entry_has_none(self):
        # AS-10 — never invented for an entry whose source carried none.
        result = ImportResult(entries=[EntryResult(outcome=Outcome.SKIPPED, index=0, handle=None)])
        row = ImportReport(result).rows[0]
        assert row.citation_key is None

    def test_reason_present_only_on_failures(self):
        result = ImportResult(
            entries=[
                EntryResult(outcome=Outcome.FAILED, index=0, reason="could not be parsed"),
                EntryResult(outcome=Outcome.CREATED, index=1, item=ItemFactory()),
                EntryResult(outcome=Outcome.SKIPPED, index=2),
            ]
        )
        failed, created, skipped = ImportReport(result).rows
        assert failed.reason == "could not be parsed"
        assert created.reason is None
        assert skipped.reason is None

    def test_a_skipped_entrys_reason_is_carried_through(self):
        """D18: a skipped entry's reason, when it has one, is not dropped."""
        result = ImportResult(entries=[EntryResult(outcome=Outcome.SKIPPED, index=0, reason="a @comment block")])
        row = ImportReport(result).rows[0]
        assert row.reason == "a @comment block"

    def test_a_created_row_carries_the_url_of_its_item(self):
        item = ItemFactory()
        result = ImportResult(entries=[EntryResult(outcome=Outcome.CREATED, index=0, item=item)])
        row = ImportReport(result).rows[0]
        assert row.item_url == reverse("literature:item-detail", kwargs={"pk": item.pk})

    @pytest.mark.parametrize(
        "entry",
        [
            EntryResult(outcome=Outcome.SKIPPED, index=0),
            EntryResult(outcome=Outcome.FAILED, index=0, reason="broken"),
        ],
        ids=["skipped", "failed"],
    )
    def test_a_non_created_row_carries_no_item_url(self, entry):
        result = ImportResult(entries=[entry])
        row = ImportReport(result).rows[0]
        assert row.item_url is None

    def test_the_created_skipped_and_failed_counts_match_the_results_own(self):
        result = ImportResult(
            entries=[
                EntryResult(outcome=Outcome.CREATED, index=0, item=ItemFactory()),
                EntryResult(outcome=Outcome.CREATED, index=1, item=ItemFactory()),
                EntryResult(outcome=Outcome.SKIPPED, index=2),
                EntryResult(outcome=Outcome.FAILED, index=3, reason="x"),
            ]
        )
        report = ImportReport(result)
        assert report.created == len(result.created)
        assert report.skipped == len(result.skipped)
        assert report.failed == len(result.failed)
        assert report.total == len(result)


class TestImportReportRow:
    def test_is_a_frozen_dataclass(self):
        row = ImportReportRow(position=1, outcome=Outcome.SKIPPED, citation_key=None, reason=None, item_url=None)
        with pytest.raises(AttributeError):
            row.position = 2

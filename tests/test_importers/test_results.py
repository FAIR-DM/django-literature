"""Tests for the reporting vocabulary: Outcome, EntryResult, ImportResult.

These objects are the whole point of the contract — they are what a caller reads
instead of comparing counts — so the invariants are asserted here rather than
inferred from runner behaviour.
"""

import dataclasses

import pytest
from django.utils.functional import Promise

from literature.importers.results import EntryResult, ImportResult, Outcome


class TestOutcome:
    def test_has_exactly_three_values(self):
        assert set(Outcome.values) == {"created", "skipped", "failed"}

    def test_labels_are_translatable(self):
        for member in Outcome:
            assert isinstance(member.label, Promise)

    def test_has_no_update_value(self):
        assert not any("updat" in value for value in Outcome.values)


class TestEntryResult:
    def test_is_immutable(self):
        result = EntryResult(outcome=Outcome.CREATED, index=0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.index = 1

    def test_defaults_are_absent_not_empty(self):
        result = EntryResult(outcome=Outcome.CREATED, index=0)
        assert result.handle is None
        assert result.item is None
        assert result.reason is None

    def test_carries_index_and_handle(self):
        result = EntryResult(
            outcome=Outcome.FAILED, index=3, handle="smith2020", reason="bad"
        )
        assert result.index == 3
        assert result.handle == "smith2020"

    def test_failed_requires_a_reason(self):
        with pytest.raises(ValueError, match="reason"):
            EntryResult(outcome=Outcome.FAILED, index=0)

    def test_reason_belongs_only_to_failure(self):
        with pytest.raises(ValueError, match="reason"):
            EntryResult(
                outcome=Outcome.CREATED, index=0, reason="why would this be here"
            )

    def test_a_skipped_entry_may_carry_a_reason(self):
        result = EntryResult(
            outcome=Outcome.SKIPPED, index=0, reason="a @comment block"
        )
        assert result.reason == "a @comment block"

    def test_a_skipped_entry_without_a_reason_is_still_valid(self):
        result = EntryResult(outcome=Outcome.SKIPPED, index=0)
        assert result.reason is None

    def test_reason_is_stringified_so_lazy_messages_survive(self):
        from django.utils.translation import gettext_lazy as _

        result = EntryResult(
            outcome=Outcome.FAILED, index=0, reason=_("unknown item type")
        )
        assert result.reason == "unknown item type"


class TestImportResult:
    @pytest.fixture
    def mixed(self):
        return ImportResult(
            entries=[
                EntryResult(outcome=Outcome.CREATED, index=0),
                EntryResult(outcome=Outcome.FAILED, index=1, reason="bad type"),
                EntryResult(outcome=Outcome.SKIPPED, index=2),
                EntryResult(outcome=Outcome.CREATED, index=3),
            ],
            dry_run=False,
        )

    def test_views_partition_the_entries(self, mixed):
        assert len(mixed.created) == 2
        assert len(mixed.failed) == 1
        assert len(mixed.skipped) == 1
        assert len(mixed.created) + len(mixed.failed) + len(mixed.skipped) == len(
            mixed.entries
        )

    def test_ok_is_false_when_anything_failed(self, mixed):
        assert mixed.ok is False

    def test_ok_is_true_when_nothing_failed(self):
        result = ImportResult(
            entries=[EntryResult(outcome=Outcome.SKIPPED, index=0)], dry_run=False
        )
        assert result.ok is True

    def test_empty_run_is_ok(self):
        result = ImportResult(entries=[], dry_run=False)
        assert result.ok is True
        assert result.entries == []

    def test_records_whether_it_wrote_anything(self):
        assert ImportResult(entries=[], dry_run=True).dry_run is True
        assert ImportResult(entries=[], dry_run=False).dry_run is False

    def test_entries_keep_source_order(self, mixed):
        assert [entry.index for entry in mixed.entries] == [0, 1, 2, 3]

    def test_is_iterable_over_entries(self, mixed):
        assert list(mixed) == mixed.entries

    def test_length_is_the_entry_count(self, mixed):
        assert len(mixed) == 4


class TestAFailureAlwaysExplainsItself:
    def test_an_empty_reason_is_refused(self):
        with pytest.raises(ValueError, match="reason"):
            EntryResult(outcome=Outcome.FAILED, index=0, reason="")

    def test_a_whitespace_only_reason_is_refused(self):
        with pytest.raises(ValueError, match="reason"):
            EntryResult(outcome=Outcome.FAILED, index=0, reason="   \n")

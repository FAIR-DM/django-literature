"""Tests for ``import_file`` (contracts/importers.md), US1.

Split in two, per tasks.md: the *reporting* half asserts what the returned
``ImportResult`` says, the *resilience* half asserts the workflow survives
everything a source file can throw at it. Both halves exercise the same
function; the split is about what each test is checking, not about two
different code paths.
"""

import io
import logging

import pytest

from literature.importers.base import Format
from literature.importers.results import Outcome
from literature.importers.runner import import_file
from literature.models import Item, ItemDate, ItemIdentifier, ItemName

from .conftest import (
    DuplicateCustomIdentifier,
    make_bad_handle_format,
    make_echo_format,
    make_failing_parse_format,
    make_unparseable_format,
)


def _counts():
    return (
        Item.objects.count(),
        ItemName.objects.count(),
        ItemDate.objects.count(),
        ItemIdentifier.objects.count(),
    )


@pytest.mark.django_db
class TestReporting:
    """What the returned ``ImportResult`` says (FR-007 through FR-013)."""

    def test_one_result_per_entry_in_source_order(self):
        """FR-007, SC-002: every entry the format found appears exactly once, in order."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "skip", "reason": "not a record"},
            {"kind": "entry_error", "reason": "bad", "id": "c"},
            {"kind": "good", "id": "d", "type": "book"},
        ]
        result = import_file(io.StringIO(), make_echo_format(entries))

        assert len(result.entries) == len(entries)
        assert [entry.index for entry in result.entries] == [0, 1, 2, 3]

    def test_outcomes_are_drawn_only_from_the_vocabulary(self):
        """FR-008."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "skip"},
            {"kind": "entry_error", "reason": "bad"},
        ]
        result = import_file(io.StringIO(), make_echo_format(entries))

        for entry in result.entries:
            assert entry.outcome in Outcome

    def test_every_failure_carries_a_reason(self):
        """FR-010."""
        entries = [{"kind": "entry_error", "reason": "unrecognised item type", "id": "a"}]
        result = import_file(io.StringIO(), make_echo_format(entries))

        assert len(result.failed) == 1
        assert result.failed[0].reason == "unrecognised item type"

    def test_every_result_carries_its_index_and_the_handle_where_offered(self):
        """FR-009, SC-009."""
        entries = [
            {"kind": "good", "id": "a", "type": "book", "handle": "smith2020"},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        result = import_file(io.StringIO(), make_echo_format(entries))

        assert result.entries[0].index == 0
        assert result.entries[0].handle == "smith2020"
        assert result.entries[1].index == 1
        assert result.entries[1].handle is None

    def test_a_failed_entrys_handle_is_also_carried(self):
        """FR-009, SC-009: a failure locates its entry by handle too, where offered."""
        entries = [{"kind": "entry_error", "reason": "bad", "id": "a", "handle": "smith2020"}]
        result = import_file(io.StringIO(), make_echo_format(entries))

        assert result.failed[0].handle == "smith2020"

    def test_skipped_is_distinguishable_from_failed(self):
        """FR-011: a recognised-but-non-bibliographic element is not reported as an error."""
        entries = [
            {"kind": "skip", "reason": "a comment"},
            {"kind": "entry_error", "reason": "bad"},
        ]
        result = import_file(io.StringIO(), make_echo_format(entries))

        assert len(result.skipped) == 1
        assert len(result.failed) == 1
        assert result.skipped[0].outcome == Outcome.SKIPPED
        assert result.failed[0].outcome == Outcome.FAILED
        assert result.skipped[0].reason is None

    def test_failures_are_in_the_result_even_with_logging_silenced(self, caplog):
        """FR-013, SC-005: the result is never the only place a failure appears from."""
        entries = [{"kind": "entry_error", "reason": "bad entry", "id": "a"}]
        with caplog.at_level(logging.CRITICAL, logger="literature.importers.runner"):
            result = import_file(io.StringIO(), make_echo_format(entries))

        assert caplog.records == []
        assert len(result.failed) == 1
        assert result.failed[0].reason == "bad entry"

    def test_caller_reads_every_entrys_fate_from_the_result_alone(self):
        """SC-001: a known mix of good, skipped, and failing entries, read back
        without consulting anything format-specific."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "entry_error", "reason": "unrecognised type", "id": "b"},
            {"kind": "skip", "reason": "a header line"},
            {"kind": "good", "id": "c", "type": "book"},
        ]
        result = import_file(io.StringIO(), make_echo_format(entries))

        assert not result.ok
        assert len(result.created) == 2
        assert len(result.failed) == 1
        assert len(result.skipped) == 1
        assert result.failed[0].reason == "unrecognised type"


@pytest.mark.django_db
class TestLazyConsumption:
    """FR-024, US1 scenario 8: entries are consumed and stored progressively.

    A generator only advances past its ``yield`` when the consumer asks
    for the next value, so ``on_yield`` firing for entry *N* observes
    however many entries the runner has *already stored* by that point —
    not how many the format has produced. A runner that drained the whole
    iterator up front (``list(fmt.parse(file))``) before storing anything
    would make every ``on_yield`` observe a count of zero instead.
    """

    def test_each_entry_is_stored_before_the_next_is_requested(self):
        observed_counts_before_yield = []

        def on_yield(_raw):
            observed_counts_before_yield.append(Item.objects.count())

        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "good", "id": "b", "type": "book"},
            {"kind": "good", "id": "c", "type": "book"},
        ]
        result = import_file(io.StringIO(), make_echo_format(entries, on_yield=on_yield))

        assert observed_counts_before_yield == [0, 1, 2]
        assert len(result.created) == 3


@pytest.mark.django_db
class TestResilience:
    """Treats file content as untrusted throughout (FR-023)."""

    def test_accepts_an_already_open_file_object_untouched(self):
        """The runner passes ``file`` straight through — it never opens a path itself."""
        received = []

        class _CapturingFormat(Format):
            label = "capturing"

            def parse(self, file):
                received.append(file)
                return iter([])

            def to_csl_json(self, raw):  # pragma: no cover - never called
                return {}

        _CapturingFormat.name = "capturing"

        handle = io.StringIO("irrelevant content")
        import_file(handle, _CapturingFormat)

        assert received == [handle]

    def test_a_failing_entry_does_not_stop_the_ones_after_it(self):
        """FR-012, SC-003."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "entry_error", "reason": "bad", "id": "b"},
            {"kind": "good", "id": "c", "type": "book"},
        ]
        result = import_file(io.StringIO(), make_echo_format(entries))

        assert len(result.created) == 2
        assert len(result.failed) == 1
        assert Item.objects.count() == 2

    def test_partial_failure_from_a_validation_error_leaves_nothing_behind(self):
        """FR-006, SC-008: item acceptable, one identifier is not — reported as
        one failure, and even the already-saved Item does not survive."""
        entries = [{"kind": "good", "id": "a", "type": "book", "DOI": "not-a-real-doi"}]
        before = _counts()

        result = import_file(io.StringIO(), make_echo_format(entries))

        assert len(result.failed) == 1
        assert _counts() == before

    def test_partial_failure_from_an_integrity_error_leaves_nothing_behind(self, bypass_identifier_validation):
        """FR-006, SC-008, research.md R2: a real IntegrityError, not just a
        ValidationError, must also leave nothing behind."""
        entries = [{"kind": "good", "id": "a", "type": "book", "custom": DuplicateCustomIdentifier()}]
        before = _counts()

        result = import_file(io.StringIO(), make_echo_format(entries))

        assert len(result.failed) == 1
        assert _counts() == before

    def test_an_entry_after_an_integrity_error_still_imports(self, bypass_identifier_validation):
        """research.md R2: the savepoint protects the entries that follow a
        database-level failure, not only ones that follow a ValidationError."""
        entries = [
            {"kind": "good", "id": "a", "type": "book", "custom": DuplicateCustomIdentifier()},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        result = import_file(io.StringIO(), make_echo_format(entries))

        assert len(result.failed) == 1
        assert len(result.created) == 1
        assert Item.objects.filter(citation_key="b").exists()

    def test_an_entry_error_from_parse_is_reported_not_raised(self):
        """FR-014: ``EntryError`` is documented as coming from ``parse`` as well
        as from ``to_csl_json``, so it must not escape either."""
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        result = import_file(io.StringIO(), make_failing_parse_format(entries, reason="entry 2 is malformed"))

        assert [entry.outcome for entry in result.entries] == [Outcome.CREATED, Outcome.FAILED]
        assert result.entries[1].index == 1
        assert result.entries[1].reason == "entry 2 is malformed"
        assert Item.objects.count() == 1

    def test_a_handle_that_cannot_be_read_is_reported_not_raised(self):
        """FR-023: ``handle_for`` reads untrusted content too. The entry is
        still reported, with no handle, rather than ending the run."""
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        result = import_file(io.StringIO(), make_bad_handle_format(entries))

        assert len(result.entries) == 1
        assert result.entries[0].outcome == Outcome.FAILED
        assert result.entries[0].handle is None
        assert Item.objects.count() == 0

    def test_unparseable_file_returns_a_one_entry_failed_result(self):
        """FR-014, SC-007."""
        result = import_file(io.StringIO(), make_unparseable_format(reason="not a BibTeX file"))

        assert len(result.entries) == 1
        assert result.entries[0].outcome == Outcome.FAILED
        assert result.entries[0].index == 0
        assert result.entries[0].reason == "not a BibTeX file"
        assert Item.objects.count() == 0

    def test_empty_file_is_a_successful_import_of_nothing(self):
        result = import_file(io.StringIO(), make_echo_format([]))

        assert result.entries == []
        assert result.ok is True

    def test_unexpected_encoding_is_reported_not_stored_corrupted(self):
        """A parse failure naming the encoding, not corrupted stored text."""
        result = import_file(
            io.StringIO(),
            make_unparseable_format(reason="cannot decode file as UTF-8"),
        )

        assert result.entries[0].outcome == Outcome.FAILED
        assert "UTF-8" in result.entries[0].reason
        assert Item.objects.count() == 0

    def test_truncated_file_reports_recovered_entries_and_a_failure_for_the_remainder(self):
        """Edge case: a ParseError raised mid-stream, after some entries."""

        class _TruncatedFormat(Format):
            label = "truncated"

            def parse(self, file):
                from literature.importers.exceptions import ParseError

                yield {"kind": "good", "id": "a", "type": "book"}
                yield {"kind": "good", "id": "b", "type": "book"}
                raise ParseError("truncated mid-entry")

            def to_csl_json(self, raw):
                return {key: value for key, value in raw.items() if key != "kind"}

        _TruncatedFormat.name = "truncated"

        result = import_file(io.StringIO(), _TruncatedFormat)

        assert len(result.entries) == 3
        assert [entry.outcome for entry in result.entries] == [
            Outcome.CREATED,
            Outcome.CREATED,
            Outcome.FAILED,
        ]
        assert result.entries[2].index == 2
        assert result.entries[2].reason == "truncated mid-entry"

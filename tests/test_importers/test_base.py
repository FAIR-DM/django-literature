"""Tests for the ``BibFormat`` contract (data-model.md, contracts/importers.md).

Two things live in this one module, because both belong to ``base.py`` now
that the workflow moved onto the class (spec.md Refinements #2): the format
contract itself — a subclass supplies exactly two stages and may override a
third (FR-003) — and the workflow every ``BibFormat`` gets by default:
``import_file``, ``import_entries``, ``import_entry`` and ``get_result``,
each an ordinary overridable method, split in two below the same way
tasks.md splits it — a *reporting* half asserting what the returned
``ImportResult`` says, and a *resilience* half asserting the workflow
survives everything a source file can throw at it. Both halves exercise the
same method; the split is about what each test is checking, not about two
different code paths. The dry-run classes at the end are US2: a dry run is a
mode of ``import_file``, not a second code path, so its tests belong here
too (decision D23's precedent, applied to the same move).
"""

import abc
import io
import logging

import pytest

from literature.importers.base import BibFormat
from literature.importers.exceptions import EntryError, ParseError, SkipEntry
from literature.importers.results import EntryResult, ImportResult, Outcome
from literature.models import Item, ItemDate, ItemIdentifier, ItemName

from .conftest import (
    DuplicateCustomIdentifier,
    make_bad_handle_format,
    make_echo_format,
    make_failing_parse_format,
    make_raising_format,
    make_skipping_handle_format,
    make_unparseable_format,
)


def _counts():
    return (
        Item.objects.count(),
        ItemName.objects.count(),
        ItemDate.objects.count(),
        ItemIdentifier.objects.count(),
    )


class TestBibFormatIsAbstract:
    def test_cannot_instantiate_without_parse_and_to_csl_json(self):
        class Incomplete(BibFormat):
            label = "Incomplete"

        Incomplete.name = "incomplete"

        with pytest.raises(TypeError):
            Incomplete()

    def test_cannot_instantiate_missing_only_parse(self):
        class NoParse(BibFormat):
            label = "No parse"

            def to_csl_json(self, raw):
                return {}

        NoParse.name = "no-parse"

        with pytest.raises(TypeError):
            NoParse()

    def test_cannot_instantiate_missing_only_to_csl_json(self):
        class NoConvert(BibFormat):
            label = "No convert"

            def parse(self, file):
                return iter([])

        NoConvert.name = "no-convert"

        with pytest.raises(TypeError):
            NoConvert()

    def test_is_an_abc(self):
        assert issubclass(BibFormat, abc.ABC)


class TestHandleFor:
    def test_defaults_to_none(self):
        class Minimal(BibFormat):
            label = "Minimal"

            def parse(self, file):
                return iter([])

            def to_csl_json(self, raw):
                return {}

        Minimal.name = "minimal"

        assert Minimal().handle_for(object()) is None

    def test_can_be_overridden(self):
        class WithHandles(BibFormat):
            label = "With handles"

            def parse(self, file):
                return iter([])

            def to_csl_json(self, raw):
                return {}

            def handle_for(self, raw):
                return raw.upper()

        WithHandles.name = "with-handles"

        assert WithHandles().handle_for("smith2020") == "SMITH2020"


class TestFullSubclass:
    def test_a_subclass_supplying_all_three_works(self):
        class Full(BibFormat):
            label = "Full"

            def parse(self, file):
                yield "raw-entry"

            def to_csl_json(self, raw):
                return {"type": "book", "id": raw}

            def handle_for(self, raw):
                return raw

        Full.name = "full"

        fmt = Full()
        assert list(fmt.parse(None)) == ["raw-entry"]
        assert fmt.to_csl_json("raw-entry") == {"type": "book", "id": "raw-entry"}
        assert fmt.handle_for("raw-entry") == "raw-entry"


class TestBibFormatRequiresOnlyTwoStages:
    """FR-003, as refined: a format MUST need to supply only ``parse`` and
    ``to_csl_json`` to get correct behaviour. This replaces the pre-rework
    version of this test, which asserted the class's public surface was
    exactly ``{parse, to_csl_json, handle_for}`` — true before the workflow
    moved onto the class, and false now that ``import_file`` and its parts
    live here too. The maintainer's ruling was explicit that this is not a
    defect to guard against: "It's not up to us to try and prevent novel use
    cases ... If you choose to overwrite additional methods, all power to
    you." What still has to hold is that the *required* surface stays
    exactly two methods.
    """

    def test_abstract_methods_are_exactly_the_two_required_stages(self):
        assert BibFormat.__abstractmethods__ == frozenset({"parse", "to_csl_json"})

    def test_the_provided_workflow_methods_are_ordinary_and_overridable(self):
        """Not hidden, not name-mangled, not marked final. Present as plain
        methods a subclass can replace — exactly what
        ``TestOverridingImportEntry`` and ``TestOverridingGetResult`` below
        do.
        """
        for name in (
            "import_file",
            "import_entries",
            "import_entry",
            "get_result",
            "entry_created",
            "entry_skipped",
            "entry_failed",
        ):
            assert callable(getattr(BibFormat, name))
            assert name not in BibFormat.__abstractmethods__


@pytest.mark.django_db
class TestWorkflowMethodsAreIndividuallyCallable:
    """T025: the split methods are genuinely usable on their own, not merely
    present. Each does its one job without the rest of the workflow having
    to run first — the point of splitting ``import_file`` into named steps.
    """

    def test_import_entry_stores_one_entry_and_returns_its_result(self):
        fmt = make_echo_format([])()

        result = fmt.import_entry({"kind": "good", "id": "a", "type": "book"}, 0, dry_run=False)

        assert result.outcome == Outcome.CREATED
        assert result.index == 0
        assert Item.objects.count() == 1

    def test_import_entries_loops_over_parsed_entries(self):
        fmt = make_echo_format([])()

        results = fmt.import_entries(
            iter(
                [
                    {"kind": "good", "id": "a", "type": "book"},
                    {"kind": "skip", "reason": "a comment"},
                ]
            ),
            dry_run=False,
        )

        assert [entry.outcome for entry in results] == [Outcome.CREATED, Outcome.SKIPPED]

    def test_get_result_builds_an_import_result_from_entry_results(self):
        fmt = make_echo_format([])()
        entries = [EntryResult(outcome=Outcome.CREATED, index=0)]

        result = fmt.get_result(entries, dry_run=False)

        assert isinstance(result, ImportResult)
        assert result.entries == entries
        assert result.dry_run is False

    def test_import_file_drives_the_whole_workflow(self):
        echo_format = make_echo_format([{"kind": "good", "id": "a", "type": "book"}])

        result = echo_format().import_file(io.StringIO())

        assert len(result.created) == 1
        assert Item.objects.count() == 1


@pytest.mark.django_db
class TestOverridingImportEntry:
    """A subclass that changes how one entry is handled still gets the rest
    of the workflow — iteration, ordering, and reporting — for free.
    """

    def test_overriding_import_entry_changes_only_that_step(self):
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "good", "id": "b", "type": "book"},
        ]

        class SkipsTheFirstEntry(make_echo_format(entries)):
            def import_entry(self, raw, index, *, dry_run):
                if index == 0:
                    return self.entry_skipped(index=index, handle=self.handle_for(raw))
                return super().import_entry(raw, index, dry_run=dry_run)

        result = SkipsTheFirstEntry().import_file(io.StringIO())

        assert [entry.outcome for entry in result] == [Outcome.SKIPPED, Outcome.CREATED]
        assert len(result.entries) == 2
        assert Item.objects.count() == 1


@pytest.mark.django_db
class TestOverridingGetResult:
    """A subclass can reshape what a run reports without touching how
    entries are imported.
    """

    def test_overriding_get_result_changes_the_report(self):
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "skip", "reason": "a comment"},
        ]

        class DropsSkippedFromTheReport(make_echo_format(entries)):
            def get_result(self, entries, *, dry_run):
                entries = [entry for entry in entries if entry.outcome != Outcome.SKIPPED]
                return super().get_result(entries, dry_run=dry_run)

        result = DropsSkippedFromTheReport().import_file(io.StringIO())

        assert len(result.entries) == 1
        assert result.entries[0].outcome == Outcome.CREATED
        assert Item.objects.count() == 1


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
        result = make_echo_format(entries)().import_file(io.StringIO())

        assert len(result.entries) == len(entries)
        assert [entry.index for entry in result.entries] == [0, 1, 2, 3]

    def test_outcomes_are_drawn_only_from_the_vocabulary(self):
        """FR-008."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "skip"},
            {"kind": "entry_error", "reason": "bad"},
        ]
        result = make_echo_format(entries)().import_file(io.StringIO())

        for entry in result.entries:
            assert entry.outcome in Outcome

    def test_every_failure_carries_a_reason(self):
        """FR-010."""
        entries = [{"kind": "entry_error", "reason": "unrecognised item type", "id": "a"}]
        result = make_echo_format(entries)().import_file(io.StringIO())

        assert len(result.failed) == 1
        assert result.failed[0].reason == "unrecognised item type"

    def test_every_result_carries_its_index_and_the_handle_where_offered(self):
        """FR-009, SC-009."""
        entries = [
            {"kind": "good", "id": "a", "type": "book", "handle": "smith2020"},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        result = make_echo_format(entries)().import_file(io.StringIO())

        assert result.entries[0].index == 0
        assert result.entries[0].handle == "smith2020"
        assert result.entries[1].index == 1
        assert result.entries[1].handle is None

    def test_a_failed_entrys_handle_is_also_carried(self):
        """FR-009, SC-009: a failure locates its entry by handle too, where offered."""
        entries = [{"kind": "entry_error", "reason": "bad", "id": "a", "handle": "smith2020"}]
        result = make_echo_format(entries)().import_file(io.StringIO())

        assert result.failed[0].handle == "smith2020"

    def test_skipped_is_distinguishable_from_failed(self):
        """FR-011: a recognised-but-non-bibliographic element is not reported as an error."""
        entries = [
            {"kind": "skip", "reason": "a comment"},
            {"kind": "entry_error", "reason": "bad"},
        ]
        result = make_echo_format(entries)().import_file(io.StringIO())

        assert len(result.skipped) == 1
        assert len(result.failed) == 1
        assert result.skipped[0].outcome == Outcome.SKIPPED
        assert result.failed[0].outcome == Outcome.FAILED
        assert result.skipped[0].reason is None

    def test_failures_are_in_the_result_even_with_logging_silenced(self, caplog):
        """FR-013, SC-005: the result is never the only place a failure appears from."""
        entries = [{"kind": "entry_error", "reason": "bad entry", "id": "a"}]
        with caplog.at_level(logging.CRITICAL, logger="literature.importers.base"):
            result = make_echo_format(entries)().import_file(io.StringIO())

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
        result = make_echo_format(entries)().import_file(io.StringIO())

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
        result = make_echo_format(entries, on_yield=on_yield)().import_file(io.StringIO())

        assert observed_counts_before_yield == [0, 1, 2]
        assert len(result.created) == 3


@pytest.mark.django_db
class TestResilience:
    """Treats file content as untrusted throughout (FR-023)."""

    def test_accepts_an_already_open_file_object_untouched(self):
        """The runner passes ``file`` straight through — it never opens a path itself."""
        received = []

        class _CapturingFormat(BibFormat):
            label = "capturing"

            def parse(self, file):
                received.append(file)
                return iter([])

            def to_csl_json(self, raw):  # pragma: no cover - never called
                return {}

        _CapturingFormat.name = "capturing"

        handle = io.StringIO("irrelevant content")
        _CapturingFormat().import_file(handle)

        assert received == [handle]

    def test_a_failing_entry_does_not_stop_the_ones_after_it(self):
        """FR-012, SC-003."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "entry_error", "reason": "bad", "id": "b"},
            {"kind": "good", "id": "c", "type": "book"},
        ]
        result = make_echo_format(entries)().import_file(io.StringIO())

        assert len(result.created) == 2
        assert len(result.failed) == 1
        assert Item.objects.count() == 2

    def test_partial_failure_from_a_validation_error_leaves_nothing_behind(self):
        """FR-006, SC-008: item acceptable, one identifier is not — reported as
        one failure, and even the already-saved Item does not survive."""
        entries = [{"kind": "good", "id": "a", "type": "book", "DOI": "not-a-real-doi"}]
        before = _counts()

        result = make_echo_format(entries)().import_file(io.StringIO())

        assert len(result.failed) == 1
        assert _counts() == before

    def test_partial_failure_from_an_integrity_error_leaves_nothing_behind(self, bypass_identifier_validation):
        """FR-006, SC-008, research.md R2: a real IntegrityError, not just a
        ValidationError, must also leave nothing behind."""
        entries = [{"kind": "good", "id": "a", "type": "book", "custom": DuplicateCustomIdentifier()}]
        before = _counts()

        result = make_echo_format(entries)().import_file(io.StringIO())

        assert len(result.failed) == 1
        assert _counts() == before

    def test_an_entry_after_an_integrity_error_still_imports(self, bypass_identifier_validation):
        """research.md R2: the savepoint protects the entries that follow a
        database-level failure, not only ones that follow a ValidationError."""
        entries = [
            {"kind": "good", "id": "a", "type": "book", "custom": DuplicateCustomIdentifier()},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        result = make_echo_format(entries)().import_file(io.StringIO())

        assert len(result.failed) == 1
        assert len(result.created) == 1
        assert Item.objects.filter(citation_key="b").exists()

    def test_an_entry_error_from_parse_is_reported_not_raised(self):
        """FR-014: ``EntryError`` is documented as coming from ``parse`` as well
        as from ``to_csl_json``, so it must not escape either."""
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        result = make_failing_parse_format(entries, reason="entry 2 is malformed")().import_file(io.StringIO())

        assert [entry.outcome for entry in result.entries] == [Outcome.CREATED, Outcome.FAILED]
        assert result.entries[1].index == 1
        assert result.entries[1].reason == "entry 2 is malformed"
        assert Item.objects.count() == 1

    def test_a_handle_that_cannot_be_read_costs_the_handle_and_nothing_else(self):
        """FR-023: ``handle_for`` reads untrusted content too, so it can fail
        on a malformed entry — but it only decides what the entry is *called*.
        A record that converts and stores perfectly well is imported without a
        handle, rather than failed because its key was unreadable or, worse,
        given whatever outcome the exception it raised happens to mean.
        """
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        result = make_bad_handle_format(entries)().import_file(io.StringIO())

        assert len(result.entries) == 1
        assert result.entries[0].outcome == Outcome.CREATED
        assert result.entries[0].handle is None
        assert Item.objects.count() == 1

    def test_a_handle_that_raises_skipentry_does_not_discard_the_entry(self):
        """``handle_for`` sharing a block with ``to_csl_json`` meant a
        ``SkipEntry`` out of it silently dropped a good bibliographic record —
        reported as "recognised, deliberately not stored", stored nowhere, with
        no reason to explain it. The two stages have separate blocks now.
        """
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        result = make_skipping_handle_format(entries)().import_file(io.StringIO())

        assert [entry.outcome for entry in result.entries] == [Outcome.CREATED]
        assert Item.objects.count() == 1

    def test_unparseable_file_returns_a_one_entry_failed_result(self):
        """FR-014, SC-007."""
        result = make_unparseable_format(reason="not a BibTeX file")().import_file(io.StringIO())

        assert len(result.entries) == 1
        assert result.entries[0].outcome == Outcome.FAILED
        assert result.entries[0].index == 0
        assert result.entries[0].reason == "not a BibTeX file"
        assert Item.objects.count() == 0

    def test_empty_file_is_a_successful_import_of_nothing(self):
        result = make_echo_format([])().import_file(io.StringIO())

        assert result.entries == []
        assert result.ok is True

    def test_unexpected_encoding_is_reported_not_stored_corrupted(self):
        """A parse failure naming the encoding, not corrupted stored text."""
        result = make_unparseable_format(reason="cannot decode file as UTF-8")().import_file(io.StringIO())

        assert result.entries[0].outcome == Outcome.FAILED
        assert "UTF-8" in result.entries[0].reason
        assert Item.objects.count() == 0

    def test_truncated_file_reports_recovered_entries_and_a_failure_for_the_remainder(self):
        """Edge case: a ParseError raised mid-stream, after some entries."""

        class _TruncatedFormat(BibFormat):
            label = "truncated"

            def parse(self, file):
                from literature.importers.exceptions import ParseError

                yield {"kind": "good", "id": "a", "type": "book"}
                yield {"kind": "good", "id": "b", "type": "book"}
                raise ParseError("truncated mid-entry")

            def to_csl_json(self, raw):
                return {key: value for key, value in raw.items() if key != "kind"}

        _TruncatedFormat.name = "truncated"

        result = _TruncatedFormat().import_file(io.StringIO())

        assert len(result.entries) == 3
        assert [entry.outcome for entry in result.entries] == [
            Outcome.CREATED,
            Outcome.CREATED,
            Outcome.FAILED,
        ]
        assert result.entries[2].index == 2
        assert result.entries[2].reason == "truncated mid-entry"


@pytest.mark.django_db
class TestExceptionsOutsideTheContract:
    """FR-013, FR-014, FR-023 for the exceptions the contract never named.

    A format is third-party code reading untrusted content, and the stage that
    builds an ``Item`` is not defensive about the *shape* of the CSL JSON it is
    handed — ``from_csl_json`` calls ``.get()`` on a date variable and iterates
    a name variable without checking either. So a real file can produce an
    ``AttributeError`` or a ``TypeError`` from a format that did nothing wrong.

    Catching only the three exceptions the contract names meant those escaped
    ``import_file``: the caller got no result at all, every entry after the bad
    one was never attempted, and the entries already stored stayed committed.
    That is the one failure this whole contract exists to rule out, so the net
    is deliberately every ``Exception`` rather than a list of types.
    """

    def test_a_csl_shape_the_conversion_cannot_handle_fails_one_entry_only(self):
        """A date variable as a bare string rather than an object. Nothing in
        the format is wrong, and ``from_csl_json`` raises ``AttributeError``.
        """
        entries = [
            {"id": "a", "type": "book"},
            {"id": "b", "type": "book", "issued": "2020"},
            {"id": "c", "type": "book"},
        ]

        result = make_echo_format(entries)().import_file(io.StringIO())

        assert [entry.outcome for entry in result] == [Outcome.CREATED, Outcome.FAILED, Outcome.CREATED]
        assert Item.objects.count() == 2
        assert "AttributeError" in result.failed[0].reason

    def test_a_name_variable_of_the_wrong_type_fails_one_entry_only(self):
        entries = [{"id": "a", "type": "book", "author": 42}, {"id": "b", "type": "book"}]

        result = make_echo_format(entries)().import_file(io.StringIO())

        assert [entry.outcome for entry in result] == [Outcome.FAILED, Outcome.CREATED]
        assert Item.objects.count() == 1

    def test_a_format_with_a_bug_fails_its_entry_rather_than_the_run(self):
        """A ``KeyError`` out of ``to_csl_json`` is a bug in the format, not a
        signal in the contract's vocabulary. It still cannot cost the caller
        the report for every other entry.
        """
        result = make_raising_format([{"id": "a"}], KeyError("author"))().import_file(io.StringIO())

        assert [entry.outcome for entry in result] == [Outcome.FAILED]
        assert "KeyError" in result.failed[0].reason

    def test_a_format_whose_reader_has_a_bug_ends_the_file_and_is_reported(self):
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        result = make_raising_format(entries, RuntimeError("iterator broke"), stage="parse")().import_file(
            io.StringIO()
        )

        assert [entry.outcome for entry in result] == [Outcome.CREATED, Outcome.FAILED]
        assert result.failed[0].index == 1
        assert "RuntimeError" in result.failed[0].reason
        assert Item.objects.count() == 1

    def test_skipentry_from_the_reader_is_a_skip_not_an_escape(self):
        """``exceptions.py``: none of a format's three signals ever reaches the
        caller. ``SkipEntry`` is a sibling of ``ParseError`` rather than a
        subclass, so a handler naming only the other two let it straight out.
        """
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        result = make_raising_format(entries, SkipEntry("trailing junk"), stage="parse")().import_file(io.StringIO())

        assert [entry.outcome for entry in result] == [Outcome.CREATED, Outcome.SKIPPED]

    def test_parseerror_from_the_converting_stage_is_filed_at_the_right_index(self):
        """Out of contract — ``ParseError`` belongs to ``parse`` — but when the
        outer handler caught it, the index had already moved past the entry
        that raised, so entry 1 got no result and the failure claimed index 2.
        """
        entries = [{"kind": "good", "id": "a", "type": "book"}, {"id": "b", "type": "book"}]

        result = make_raising_format(entries, ParseError("boom"))().import_file(io.StringIO())

        assert [(entry.index, entry.outcome) for entry in result] == [(0, Outcome.FAILED), (1, Outcome.FAILED)]


@pytest.mark.django_db
class TestFailureReasons:
    """FR-010: every failure carries a reason somebody can act on."""

    def test_a_validation_error_reads_as_its_message_not_its_repr(self):
        """``str(ValidationError)`` is the ``repr`` of the list inside it, so
        a reader got ``["Unknown CSL JSON item type: 'nope'"]`` — brackets,
        quotes and all — for the failure mode the contract names as a format's
        ordinary way of rejecting an entry.
        """
        result = make_echo_format([{"id": "a", "type": "nope"}])().import_file(io.StringIO())

        assert result.failed[0].reason == "Unknown CSL JSON item type: 'nope'"

    def test_an_exception_raised_with_no_message_still_yields_a_reason(self):
        """``str(EntryError())`` is ``""`` — not ``None``, so it passed the
        invariant, and printed as a blank line next to the entry's index.
        """
        result = make_raising_format([{"id": "a"}], EntryError())().import_file(io.StringIO())

        assert result.failed[0].reason.strip()
        assert "EntryError" in result.failed[0].reason

    def test_a_reason_the_format_wrote_is_passed_through_unchanged(self):
        """The contract's own exceptions carry a message written for whoever
        has to fix the file, so nothing is prepended to it.
        """
        result = make_raising_format([{"id": "a"}], EntryError("no author, no year"))().import_file(io.StringIO())

        assert result.failed[0].reason == "no author, no year"


@pytest.mark.django_db(transaction=True)
class TestResilienceOutsideATestTransaction:
    """The resilience guarantees at the transaction level a caller runs at.

    Every test in ``TestResilience`` runs under non-transactional
    ``django_db``, so the runner's per-entry ``transaction.atomic()`` is a
    savepoint nested inside the test's own transaction, and a failure rolls
    back through Django's ``savepoint_rollback`` branch. A real caller in
    autocommit hits the other branch entirely: the per-entry block is
    outermost, and the rollback is a genuine ``connection.rollback()``.

    Both branches behave the same here, but "we never checked" and "it works"
    are different claims, and the per-entry savepoint is the mechanism the
    atomicity promise rests on.
    """

    def test_a_database_failure_rolls_back_its_entry_alone(self, bypass_identifier_validation):
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"id": "b", "type": "book", "custom": DuplicateCustomIdentifier()},
            {"kind": "good", "id": "c", "type": "book"},
        ]

        result = make_echo_format(entries)().import_file(io.StringIO())

        assert [entry.outcome for entry in result] == [Outcome.CREATED, Outcome.FAILED, Outcome.CREATED]
        assert Item.objects.count() == 2
        assert not Item.objects.filter(citation_key="b").exists()
        assert ItemIdentifier.objects.count() == 0

    def test_a_partway_failure_leaves_nothing_of_its_entry_behind(self):
        """FR-006, SC-008 — an entry is atomic, counted across every table it
        would have touched.
        """
        entries = [{"id": "a", "type": "book", "author": [{"family": "Kuhn"}], "issued": "2020"}]

        result = make_echo_format(entries)().import_file(io.StringIO())

        assert [entry.outcome for entry in result] == [Outcome.FAILED]
        assert _counts() == (0, 0, 0, 0)


@pytest.mark.django_db
class TestDryRun:
    """FR-015, FR-016, SC-004."""

    def test_created_entries_are_reported_but_nothing_is_stored(self):
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        before = _counts()

        result = make_echo_format(entries)().import_file(io.StringIO(), dry_run=True)

        assert len(result.created) == 2
        assert _counts() == before

    def test_a_failing_entrys_reason_appears_identically(self):
        entries = [{"kind": "entry_error", "reason": "unrecognised item type", "id": "a"}]

        result = make_echo_format(entries)().import_file(io.StringIO(), dry_run=True)

        assert len(result.failed) == 1
        assert result.failed[0].reason == "unrecognised item type"

    def test_result_states_whether_it_was_a_dry_run(self):
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        dry = make_echo_format(entries)().import_file(io.StringIO(), dry_run=True)
        real = make_echo_format(entries)().import_file(io.StringIO())

        assert dry.dry_run is True
        assert real.dry_run is False

    def test_outcomes_match_the_equivalent_real_run(self):
        """US2 scenario 4: a dry run and a real run over the same file agree."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "entry_error", "reason": "bad", "id": "b"},
            {"kind": "skip", "reason": "a comment"},
            {"kind": "good", "id": "c", "type": "book"},
        ]
        fmt = make_echo_format(entries)

        dry = fmt().import_file(io.StringIO(), dry_run=True)
        real = fmt().import_file(io.StringIO())

        assert [entry.outcome for entry in dry.entries] == [entry.outcome for entry in real.entries]
        assert [entry.reason for entry in dry.entries] == [entry.reason for entry in real.entries]
        assert [entry.handle for entry in dry.entries] == [entry.handle for entry in real.entries]

    def test_dry_run_entries_carry_no_item_even_when_created(self):
        """plan.md: exposing a rolled-back instance would hand back an object
        that looks saved and is not."""
        entries = [{"kind": "good", "id": "a", "type": "book"}]

        result = make_echo_format(entries)().import_file(io.StringIO(), dry_run=True)

        assert result.created[0].item is None

    def test_a_failing_entry_inside_a_dry_run_does_not_stop_the_rest(self):
        """The per-entry savepoint still protects the entries that follow,
        nested inside the outer rollback-only transaction."""
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "entry_error", "reason": "bad", "id": "b"},
            {"kind": "good", "id": "c", "type": "book"},
        ]
        before = _counts()

        result = make_echo_format(entries)().import_file(io.StringIO(), dry_run=True)

        assert [entry.outcome for entry in result.entries] == [
            Outcome.CREATED,
            Outcome.FAILED,
            Outcome.CREATED,
        ]
        assert _counts() == before

    def test_a_database_level_failure_inside_a_dry_run_does_not_poison_the_rest(self, bypass_identifier_validation):
        """research.md R2's savepoint-per-entry mechanism, exercised with the
        outer dry-run transaction also open — a genuine IntegrityError nested
        inside the rollback-only outer block must not prevent the entry after
        it from being reported as created."""
        entries = [
            {"kind": "good", "id": "a", "type": "book", "custom": DuplicateCustomIdentifier()},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        before = _counts()

        result = make_echo_format(entries)().import_file(io.StringIO(), dry_run=True)

        assert len(result.failed) == 1
        assert len(result.created) == 1
        assert _counts() == before


@pytest.mark.django_db(transaction=True)
class TestDryRunOutsideATestTransaction:
    """The same guarantee at the transaction level a real caller runs at.

    Every test above runs under non-transactional ``django_db``, so the
    runner's outer ``transaction.atomic()`` is a savepoint nested in the test's
    own transaction and ``set_rollback(True)`` takes Django's
    ``savepoint_rollback`` path. A caller in autocommit hits the other branch:
    the block is outermost and the rollback is a real ``connection.rollback()``.
    Nothing else in the suite exercises it.
    """

    def test_a_dry_run_stores_nothing(self):
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "good", "id": "b", "type": "book"},
        ]
        before = _counts()

        result = make_echo_format(entries)().import_file(io.StringIO(), dry_run=True)

        assert len(result.created) == 2
        assert _counts() == before

    def test_a_real_run_still_commits(self):
        """The counterpart: without the outer block, created entries persist."""
        entries = [{"kind": "good", "id": "a", "type": "book"}]
        items_before = Item.objects.count()

        result = make_echo_format(entries)().import_file(io.StringIO())

        assert len(result.created) == 1
        assert Item.objects.count() == items_before + 1


class SecondaryRouter:
    """Send every ``literature`` model to the ``secondary`` alias.

    What an installing project does when the catalogue lives somewhere other
    than its default database. This package is a reusable app, so that choice
    is never its own to make.
    """

    def db_for_read(self, model, **hints):
        return "secondary" if model._meta.app_label == "literature" else None

    db_for_write = db_for_read

    def allow_migrate(self, db, app_label, **hints):
        if app_label == "literature":
            return db == "secondary"
        return None


@pytest.mark.django_db(databases=["default", "secondary"], transaction=True)
class TestDryRunFollowsTheRouter:
    """FR-015 when the catalogue is not on the default connection.

    ``transaction.atomic()`` and ``set_rollback(True)`` both default to the
    ``default`` alias, while ``from_csl_json`` writes through whichever alias
    the router picks. When those differ, the outer transaction wrapped an idle
    connection and the rollback flag was set on it — so a dry run ran on the
    real connection with no transaction around it at all, committed every row,
    and reported ``dry_run=True`` with a list of created entries. The caller
    had no signal whatsoever.
    """

    @pytest.fixture(autouse=True)
    def _route_literature_elsewhere(self, settings):
        settings.DATABASE_ROUTERS = [SecondaryRouter()]

    def test_a_dry_run_stores_nothing_on_the_routed_database(self):
        entries = [
            {"kind": "good", "id": "a", "type": "book"},
            {"kind": "good", "id": "b", "type": "book"},
        ]

        result = make_echo_format(entries)().import_file(io.StringIO(), dry_run=True)

        assert result.dry_run is True
        assert len(result.created) == 2
        assert Item.objects.count() == 0

    def test_a_real_run_still_commits_on_the_routed_database(self):
        result = make_echo_format([{"kind": "good", "id": "a", "type": "book"}])().import_file(io.StringIO())

        assert len(result.created) == 1
        assert Item.objects.count() == 1

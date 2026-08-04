"""Tests for the ``BibFormat`` contract itself (data-model.md, contracts/importers.md).

A format supplies exactly two stages and may override a third. FR-003 is the
point of this module: nothing here gives a format a route to the stage that
builds an ``Item``, so the test asserts the absence of extra surface, not
only the presence of the three sanctioned members.
"""

import abc
import io

import pytest

from literature.importers.base import BibFormat
from literature.importers.results import EntryResult, ImportResult, Outcome
from literature.models import Item

from .conftest import make_echo_format


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


class TestFormatHasNoRouteToBuildingAnItem:
    """FR-003: a format supplies parse, to_csl_json, and (optionally) handle_for.

    Nothing else — no hook, override point, or attribute reaches the stage
    that builds an ``Item``. Checked by enumerating the class's own public
    surface rather than only confirming the three sanctioned members exist,
    since the risk this test guards against is something *extra* being
    added, not something required being missing.
    """

    def test_public_surface_is_exactly_the_three_stages(self):
        public_attrs = {name for name in vars(BibFormat) if not name.startswith("_")}
        assert public_attrs == {"parse", "to_csl_json", "handle_for"}


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

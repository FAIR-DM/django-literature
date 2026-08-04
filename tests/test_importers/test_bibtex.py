"""Tests for the BibTeX format (spec 004).

One test module per source module, per the constitution's rule that test
modules mirror the ``literature/`` tree. Concerns are separated by class
rather than by file, so this module grows as the stories land: registration
first, then mapping, cleaning, dialects and preservation.

Fixtures live in ``tests/fixtures/bibtex/``. See the README there for what
each file isolates and which of the two real exports is genuine.
"""

import dataclasses
from pathlib import Path

import pytest
from partial_date import PartialDate

from literature.importers import Outcome, available_formats, get_format
from literature.importers.base import BibFormat
from literature.importers.bibtex import (
    ENTRY_TYPE_TABLE,
    FIELD_TABLE,
    IDENTIFIER_FIELD_TABLE,
    NAME_FIELD_TABLE,
    BibTeXFormat,
)
from literature.importers.exceptions import SkipEntry
from literature.models import Item

FIXTURES = Path(__file__).parent.parent / "fixtures" / "bibtex"


def fixture(name):
    """Open a corpus file for reading, as a caller would hand one over."""
    return (FIXTURES / name).open(encoding="utf-8")


def entry(entry_type="misc", cite_key="x", **fields):
    """A minimal raw entry dict, shaped as ``bibtexparser`` would produce one.

    ``to_csl_json`` only needs the dict shape, not a real parse, so most
    mapping tests build one directly rather than routing a fixture through
    the parser.
    """
    return {"ENTRYTYPE": entry_type, "ID": cite_key, **fields}


def _is_source_field(bib_key: str) -> bool:
    """Whether ``bib_key`` is a field the source entry itself wrote.

    Excludes the two keys ``bibtexparser`` adds to every entry structurally
    (``ENTRYTYPE``, ``ID`` — already surfaced as ``type``/``citation-key``)
    and anything it prefixes with an underscore as its own bookkeeping
    (``_FROM_CROSSREF``, added once ``crossref`` inheritance resolves).
    Neither is something the source file stated (TestCorpusPreservation).
    """
    return bib_key not in {"ENTRYTYPE", "ID"} and not bib_key.startswith("_")


def _accounted_for(bib_key: str, csl: dict) -> bool:
    """Whether ``bib_key`` survived conversion, mapped or preserved (SC-006).

    Classified from the same tables ``to_csl_json`` itself reads rather than
    a hand-written list of field names, so a table entry the mapping code
    forgot to also emit would show up here as unmapped-and-not-preserved —
    the gap SC-006 exists to catch.
    """
    custom = csl.get("custom")
    custom = custom if isinstance(custom, dict) else {}
    bibtex_custom = custom.get("bibtex")
    bibtex_custom = bibtex_custom if isinstance(bibtex_custom, dict) else {}
    if bib_key in bibtex_custom or bib_key in custom:
        return True
    mapping = FIELD_TABLE.get(bib_key) or NAME_FIELD_TABLE.get(bib_key) or IDENTIFIER_FIELD_TABLE.get(bib_key)
    if mapping is not None:
        return mapping.csl in csl
    if bib_key in {"year", "month", "date"}:
        return "issued" in csl
    return False


def _parse_or_none(path: Path) -> list | None:
    """This file's raw entries, or ``None`` for one ``bibtexparser`` cannot
    even read (whole-file decoding failures, SC-008's territory).
    """
    with (FIXTURES / path.name).open(encoding="utf-8") as handle:
        try:
            return list(BibTeXFormat().parse(handle))
        except Exception:
            return None


class TestRegistration:
    """The format is reachable without configuration (FR-003, FR-027)."""

    def test_is_a_bibformat(self):
        assert issubclass(BibTeXFormat, BibFormat)

    def test_names_itself(self):
        assert BibTeXFormat.name == "bibtex"
        assert BibTeXFormat.label

    def test_reachable_from_the_importers_namespace(self):
        """Public names come from ``literature.importers``.

        Not from ``literature`` itself, which stays empty on purpose: a Django
        app's top-level ``__init__`` is imported before the app registry is
        populated, so re-exporting anything reaching the models would raise
        ``AppRegistryNotReady`` at startup (003 research R3).
        """
        import literature.importers as importers

        assert importers.BibTeXFormat is BibTeXFormat

    def test_shipped_by_default(self):
        """No configuration required (Article X, FR-003)."""
        assert "bibtex" in available_formats()

    def test_resolvable_by_name(self):
        assert get_format("bibtex") is BibTeXFormat

    def test_implements_the_stages_a_format_owns(self):
        assert not BibTeXFormat.__abstractmethods__


class TestParse:
    """``parse`` yields a file's entries in source order."""

    def test_yields_every_entry(self):
        with fixture("clean_multi_type.bib") as handle:
            entries = list(BibTeXFormat().parse(handle))
        assert len(entries) == 6

    def test_preserves_source_order(self):
        with fixture("clean_multi_type.bib") as handle:
            handles = [BibTeXFormat().handle_for(raw) for raw in BibTeXFormat().parse(handle)]
        assert handles == [
            "shannon1948mathematical",
            "knuth1984texbook",
            "lamport1978time",
            "codd1970relational",
            "berners1989information",
            "w3c2024standards",
        ]

    def test_is_an_iterator_not_a_list(self):
        """FR-004 depends on entries being consumable one at a time."""
        with fixture("clean_multi_type.bib") as handle:
            produced = BibTeXFormat().parse(handle)
            assert iter(produced) is iter(produced)

    def test_empty_file_yields_nothing(self):
        with fixture("empty.bib") as handle:
            assert list(BibTeXFormat().parse(handle)) == []


class TestHandles:
    """The cite key is what a reader searches for (FR-012)."""

    def test_handle_is_the_cite_key(self):
        with fixture("clean_multi_type.bib") as handle:
            first = next(iter(BibTeXFormat().parse(handle)))
        assert BibTeXFormat().handle_for(first) == "shannon1948mathematical"

    @pytest.mark.django_db
    def test_handle_is_also_the_built_items_citation_key(self):
        """The same cite key names the entry in the report and the stored Item."""
        with fixture("clean_multi_type.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert [e.handle for e in result.created] == [
            "shannon1948mathematical",
            "knuth1984texbook",
            "lamport1978time",
            "codd1970relational",
            "berners1989information",
            "w3c2024standards",
        ]
        assert set(Item.objects.values_list("citation_key", flat=True)) == {e.handle for e in result.created}


class TestEntryTypes:
    """Every classic entry type maps to its CSL item type (FR-006)."""

    @pytest.mark.parametrize(("bibtex_type", "mapping"), sorted(ENTRY_TYPE_TABLE.items()))
    def test_every_classic_type_maps_to_its_csl_equivalent(self, bibtex_type, mapping):
        assert BibTeXFormat().to_csl_json(entry(entry_type=bibtex_type))["type"] == mapping.csl

    @pytest.mark.parametrize("bibtex_type", ["set", "xdata", ""])
    def test_an_unrecognised_type_maps_to_document_rather_than_failing(self, bibtex_type):
        """``set`` and ``xdata`` are real BibLaTeX types with no CSL meaning:
        one groups other entries, the other only supplies fields to them.
        They are the examples here because they are the two the entry-type
        table is expected never to carry, so this test cannot be made to fail
        by mapping more of BibLaTeX correctly.
        """
        assert BibTeXFormat().to_csl_json(entry(entry_type=bibtex_type))["type"] == "document"

    def test_unknown_types_from_the_corpus_land_as_document(self):
        """``unknown_entry_type.bib``: neither type maps to a CSL type."""
        with fixture("unknown_entry_type.bib") as handle:
            raws = list(BibTeXFormat().parse(handle))
        assert [BibTeXFormat().to_csl_json(raw)["type"] for raw in raws] == ["document", "document"]


class TestFields:
    """Every classic BibTeX field maps to its documented CSL variable (FR-007)."""

    @pytest.mark.parametrize(("bibtex_field", "mapping"), sorted(FIELD_TABLE.items()))
    def test_every_classic_field_maps_to_its_csl_variable(self, bibtex_field, mapping):
        raw = entry(**{bibtex_field: "some value"})
        assert BibTeXFormat().to_csl_json(raw)[mapping.csl] == "some value"


class TestNames:
    """Contributor lists keep source order and role (FR-008, FR-009)."""

    def test_authors_keep_source_order_and_role(self):
        raw = entry(author="Shannon, Claude E. and Doe, Jane")
        csl = BibTeXFormat().to_csl_json(raw)
        assert csl["author"] == [
            {"given": "Claude E.", "family": "Shannon"},
            {"given": "Jane", "family": "Doe"},
        ]

    def test_editors_land_under_their_own_role(self):
        raw = entry(editor="Editor, Enid")
        csl = BibTeXFormat().to_csl_json(raw)
        assert csl["editor"] == [{"given": "Enid", "family": "Editor"}]
        assert "author" not in csl

    def test_von_particle_lands_as_non_dropping_particle(self):
        raw = entry(author="van Beethoven, Ludwig")
        csl = BibTeXFormat().to_csl_json(raw)
        assert csl["author"] == [{"given": "Ludwig", "family": "Beethoven", "non-dropping-particle": "van"}]

    def test_jr_suffix_lands_as_suffix(self):
        raw = entry(author="King, Jr., Martin Luther")
        csl = BibTeXFormat().to_csl_json(raw)
        assert csl["author"] == [{"given": "Martin Luther", "family": "King", "suffix": "Jr."}]

    def test_first_von_last_form_is_understood_too(self):
        raw = entry(author="Ludwig van Beethoven")
        csl = BibTeXFormat().to_csl_json(raw)
        assert csl["author"] == [{"given": "Ludwig", "family": "Beethoven", "non-dropping-particle": "van"}]

    def test_brace_wrapped_institutional_name_goes_to_literal_unsplit(self):
        with fixture("clean_multi_type.bib") as handle:
            raws = list(BibTeXFormat().parse(handle))
        w3c = next(raw for raw in raws if raw["ID"] == "w3c2024standards")
        csl = BibTeXFormat().to_csl_json(w3c)
        assert csl["author"] == [{"literal": "World Wide Web Consortium"}]


class TestDates:
    """Dates are stored at the precision the source states (FR-010)."""

    def test_year_alone_gives_year_precision(self):
        raw = entry(year="1978")
        assert BibTeXFormat().to_csl_json(raw)["issued"] == {"date-parts": [[1978]]}

    def test_year_and_numeric_month_give_month_precision(self):
        raw = entry(year="1948", month="7")
        assert BibTeXFormat().to_csl_json(raw)["issued"] == {"date-parts": [[1948, 7]]}

    def test_no_year_means_no_issued_date(self):
        assert "issued" not in BibTeXFormat().to_csl_json(entry())

    def test_a_spelled_out_month_macro_resolves_to_its_number(self):
        """``string_macros.bib``: ``month = jan`` expands to ``January`` (FR-013)."""
        with fixture("string_macros.bib") as handle:
            raws = list(BibTeXFormat().parse(handle))
        hopper = next(raw for raw in raws if raw["ID"] == "uses_macro_two")
        assert BibTeXFormat().to_csl_json(hopper)["issued"] == {"date-parts": [[1952, 1]]}

    def test_bare_full_month_name_does_not_pad_a_day(self):
        """``real_crossref_classic.bib`` writes bare ``month=July`` (no day stated)."""
        with fixture("real_crossref_classic.bib") as handle:
            raws = list(BibTeXFormat().parse(handle))
        akiba = next(raw for raw in raws if raw["ID"] == "Akiba_2019")
        assert BibTeXFormat().to_csl_json(akiba)["issued"] == {"date-parts": [[2019, 7]]}


class TestIdentifiers:
    """DOI, ISBN, ISSN and URL become typed identifier records (FR-011)."""

    def test_doi_isbn_and_url_from_the_clean_corpus(self):
        with fixture("clean_multi_type.bib") as handle:
            raws = {raw["ID"]: raw for raw in BibTeXFormat().parse(handle)}

        shannon = BibTeXFormat().to_csl_json(raws["shannon1948mathematical"])
        assert shannon["DOI"] == "10.1002/j.1538-7305.1948.tb01338.x"

        knuth = BibTeXFormat().to_csl_json(raws["knuth1984texbook"])
        assert knuth["ISBN"] == "0-201-13447-0"

        w3c = BibTeXFormat().to_csl_json(raws["w3c2024standards"])
        assert w3c["URL"] == "https://www.w3.org/standards/"

    def test_issn_from_a_real_export(self):
        with fixture("real_crossref_classic.bib") as handle:
            raws = list(BibTeXFormat().parse(handle))
        lecun = next(raw for raw in raws if raw["ID"] == "LeCun_2015")
        assert BibTeXFormat().to_csl_json(lecun)["ISSN"] == "1476-4687"

    def test_no_identifier_fields_means_no_identifier_keys(self):
        csl = BibTeXFormat().to_csl_json(entry())
        assert not ({"DOI", "ISBN", "ISSN", "URL"} & csl.keys())

    def test_identifier_field_names_are_looked_up_case_insensitively(self):
        """``real_crossref_classic.bib`` carries uppercase ``ISSN`` and ``DOI``.

        The case-folding is ``bibtexparser``'s own (every field key is
        lowercased while parsing), so this is really an assertion that
        nothing here undoes it.
        """
        with fixture("real_crossref_classic.bib") as handle:
            raws = list(BibTeXFormat().parse(handle))
        lecun = next(raw for raw in raws if raw["ID"] == "LeCun_2015")
        csl = BibTeXFormat().to_csl_json(lecun)
        assert csl["DOI"] == "10.1038/nature14539"
        assert csl["ISSN"] == "1476-4687"


class TestBlocks:
    """``@string`` macros expand; ``@comment``/``@preamble`` are skipped (FR-013, FR-014, FR-016)."""

    def test_string_macros_are_expanded_in_referencing_entries(self):
        with fixture("string_macros.bib") as handle:
            raws = {raw["ID"]: raw for raw in BibTeXFormat().parse(handle)}

        franklin = BibTeXFormat().to_csl_json(raws["uses_macro"])
        assert franklin["container-title"] == "Journal of Biology"

        hopper = BibTeXFormat().to_csl_json(raws["uses_macro_two"])
        assert hopper["container-title"] == "ACM Computing Surveys"

    @pytest.mark.django_db
    def test_comments_and_preamble_are_skipped_not_failed_and_create_no_item(self):
        with fixture("comments_and_preamble.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok
        assert [e.outcome for e in result] == [Outcome.CREATED, Outcome.SKIPPED, Outcome.SKIPPED]
        assert Item.objects.count() == 1
        assert Item.objects.get().citation_key == "after_the_blocks"

    def test_a_field_repeated_in_one_entry_keeps_the_first_occurrence(self):
        """FR-016: the rule is documented here and in ``bibtex.py`` — first wins,
        which is ``bibtexparser``'s own field-parsing behaviour, not something
        this format chooses independently.
        """
        with fixture("duplicate_field.bib") as handle:
            raw = next(iter(BibTeXFormat().parse(handle)))
        assert BibTeXFormat().to_csl_json(raw)["title"] == "First Title"

    @pytest.mark.django_db
    def test_a_zero_field_entry_is_swallowed_as_a_comment_by_the_parser(self):
        """``sparse_entry.bib`` documents a real limitation, not a design choice.

        ``bibtexparser`` 1.4.4's grammar requires at least one field inside an
        entry; ``@misc{bare_minimum,\\n}`` fails to match the entry rule and
        falls through to the ``implicit_comment`` rule instead, so it never
        reaches ``to_csl_json`` as an entry at all. The corpus fixture and
        spec.md's edge case ("Sparse is not invalid") both expect this entry
        to be *stored*; the parser this story depends on cannot deliver that
        without hand-rolled pre-parsing, which research.md rejected. Recorded
        as a concern rather than worked around (decisions.md D11).
        """
        with fixture("sparse_entry.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert [e.outcome for e in result] == [Outcome.SKIPPED]
        assert Item.objects.count() == 0


class TestCrossref:
    """``crossref`` inheritance resolves regardless of file order (FR-015)."""

    @pytest.mark.django_db
    def test_a_forward_reference_inherits_the_later_parents_fields(self):
        with fixture("crossref_forward.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok
        assert [e.outcome for e in result] == [Outcome.CREATED, Outcome.CREATED]
        assert [e.handle for e in result] == ["chapter_referencing_later_parent", "the_parent_book"]

        chapter = Item.objects.get(citation_key="chapter_referencing_later_parent")
        assert chapter.title == "A Chapter In A Collection"
        assert chapter.publisher == "University Press"
        assert chapter.item_dates.get(date_type="issued").begin.date.year == 1995

    @pytest.mark.django_db
    def test_a_cycle_terminates_and_each_entry_still_imports_with_its_own_fields(self):
        with fixture("crossref_cycle.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert [e.outcome for e in result] == [Outcome.CREATED, Outcome.CREATED, Outcome.CREATED]
        assert {item.title for item in Item.objects.all()} == {
            "Entry A",
            "Entry B",
            "Entry That References Itself",
        }

    @pytest.mark.django_db
    def test_a_crossref_to_a_missing_entry_does_not_fail_the_entry(self):
        with fixture("crossref_missing.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert [e.outcome for e in result] == [Outcome.CREATED]


class TestCleaning:
    """Recoverable malformations are normalized before mapping (FR-017, FR-018)."""

    def test_doi_as_a_resolver_url_normalizes_to_the_bare_identifier(self):
        with fixture("doi_as_url.bib") as handle:
            raws = {raw["ID"]: raw for raw in BibTeXFormat().parse(handle)}

        full = BibTeXFormat().to_csl_json(raws["doi_full_url"])
        assert full["DOI"] == "10.1234/example.2021.001"

        dx = BibTeXFormat().to_csl_json(raws["doi_dx_url"])
        assert dx["DOI"] == "10.1234/example.2021.002"

    def test_doi_carrying_a_label_normalizes_to_the_bare_identifier(self):
        with fixture("doi_labelled.bib") as handle:
            raw = next(iter(BibTeXFormat().parse(handle)))
        assert BibTeXFormat().to_csl_json(raw)["DOI"] == "10.1234/example.2022.001"

    def test_an_isbn_carrying_a_redundant_label_normalizes_to_the_bare_identifier(self):
        """No export in the corpus writes a labelled ISBN, so the behaviour is
        pinned on a constructed entry rather than through a fixture — without
        this the normalizer runs on every clean ISBN and is never asked to
        strip anything.
        """
        raw = {"ENTRYTYPE": "book", "ID": "labelled_isbn", "isbn": "ISBN-13: 0-201-13447-0"}
        assert BibTeXFormat().to_csl_json(raw)["ISBN"] == "0-201-13447-0"

    def test_latex_accents_decode_to_the_characters_they_represent(self):
        with fixture("latex_escapes.bib") as handle:
            raw = next(iter(BibTeXFormat().parse(handle)))
        csl = BibTeXFormat().to_csl_json(raw)
        assert csl["author"] == [
            {"given": "Hans", "family": "Krüger"},
            {"given": "María", "family": "Álvarez"},
            {"given": "Jørgen", "family": "Weiß"},
        ]

    def test_capitalization_protecting_braces_are_removed(self):
        with fixture("latex_escapes.bib") as handle:
            raw = next(iter(BibTeXFormat().parse(handle)))
        csl = BibTeXFormat().to_csl_json(raw)
        assert csl["title"] == "A Study of DNA Sequencing in Århus"
        assert "{" not in csl["title"]
        assert "}" not in csl["title"]

    def test_a_construct_the_decoder_does_not_recognise_is_left_visible_not_dropped(self):
        """``unknown_macro2020``: the decoder knows ``\\u`` as an accent command,

        so ``\\unknownmacro`` is not left untouched character-for-character —
        but nothing from the source is discarded either. ``\\textcelsius`` has
        no unicode equivalent bibtexparser knows, so it is left exactly as
        written, backslash and all.
        """
        with fixture("latex_escapes.bib") as handle:
            raws = list(BibTeXFormat().parse(handle))
        raw = next(r for r in raws if r["ID"] == "unknown_macro2020")
        title = BibTeXFormat().to_csl_json(raw)["title"]
        assert "\\textcelsius" in title
        assert "knownmacrox" in title


class TestRecovery:
    """A value cleaning cannot rescue is preserved, not failed (FR-019, FR-020, FR-021)."""

    @pytest.mark.django_db
    def test_an_identifier_that_still_will_not_validate_after_cleaning_is_preserved(self):
        with fixture("doi_labelled.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok, [e.reason for e in result.failed]
        assert [e.outcome for e in result] == [Outcome.CREATED, Outcome.CREATED]

        item = Item.objects.get(citation_key="doi_not_a_doi")
        assert "DOI" not in [i.type for i in item.item_identifiers.all()]
        preserved = item.item_identifiers.get(type="doi")
        assert preserved.value == "see the publisher website"

    @pytest.mark.django_db
    def test_an_unresolvable_date_lands_in_the_records_own_fallback(self):
        with fixture("unparseable_date.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok, [e.reason for e in result.failed]
        assert [e.outcome for e in result] == [Outcome.CREATED, Outcome.CREATED]

        nonsense = Item.objects.get(citation_key="date_nonsense")
        issued = nonsense.item_dates.get(date_type="issued")
        assert issued.begin is None
        assert issued.literal == "in press"

        range_text = Item.objects.get(citation_key="date_range_text")
        issued = range_text.item_dates.get(date_type="issued")
        assert issued.begin is None
        assert issued.literal == "Spring 1999--2000"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "filename", ["doi_as_url.bib", "doi_labelled.bib", "unparseable_date.bib", "latex_escapes.bib"]
    )
    def test_no_recoverable_malformation_fails_its_entry(self, filename):
        """FR-021: with cleaning and preservation in place, none of these
        constructed malformations cost an entry — every one is created.
        """
        with fixture(filename) as handle:
            result = BibTeXFormat().import_file(handle)
        assert result.ok, [e.reason for e in result.failed]
        assert all(e.outcome == Outcome.CREATED for e in result)


class TestCorpusRecovery:
    """SC-002, across the whole committed corpus: no entry is refused for a
    reason normalization resolves, and every refusal names what could not
    be recovered.
    """

    #: A file that is not valid UTF-8 fails before any entry exists to
    #: clean — the whole file is unreadable (FR-014), which is SC-008's
    #: territory, not a value cleaning could ever have reached.
    _WHOLE_FILE_UNREADABLE = {"latin1_encoded.bib"}

    @pytest.mark.django_db
    def test_no_entry_across_the_corpus_is_refused_for_a_reason_normalization_resolves(self):
        failures: list[str] = []
        for path in sorted(FIXTURES.glob("*.bib")):
            with fixture(path.name) as handle:
                result = BibTeXFormat().import_file(handle, dry_run=True)
            for entry_result in result:
                if entry_result.outcome is Outcome.FAILED:
                    assert entry_result.reason, f"{path.name}#{entry_result.index} failed with no reason"
                    failures.append(path.name)

        assert set(failures) <= self._WHOLE_FILE_UNREADABLE, (
            f"entries failed outside the known whole-file-unreadable cases: {failures}"
        )


class TestCorpusAcceptance:
    """The acceptance-level checks TASK_BRIEF names directly."""

    @pytest.mark.django_db
    def test_clean_multi_type_creates_one_item_per_entry_as_expected(self):
        with fixture("clean_multi_type.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok
        assert len(result.created) == 6

        by_key = {item.citation_key: item for item in Item.objects.all()}
        assert by_key["shannon1948mathematical"].type == "article-journal"
        assert by_key["knuth1984texbook"].type == "book"
        assert by_key["lamport1978time"].type == "paper-conference"
        assert by_key["codd1970relational"].type == "thesis"
        assert by_key["berners1989information"].type == "report"
        assert by_key["w3c2024standards"].type == "document"

    @pytest.mark.django_db
    def test_real_crossref_classic_imports_correctly(self):
        """A genuine Crossref export: uppercase field names, bare month macros,
        ``&amp;`` entities left as-is (decoding is US2), Unicode en-dashes.
        """
        with fixture("real_crossref_classic.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok, [e.reason for e in result.failed]
        assert len(result.created) == 6
        assert Item.objects.count() == 6


class TestBibLaTeX:
    """A BibLaTeX export reads the same way a classic one does (FR-022, FR-023).

    ``constructed_biblatex.bib`` is written to follow Zotero's and JabRef's
    BibLaTeX-exporter conventions (README, D9): ``journaltitle`` over
    ``journal``, a single ``date`` field, and entry types classic BibTeX has
    no equivalent for.
    """

    def test_journaltitle_maps_to_container_title_exactly_as_journal_does(self):
        raw = entry(journaltitle="Nature")
        assert BibTeXFormat().to_csl_json(raw)["container-title"] == "Nature"

    @pytest.mark.parametrize(
        ("date", "date_parts"),
        [
            ("2015-05-28", [2015, 5, 28]),
            ("2024-01", [2024, 1]),
            ("1970", [1970]),
        ],
    )
    def test_a_single_date_field_stores_at_the_precision_it_states(self, date, date_parts):
        raw = entry(date=date)
        assert BibTeXFormat().to_csl_json(raw)["issued"] == {"date-parts": [date_parts]}

    def test_a_date_field_in_a_shape_this_importer_does_not_resolve_falls_back_to_literal(self):
        """A range, a valid BibLaTeX ``date`` shape, is not one of the
        year/year-month/full-date precisions FR-010 asks this importer to
        resolve. Not discarded either way (FR-020) — the same fallback an
        unparseable classic ``year`` already uses.
        """
        raw = entry(date="2019/2020")
        assert BibTeXFormat().to_csl_json(raw)["issued"] == {"literal": "2019/2020"}

    @pytest.mark.parametrize(
        ("bibtex_type", "mapping"),
        sorted(item for item in ENTRY_TYPE_TABLE.items() if item[1].dialect == "biblatex"),
    )
    def test_every_biblatex_only_type_maps_to_a_real_csl_type_not_the_fallback(self, bibtex_type, mapping):
        csl_type = BibTeXFormat().to_csl_json(entry(entry_type=bibtex_type))["type"]
        assert csl_type == mapping.csl
        assert csl_type != "document"

    @pytest.mark.django_db
    def test_constructed_biblatex_corpus_imports_with_real_types_container_titles_and_date_precision(self):
        with fixture("constructed_biblatex.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok, [e.reason for e in result.failed]
        assert len(result.created) == 7
        assert "document" not in {item.type for item in Item.objects.all()}

        by_key = {item.citation_key: item for item in Item.objects.all()}
        assert by_key["lecun2015deep"].type == "article-journal"
        assert by_key["lecun2015deep"].container_title == "Nature"
        assert by_key["w3c2024standards"].type == "webpage"
        assert by_key["codd1970relational"].type == "thesis"
        assert by_key["berners1989information"].type == "report"
        assert by_key["collected1995"].type == "collection"
        assert by_key["chapter1995"].type == "chapter"

        assert by_key["lecun2015deep"].item_dates.get(date_type="issued").begin == PartialDate("2015-05-28")
        assert by_key["w3c2024standards"].item_dates.get(date_type="issued").begin == PartialDate("2024-01")
        assert by_key["codd1970relational"].item_dates.get(date_type="issued").begin == PartialDate("1970")

    @pytest.mark.django_db
    def test_a_file_mixing_both_conventions_across_entries_imports_correctly(self):
        """FR-023 acceptance scenario 4: every entry reads correctly without
        anyone naming a dialect, whether it writes classic or BibLaTeX field
        names and entry types.
        """
        with fixture("constructed_biblatex.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok, [e.reason for e in result.failed]
        assert all(e.outcome == Outcome.CREATED for e in result)


class TestPrecedence:
    """Where the dialects supply the same information twice and disagree,
    resolution is deterministic (FR-024). The direction: the BibLaTeX field
    wins over its classic counterpart (D17).
    """

    def test_conflicting_date_and_year_resolve_to_the_biblatex_date(self):
        raw = entry(date="2019-03", year="2018")
        assert BibTeXFormat().to_csl_json(raw)["issued"] == {"date-parts": [[2019, 3]]}

    def test_a_date_and_year_that_agree_resolve_the_same_way_either_would_alone(self):
        raw = entry(date="2018", year="2018")
        assert BibTeXFormat().to_csl_json(raw)["issued"] == {"date-parts": [[2018]]}

    def test_conflicting_journaltitle_and_journal_resolve_to_journaltitle(self):
        raw = entry(journal="Classic Field Name", journaltitle="BibLaTeX Field Name")
        assert BibTeXFormat().to_csl_json(raw)["container-title"] == "BibLaTeX Field Name"

    def test_a_journaltitle_and_journal_that_agree_resolve_the_same_way_either_would_alone(self):
        raw = entry(journal="Nature", journaltitle="Nature")
        assert BibTeXFormat().to_csl_json(raw)["container-title"] == "Nature"

    def test_the_corpus_mixed_dialect_entry_resolves_both_conflicts_deterministically(self):
        """``mixed_dialect_entry`` in ``constructed_biblatex.bib`` carries both
        forms of both conflicts at once: ``journal`` vs. ``journaltitle``, and
        ``year`` vs. ``date``.
        """
        with fixture("constructed_biblatex.bib") as handle:
            raws = {raw["ID"]: raw for raw in BibTeXFormat().parse(handle)}
        csl = BibTeXFormat().to_csl_json(raws["mixed_dialect_entry"])
        assert csl["container-title"] == "BibLaTeX Field Name"
        assert csl["issued"] == {"date-parts": [[2019, 3]]}


class TestDialectEquivalence:
    """SC-005: the same library exported as classic BibTeX and as BibLaTeX
    produces equivalent catalogue records, judged on item type, contributors
    and their order, dates and their precision, and identifiers.

    ``equivalence_classic.bib`` is three entries lifted verbatim from
    ``real_crossref_classic.bib`` (a genuine Crossref export, D9);
    ``equivalence_biblatex.bib`` writes the same three references in
    BibLaTeX convention. See the corpus README for how the pair was built.
    """

    @pytest.mark.django_db
    def test_the_equivalence_pair_produce_equivalent_records(self):
        with fixture("equivalence_classic.bib") as handle:
            classic_result = BibTeXFormat().import_file(handle)
        with fixture("equivalence_biblatex.bib") as handle:
            biblatex_result = BibTeXFormat().import_file(handle)

        assert classic_result.ok, [e.reason for e in classic_result.failed]
        assert biblatex_result.ok, [e.reason for e in biblatex_result.failed]
        assert len(classic_result.created) == 3
        assert len(biblatex_result.created) == 3

        # Both sides are read off their own result entries, never looked up by
        # cite key: the second import's keys collide with the first's and are
        # de-collided on the way in (``LeCun_2015`` then ``LeCun_2015b``), so a
        # lookup by ``handle`` returns the classic row on both sides and the
        # comparison below comes out true against itself.
        classic_by_key = {e.handle: e.item for e in classic_result.created}
        biblatex_by_key = {e.handle: e.item for e in biblatex_result.created}
        assert classic_by_key.keys() == biblatex_by_key.keys()
        assert not {item.pk for item in classic_by_key.values()} & {item.pk for item in biblatex_by_key.values()}

        def contributors(item):
            return [
                (name.role, name.name.given, name.name.family) for name in item.item_names.order_by("role", "order")
            ]

        def identifiers(item):
            return {i.type: i.value for i in item.item_identifiers.all()}

        for key in classic_by_key:
            classic_item = classic_by_key[key]
            biblatex_item = biblatex_by_key[key]

            assert classic_item.type == biblatex_item.type, key
            assert contributors(classic_item) == contributors(biblatex_item), key
            # Beyond SC-005's four criteria, and deliberately: ``journal``
            # against ``journaltitle`` is one of only two ways the pair
            # differs, so leaving it out would let half the difference this
            # fixture exists to exercise break without the test noticing.
            assert classic_item.container_title == biblatex_item.container_title, key

            classic_issued = classic_item.item_dates.get(date_type="issued")
            biblatex_issued = biblatex_item.item_dates.get(date_type="issued")
            assert classic_issued.begin == biblatex_issued.begin, key

            assert identifiers(classic_item) == identifiers(biblatex_item), key


class TestPreservation:
    """Nothing a source entry carried is thrown away (FR-025, FR-026, D3, D20).

    Reference-manager bookkeeping — ``file``, ``owner``, ``timestamp``,
    ``groups``, ``mendeley-tags``, ``bdsk-url-1``, ``readstatus`` in
    ``unknown_fields.bib`` — maps to no CSL variable and has no column of its
    own, but is still retrievable from the stored record afterwards.
    """

    def test_unmapped_fields_are_collected_under_a_single_bibtex_key(self):
        raw = entry(file=":home/sam/papers/x.pdf:PDF", owner="sam", timestamp="2024-03-11")
        csl = BibTeXFormat().to_csl_json(raw)
        assert csl["custom"]["bibtex"] == {
            "file": ":home/sam/papers/x.pdf:PDF",
            "owner": "sam",
            "timestamp": "2024-03-11",
        }

    def test_an_entry_with_no_unmapped_fields_carries_no_custom_key(self):
        assert "custom" not in BibTeXFormat().to_csl_json(entry(title="Plain"))

    def test_the_sorting_key_field_is_preserved_too(self):
        """``key`` is BibTeX's own sorting hint (FIELD_TABLE's module comment);
        it has no CSL equivalent and is not consumed by anything else here.
        """
        raw = entry(key="alpha-sort")
        assert BibTeXFormat().to_csl_json(raw)["custom"]["bibtex"] == {"key": "alpha-sort"}

    @pytest.mark.django_db
    def test_unmapped_fields_are_retrievable_from_the_stored_item(self):
        with fixture("unknown_fields.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok, [e.reason for e in result.failed]
        item = Item.objects.get(citation_key="manager_bookkeeping")
        assert item.custom["bibtex"] == {
            "file": ":home/sam/papers/curie1898.pdf:PDF",
            "owner": "sam",
            "timestamp": "2024-03-11",
            "groups": "Physics/Classics",
            "mendeley-tags": "radioactivity;classics",
            "bdsk-url-1": "https://example.org/curie",
            "readstatus": "read",
        }
        # The general sweep this story adds is not US2's narrow D13 rescue —
        # none of this bookkeeping is an identifier field, so none of it is
        # promoted to an ``ItemIdentifier`` row.
        assert item.item_identifiers.count() == 0

    @pytest.mark.django_db
    def test_reported_as_created_with_no_additional_outcome_or_reporting_surface(self):
        """FR-026: indistinguishable from an entry with no unmapped fields —
        same outcome, no new ``Outcome`` value, no per-field reporting.
        """
        with fixture("unknown_fields.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert [e.outcome for e in result] == [Outcome.CREATED]
        assert set(Outcome) == {Outcome.CREATED, Outcome.SKIPPED, Outcome.FAILED}

        entry_result = result.created[0]
        assert entry_result.reason is None
        assert {f.name for f in dataclasses.fields(entry_result)} == {"outcome", "index", "handle", "item", "reason"}

    @pytest.mark.django_db
    def test_an_unresolvable_crossref_is_preserved_as_an_ordinary_unmapped_field(self):
        """Acceptance scenario 3: a ``crossref`` naming an entry the file does
        not contain resolves nothing, but is not dropped either, and does not
        fail the entry it appears on.
        """
        with fixture("crossref_missing.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert [e.outcome for e in result] == [Outcome.CREATED]
        item = Item.objects.get(citation_key="references_absent_parent")
        assert item.custom["bibtex"]["crossref"] == "a_book_that_is_not_here"

    @pytest.mark.django_db
    def test_a_resolved_crossref_is_preserved_the_same_way_with_no_special_case(self):
        """``crossref`` names no CSL variable whether or not it resolves, so
        the same rule preserves it either way (no branch keyed on success).
        ``_FROM_CROSSREF`` — the parser's own record of which fields were
        inherited, not something the source file wrote — is not a field of
        this entry and must not leak into the preserved bookkeeping.
        """
        with fixture("crossref_forward.bib") as handle:
            result = BibTeXFormat().import_file(handle)

        assert result.ok, [e.reason for e in result.failed]
        chapter = Item.objects.get(citation_key="chapter_referencing_later_parent")
        assert chapter.custom["bibtex"] == {"crossref": "the_parent_book"}


class TestCorpusPreservation:
    """SC-006, across the whole committed corpus: every field a source entry
    carries is either mapped to a CSL variable or retrievable from the stored
    record afterwards, and none is absent from both.
    """

    def test_every_field_in_every_corpus_entry_is_mapped_or_preserved(self):
        gaps: list[str] = []
        for path in sorted(FIXTURES.glob("*.bib")):
            raws = _parse_or_none(path)
            if raws is None:
                # A file bibtexparser cannot even read (``latin1_encoded.bib``)
                # supplies no entry with fields to check here — SC-008's
                # territory, not SC-006's.
                continue
            for raw in raws:
                try:
                    csl = BibTeXFormat().to_csl_json(raw)
                except SkipEntry:
                    continue
                for bib_key, value in raw.items():
                    if _is_source_field(bib_key) and value and not _accounted_for(bib_key, csl):
                        gaps.append(f"{path.name}#{raw.get('ID')}: {bib_key!r}")

        assert not gaps

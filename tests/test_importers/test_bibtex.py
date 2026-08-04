"""Tests for the BibTeX format (spec 004).

One test module per source module, per the constitution's rule that test
modules mirror the ``literature/`` tree. Concerns are separated by class
rather than by file, so this module grows as the stories land: registration
first, then mapping, cleaning, dialects and preservation.

Fixtures live in ``tests/fixtures/bibtex/``. See the README there for what
each file isolates and which of the two real exports is genuine.
"""

from pathlib import Path

import pytest

from literature.importers import Outcome, available_formats, get_format
from literature.importers.base import BibFormat
from literature.importers.bibtex import ENTRY_TYPE_TABLE, FIELD_TABLE, BibTeXFormat
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

    @pytest.mark.parametrize("bibtex_type", ["artwork", "dataset", "patent", ""])
    def test_an_unrecognised_type_maps_to_document_rather_than_failing(self, bibtex_type):
        assert BibTeXFormat().to_csl_json(entry(entry_type=bibtex_type))["type"] == "document"

    def test_unknown_types_from_the_corpus_land_as_document(self):
        """``unknown_entry_type.bib``: neither type is classic BibTeX."""
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

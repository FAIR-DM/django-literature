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

from literature.importers import available_formats, get_format
from literature.importers.base import BibFormat
from literature.importers.bibtex import ENTRY_TYPE_TABLE, FIELD_TABLE, BibTeXFormat

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

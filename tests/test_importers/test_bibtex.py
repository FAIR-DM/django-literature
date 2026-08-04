"""Tests for the BibTeX format (spec 004).

One test module per source module, per the constitution's rule that test
modules mirror the ``literature/`` tree. Concerns are separated by class
rather than by file, so this module grows as the stories land: registration
first, then mapping, cleaning, dialects and preservation.

Fixtures live in ``tests/fixtures/bibtex/``. See the README there for what
each file isolates and which of the two real exports is genuine.
"""

from pathlib import Path

from literature.importers import available_formats, get_format
from literature.importers.base import BibFormat
from literature.importers.bibtex import BibTeXFormat

FIXTURES = Path(__file__).parent.parent / "fixtures" / "bibtex"


def fixture(name):
    """Open a corpus file for reading, as a caller would hand one over."""
    return (FIXTURES / name).open(encoding="utf-8")


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

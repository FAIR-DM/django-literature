"""Tests for shared identifier normalization (spec 005 T005).

``IdentifierNormalizer`` is exactly the two format-neutral helpers extracted from
``bibtex.py`` — ``_normalize_doi`` and ``_normalize_isbn`` — moved verbatim, per Article XV,
onto a class both the BibTeX and RIS formats can call (plan.md "Shared normalization").
"""

from literature.importers.normalizers import IdentifierNormalizer


class TestNormalizeDoi:
    """Strips a resolver URL prefix or a ``doi:`` label, leaving the bare DOI (FR-025)."""

    def test_strips_https_doi_org_prefix(self):
        assert IdentifierNormalizer.normalize_doi("https://doi.org/10.1234/x") == "10.1234/x"

    def test_strips_dx_doi_org_prefix(self):
        assert IdentifierNormalizer.normalize_doi("http://dx.doi.org/10.1234/x") == "10.1234/x"

    def test_strips_doi_label(self):
        assert IdentifierNormalizer.normalize_doi("doi:10.1234/x") == "10.1234/x"

    def test_strips_doi_label_case_insensitively(self):
        assert IdentifierNormalizer.normalize_doi("DOI: 10.1234/x") == "10.1234/x"

    def test_strips_a_label_and_a_url_combined(self):
        assert IdentifierNormalizer.normalize_doi("doi:https://doi.org/10.1234/x") == "10.1234/x"

    def test_leaves_a_bare_doi_unchanged(self):
        assert IdentifierNormalizer.normalize_doi("10.1234/x") == "10.1234/x"

    def test_strips_surrounding_whitespace(self):
        assert IdentifierNormalizer.normalize_doi("  10.1234/x  ") == "10.1234/x"


class TestNormalizeIsbn:
    """Strips a redundant ``isbn:``/``isbn-13:`` label (FR-025)."""

    def test_strips_isbn_label(self):
        assert IdentifierNormalizer.normalize_isbn("isbn:0-201-13447-0") == "0-201-13447-0"

    def test_strips_isbn13_label(self):
        assert IdentifierNormalizer.normalize_isbn("ISBN-13: 9780201134476") == "9780201134476"

    def test_leaves_a_bare_isbn_unchanged(self):
        assert IdentifierNormalizer.normalize_isbn("0-201-13447-0") == "0-201-13447-0"

    def test_strips_surrounding_whitespace(self):
        assert IdentifierNormalizer.normalize_isbn("  0-201-13447-0  ") == "0-201-13447-0"

"""Tests for literature.validators — FR-020 identifier value validation.

Covers valid/invalid values for each known identifier type and verifies that
unknown identifier types accept any value string without error.
"""

import pytest
from django.core.exceptions import ValidationError

from literature.choices import IdentifierType
from tests.factories import ItemIdentifierFactory


def _clean_identifier(id_type, value):
    """Create an ItemIdentifier and call full_clean(); return the instance."""
    ii = ItemIdentifierFactory(type=id_type, value=value)
    ii.full_clean()  # triggers ItemIdentifier.clean()
    return ii


@pytest.mark.django_db
class TestIdentifierValidation:
    """Value-format validation dispatched per identifier type (FR-020)."""

    @pytest.mark.parametrize(
        "doi",
        [
            "10.1029/2019JB018475",
            "10.1000/xyz123",
            "10.1234/test-doi_with.chars",
            "10.12345/long-prefix-doi",
        ],
    )
    def test_doi_valid(self, doi):
        """Valid DOIs (starting with 10.<4+digits>/) pass validation."""
        _clean_identifier(IdentifierType.DOI, doi)

    @pytest.mark.parametrize(
        "doi",
        [
            "not-a-doi",
            "10./missing-suffix",
            "10.123/",  # no non-whitespace after slash
            "9.1234/abc",  # wrong prefix
            "doi:10.1234/ok",  # with scheme prefix
            "",
            "10.12 34/abc",  # space in prefix
        ],
    )
    def test_doi_invalid(self, doi):
        """Malformed DOIs raise ValidationError."""
        with pytest.raises(ValidationError):
            _clean_identifier(IdentifierType.DOI, doi)

    @pytest.mark.parametrize(
        "isbn",
        [
            "978-0-306-40615-7",  # ISBN-13 with hyphens
            "9780306406157",  # ISBN-13 no hyphens
            "0-306-40615-2",  # ISBN-10 with hyphens
            "0306406152",  # ISBN-10 no hyphens
            "0-19-853453-1",  # Oxford classic ISBN-10
        ],
    )
    def test_isbn_valid(self, isbn):
        """Valid ISBN-10 and ISBN-13 values pass validation."""
        _clean_identifier(IdentifierType.ISBN, isbn)

    @pytest.mark.parametrize(
        "isbn",
        [
            "978-0-306-40615-0",  # wrong ISBN-13 check digit
            "0-306-40615-9",  # wrong ISBN-10 check digit
            "1234567",  # too short
            "not-an-isbn",
            "978-0-306-40615",  # incomplete
        ],
    )
    def test_isbn_invalid(self, isbn):
        """Invalid ISBN values raise ValidationError."""
        with pytest.raises(ValidationError):
            _clean_identifier(IdentifierType.ISBN, isbn)

    @pytest.mark.parametrize(
        "issn",
        [
            "1742-2094",
            "0028-0836",  # Nature
            "1476-4687",  # Nature (online)
            "0000-000X",  # X check digit
        ],
    )
    def test_issn_valid(self, issn):
        """Valid ISSN format (NNNN-NNNX) passes validation."""
        _clean_identifier(IdentifierType.ISSN, issn)

    @pytest.mark.parametrize(
        "issn",
        [
            "1742-209",  # too short
            "17422094",  # no hyphen
            "ABCD-1234",  # non-digit prefix
            "1234-12345",  # too long suffix
            "",
        ],
    )
    def test_issn_invalid(self, issn):
        """Malformed ISSN values raise ValidationError."""
        with pytest.raises(ValidationError):
            _clean_identifier(IdentifierType.ISSN, issn)

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.example.com/path?q=1",
            "http://example.com",
            "ftp://ftp.example.org/file.txt",
        ],
    )
    def test_url_valid(self, url):
        """Valid http/https/ftp URLs pass validation."""
        _clean_identifier(IdentifierType.URL, url)

    @pytest.mark.parametrize(
        "url",
        [
            "/relative/path",
            "example.com",  # no scheme
            "javascript:alert(1)",  # non-allowed scheme
            "",
        ],
    )
    def test_url_invalid(self, url):
        """Relative or scheme-less URLs raise ValidationError."""
        with pytest.raises(ValidationError):
            _clean_identifier(IdentifierType.URL, url)

    @pytest.mark.parametrize("pmid", ["12345678", "1", "9999999999"])
    def test_pmid_valid(self, pmid):
        """Numeric strings are valid PMIDs."""
        _clean_identifier(IdentifierType.PMID, pmid)

    @pytest.mark.parametrize("pmid", ["abc", "12 34", "PMID:1234", ""])
    def test_pmid_invalid(self, pmid):
        """Non-numeric PMID values raise ValidationError."""
        with pytest.raises(ValidationError):
            _clean_identifier(IdentifierType.PMID, pmid)

    @pytest.mark.parametrize("pmcid", ["4567890", "1", "12345678901"])
    def test_pmcid_valid(self, pmcid):
        """Numeric strings are valid PMCIDs."""
        _clean_identifier(IdentifierType.PMCID, pmcid)

    @pytest.mark.parametrize("pmcid", ["PMC1234", "abc", ""])
    def test_pmcid_invalid(self, pmcid):
        """Non-numeric PMCID values raise ValidationError."""
        with pytest.raises(ValidationError):
            _clean_identifier(IdentifierType.PMCID, pmcid)

    @pytest.mark.parametrize(
        "id_type, value",
        [
            ("arxiv", "2104.00001"),
            ("handle", "20.500.12345/123"),
            ("custom-type", "any-value-whatsoever"),
        ],
    )
    def test_unknown_type_accepts_any_value(self, id_type, value):
        """Unknown identifier types are not validated — any value is accepted."""
        _clean_identifier(id_type, value)

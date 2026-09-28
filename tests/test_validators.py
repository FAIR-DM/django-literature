"""Tests for ``literature/validators.py``."""

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
        with pytest.raises(ValidationError):
            _clean_identifier(IdentifierType.ISBN, isbn)

    @pytest.mark.parametrize(
        "issn",
        [
            "1742-2094",
            "0028-0836",  # Nature
            "1476-4687",  # Nature (online)
            "0956-540X",  # X check digit
        ],
    )
    def test_issn_valid(self, issn):
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
        with pytest.raises(ValidationError):
            _clean_identifier(IdentifierType.URL, url)

    @pytest.mark.parametrize("pmid", ["12345678", "1", "9999999999"])
    def test_pmid_valid(self, pmid):
        _clean_identifier(IdentifierType.PMID, pmid)

    @pytest.mark.parametrize("pmid", ["abc", "12 34", "PMID:1234", ""])
    def test_pmid_invalid(self, pmid):
        with pytest.raises(ValidationError):
            _clean_identifier(IdentifierType.PMID, pmid)

    @pytest.mark.parametrize(
        "pmcid", ["PMC2728067", "PMC1234", "4567890", "1", "12345678901"]
    )
    def test_pmcid_valid(self, pmcid):
        _clean_identifier(IdentifierType.PMCID, pmcid)

    @pytest.mark.parametrize("pmcid", ["PMC", "PMC12a", "pmc1234", "abc", ""])
    def test_pmcid_invalid(self, pmcid):
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
        _clean_identifier(id_type, value)


@pytest.mark.django_db
class TestISBNChecksumDistinction:
    @pytest.mark.parametrize(
        "isbn",
        [
            "978-0-306-40615-0",  # wrong ISBN-13 check digit
            "0-306-40615-9",  # wrong ISBN-10 check digit
        ],
    )
    def test_a_wrong_check_digit_raises_the_checksum_code(self, isbn):
        with pytest.raises(ValidationError) as excinfo:
            _clean_identifier(IdentifierType.ISBN, isbn)
        assert excinfo.value.code == "invalid_isbn_checksum"

    @pytest.mark.parametrize(
        "isbn",
        [
            "1234567",  # too short
            "not-an-isbn",
            "978-0-306-40615",  # incomplete
        ],
    )
    def test_a_wrong_shape_raises_the_shape_code(self, isbn):
        with pytest.raises(ValidationError) as excinfo:
            _clean_identifier(IdentifierType.ISBN, isbn)
        assert excinfo.value.code == "invalid_isbn"

    def test_the_two_codes_are_distinct(self):
        with pytest.raises(ValidationError) as checksum_error:
            _clean_identifier(IdentifierType.ISBN, "978-0-306-40615-0")
        with pytest.raises(ValidationError) as shape_error:
            _clean_identifier(IdentifierType.ISBN, "not-an-isbn")
        assert checksum_error.value.code != shape_error.value.code
        assert checksum_error.value.messages != shape_error.value.messages


@pytest.mark.django_db
class TestISSNChecksumDistinction:
    @pytest.mark.parametrize(
        "issn",
        [
            "1742-2095",  # right shape, wrong check digit
            "0956-5401",  # right shape, wrong check digit (correct one ends in X)
        ],
    )
    def test_a_wrong_check_digit_raises_the_checksum_code(self, issn):
        with pytest.raises(ValidationError) as excinfo:
            _clean_identifier(IdentifierType.ISSN, issn)
        assert excinfo.value.code == "invalid_issn_checksum"

    @pytest.mark.parametrize(
        "issn",
        [
            "1742-209",  # too short
            "17422094",  # no hyphen
            "not-an-issn",
        ],
    )
    def test_a_wrong_shape_raises_the_shape_code(self, issn):
        with pytest.raises(ValidationError) as excinfo:
            _clean_identifier(IdentifierType.ISSN, issn)
        assert excinfo.value.code == "invalid_issn"

    def test_the_two_codes_are_distinct(self):
        with pytest.raises(ValidationError) as checksum_error:
            _clean_identifier(IdentifierType.ISSN, "1742-2095")
        with pytest.raises(ValidationError) as shape_error:
            _clean_identifier(IdentifierType.ISSN, "not-an-issn")
        assert checksum_error.value.code != shape_error.value.code
        assert checksum_error.value.messages != shape_error.value.messages

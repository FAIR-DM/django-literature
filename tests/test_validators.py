"""Tests for literature.validators — FR-020 identifier value validation.

Covers valid/invalid values for each known identifier type and verifies that
unknown identifier types accept any value string without error.
"""

import pytest
from django.core.exceptions import ValidationError

from literature.choices import IdentifierType

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _clean_identifier(make_item, make_item_identifier, id_type, value):
    """Create an ItemIdentifier and call full_clean(); return the instance."""
    item = make_item()
    ii = make_item_identifier(item=item, type=id_type, value=value)
    ii.full_clean()  # triggers ItemIdentifier.clean()
    return ii


# ---------------------------------------------------------------------------
# DOI
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "doi",
    [
        "10.1029/2019JB018475",
        "10.1000/xyz123",
        "10.1234/test-doi_with.chars",
        "10.12345/long-prefix-doi",
    ],
)
def test_validate_doi_valid(make_item, make_item_identifier, doi):
    """Valid DOIs (starting with 10.<4+digits>/) pass validation."""
    _clean_identifier(make_item, make_item_identifier, IdentifierType.DOI, doi)


@pytest.mark.django_db
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
def test_validate_doi_invalid(make_item, make_item_identifier, doi):
    """Malformed DOIs raise ValidationError."""
    with pytest.raises(ValidationError):
        _clean_identifier(make_item, make_item_identifier, IdentifierType.DOI, doi)


# ---------------------------------------------------------------------------
# ISBN
# ---------------------------------------------------------------------------


@pytest.mark.django_db
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
def test_validate_isbn_valid(make_item, make_item_identifier, isbn):
    """Valid ISBN-10 and ISBN-13 values pass validation."""
    _clean_identifier(make_item, make_item_identifier, IdentifierType.ISBN, isbn)


@pytest.mark.django_db
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
def test_validate_isbn_invalid(make_item, make_item_identifier, isbn):
    """Invalid ISBN values raise ValidationError."""
    with pytest.raises(ValidationError):
        _clean_identifier(make_item, make_item_identifier, IdentifierType.ISBN, isbn)


# ---------------------------------------------------------------------------
# ISSN
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "issn",
    [
        "1742-2094",
        "0028-0836",  # Nature
        "1476-4687",  # Nature (online)
        "0000-000X",  # X check digit
    ],
)
def test_validate_issn_valid(make_item, make_item_identifier, issn):
    """Valid ISSN format (NNNN-NNNX) passes validation."""
    _clean_identifier(make_item, make_item_identifier, IdentifierType.ISSN, issn)


@pytest.mark.django_db
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
def test_validate_issn_invalid(make_item, make_item_identifier, issn):
    """Malformed ISSN values raise ValidationError."""
    with pytest.raises(ValidationError):
        _clean_identifier(make_item, make_item_identifier, IdentifierType.ISSN, issn)


# ---------------------------------------------------------------------------
# URL
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    [
        "https://www.example.com/path?q=1",
        "http://example.com",
        "ftp://ftp.example.org/file.txt",
    ],
)
def test_validate_url_valid(make_item, make_item_identifier, url):
    """Valid http/https/ftp URLs pass validation."""
    _clean_identifier(make_item, make_item_identifier, IdentifierType.URL, url)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    [
        "/relative/path",
        "example.com",  # no scheme
        "javascript:alert(1)",  # non-allowed scheme
        "",
    ],
)
def test_validate_url_invalid(make_item, make_item_identifier, url):
    """Relative or scheme-less URLs raise ValidationError."""
    with pytest.raises(ValidationError):
        _clean_identifier(make_item, make_item_identifier, IdentifierType.URL, url)


# ---------------------------------------------------------------------------
# PMID
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("pmid", ["12345678", "1", "9999999999"])
def test_validate_pmid_valid(make_item, make_item_identifier, pmid):
    """Numeric strings are valid PMIDs."""
    _clean_identifier(make_item, make_item_identifier, IdentifierType.PMID, pmid)


@pytest.mark.django_db
@pytest.mark.parametrize("pmid", ["abc", "12 34", "PMID:1234", ""])
def test_validate_pmid_invalid(make_item, make_item_identifier, pmid):
    """Non-numeric PMID values raise ValidationError."""
    with pytest.raises(ValidationError):
        _clean_identifier(make_item, make_item_identifier, IdentifierType.PMID, pmid)


# ---------------------------------------------------------------------------
# PMCID
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("pmcid", ["4567890", "1", "12345678901"])
def test_validate_pmcid_valid(make_item, make_item_identifier, pmcid):
    """Numeric strings are valid PMCIDs."""
    _clean_identifier(make_item, make_item_identifier, IdentifierType.PMCID, pmcid)


@pytest.mark.django_db
@pytest.mark.parametrize("pmcid", ["PMC1234", "abc", ""])
def test_validate_pmcid_invalid(make_item, make_item_identifier, pmcid):
    """Non-numeric PMCID values raise ValidationError."""
    with pytest.raises(ValidationError):
        _clean_identifier(make_item, make_item_identifier, IdentifierType.PMCID, pmcid)


# ---------------------------------------------------------------------------
# Unknown identifier type — always accepted
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "id_type, value",
    [
        ("arxiv", "2104.00001"),
        ("handle", "20.500.12345/123"),
        ("custom-type", "any-value-whatsoever"),
    ],
)
def test_unknown_identifier_type_accepts_any_value(make_item, make_item_identifier, id_type, value):
    """Unknown identifier types are not validated — any value is accepted."""
    _clean_identifier(make_item, make_item_identifier, id_type, value)

"""Tests for literature.utils: CSL JSON date-parts parsing and DOI links.

parse_date_parts() is exercised across every precision the CSL JSON date-parts
spec allows, plus the empty-input and unparseable-input paths that fall back to
None. doi_url() is exercised for bare DOIs and for values that are not DOIs.
"""

import pytest

from literature.utils import doi_url, parse_date_parts


class TestParseDateParts:
    def test_year_only(self):
        result = parse_date_parts([2019])
        assert str(result) == "2019"

    def test_year_month(self):
        result = parse_date_parts([2019, 8])
        assert str(result).startswith("2019-08")

    def test_full_date(self):
        result = parse_date_parts([2019, 8, 16])
        assert str(result).startswith("2019-08-16")

    def test_string_digits_are_coerced(self):
        result = parse_date_parts(["2019", "8"])
        assert str(result).startswith("2019-08")

    def test_extra_parts_are_ignored(self):
        result = parse_date_parts([2019, 8, 16, 12])
        assert str(result).startswith("2019-08-16")

    def test_empty_list_returns_none(self):
        assert parse_date_parts([]) is None

    def test_none_input_returns_none(self):
        assert parse_date_parts(None) is None

    def test_non_numeric_returns_none(self):
        assert parse_date_parts(["not-a-year"]) is None


class TestDoiUrl:
    def test_a_bare_doi_resolves_through_doi_org(self):
        assert doi_url("10.1002/j.1538-7305.1948.tb01338.x") == (
            "https://doi.org/10.1002/j.1538-7305.1948.tb01338.x"
        )

    @pytest.mark.parametrize(
        "value",
        ["978-3-16-148410-0", "10.1234", "javascript:alert(1)", "", None],
    )
    def test_a_value_not_shaped_like_a_doi_gets_no_link(self, value):
        assert doi_url(value) is None

    def test_markup_in_a_stored_doi_cannot_leave_the_path(self):
        url = doi_url('10.1234/x"><script>')
        assert url.startswith("https://doi.org/10.1234/x")
        assert '"' not in url
        assert "<" not in url

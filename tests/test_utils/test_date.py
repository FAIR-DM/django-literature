"""Tests for literature.utils.date — CSL JSON date-parts parsing.

Exercises parse_date_parts() directly across every precision the CSL JSON
date-parts spec allows, plus the empty-input and unparseable-input paths that
fall back to None.
"""

from literature.utils.date import parse_date_parts


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

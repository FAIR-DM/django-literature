"""Tests for ``literature/utils/doi.py``."""

import pytest

from literature.utils.doi import doi_url


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

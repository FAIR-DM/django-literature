"""Tests for ``literature/ui/links.py`` — RS-001."""

import pytest

from literature.ui.links import web_url


class TestWebUrl:
    """Only http and https reach an ``href``; everything else is plain text."""

    @pytest.mark.parametrize(
        "value",
        [
            "https://example.org/paper",
            "http://example.org/paper",
            "HTTPS://example.org/paper",
            "https://example.org/paper?q=1&r=2#frag",
        ],
    )
    def test_web_urls_are_linkable(self, value):
        assert web_url(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "javascript:alert(document.cookie)",
            "javascript://%0aalert(document.cookie)",
            "JaVaScRiPt://%0aalert(1)",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            "vbscript:msgbox(1)",
            "file:///etc/passwd",
            "ftp://example.org/paper",
        ],
    )
    def test_other_schemes_are_not_linkable(self, value):
        assert web_url(value) is None

    @pytest.mark.parametrize(
        "value",
        [
            "10.1234/abcd",  # a bare DOI
            "978-3-16-148410-0",  # an ISBN
            "ark:/12345/x",
            "",
            None,
        ],
    )
    def test_values_that_are_not_urls_are_not_linkable(self, value):
        assert web_url(value) is None

    def test_an_unparseable_value_is_not_linkable(self):
        # An unclosed IPv6 bracket makes urlsplit raise rather than return.
        assert web_url("http://[::1") is None

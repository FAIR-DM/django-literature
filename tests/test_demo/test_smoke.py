"""Tests for ``demo/smoke.py`` — the guard's assertions (FR-018 through FR-022).

The script speaks real HTTP to a running demo and is not itself run under pytest
(``demo/smoke.py``'s docstring). What is testable without a server is everything that
decides whether the walk means anything: the two link patterns it follows, the prefix
those patterns assume, the login-redirect check that keeps the walk unauthenticated
(FR-005), and the bound on the body excerpt a failure reports (FR-020).

Each pattern is asserted against the HTML the front end really renders. A pattern
checked only against markup written here would keep passing after the templates moved
on, which is the drift this feature exists to catch.

``demo`` is absent from ``tests.settings.INSTALLED_APPS`` (plan.md D-10), but
``demo.smoke`` imports nothing from Django, so importing it needs no app registry.
"""

import re
from pathlib import Path

import pytest
from django.urls import reverse

from demo.smoke import (
    _BODY_EXCERPT_LIMIT,
    _CONTRIBUTOR_LINK_RE,
    _ITEM_LINK_RE,
    _SECOND_PAGE_LINK,
    DemoWalk,
    SmokeCheckFailed,
)
from tests.factories import ItemFactory, ItemNameFactory

_DEMO_URLS = Path(__file__).resolve().parent.parent.parent / "demo" / "urls.py"


class TestItemLinkPattern:
    """The pattern the walk follows from the catalogue list to a reference page."""

    def test_matches_the_anchor_the_catalogue_list_renders(self, client, db):
        item = ItemFactory(title="A Walked Reference")

        response = client.get(reverse("literature:item-list"))
        matches = _ITEM_LINK_RE.findall(response.content.decode())

        assert (reverse("literature:item-detail", kwargs={"pk": item.pk}), item.title) in matches

    def test_does_not_match_a_contributor_link(self, db):
        # Both live under /catalogue/; only the reference page's path is a bare
        # primary key (ADR-0015), and a pattern that matched both would send the
        # walk to a contributor page while reporting a reference page.
        item_name = ItemNameFactory(item=ItemFactory())
        contributor_path = reverse("literature:contributor-detail", kwargs={"pk": item_name.name.pk})

        assert _ITEM_LINK_RE.search(f'<a href="{contributor_path}">Someone</a>') is None

    def test_second_page_link_is_the_one_the_paginated_list_renders(self, client, db):
        ItemFactory.create_batch(30)

        response = client.get(reverse("literature:item-list"))

        assert _SECOND_PAGE_LINK in response.content.decode()


class TestContributorLinkPattern:
    """The pattern the walk follows from a reference page to a contributor page."""

    def test_matches_the_anchor_the_reference_page_renders(self, client, db):
        item = ItemFactory()
        item_name = ItemNameFactory(item=item)

        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        match = _CONTRIBUTOR_LINK_RE.search(response.content.decode())

        assert match is not None
        assert match.group("path") == reverse("literature:contributor-detail", kwargs={"pk": item_name.name.pk})
        assert match.group("text") == str(item_name.name)


class TestPatternPrefix:
    """Both patterns hard-code ``/catalogue/``, which only the demo's own URLconf sets."""

    def test_the_demo_mounts_the_front_end_where_the_patterns_look_for_it(self):
        # The suite reaches these pages through reverse() under tests/urls.py, so a
        # test suite that stayed green would say nothing about where the demo serves
        # them. Read the demo's URLconf as text: importing it evaluates
        # admin.site.urls against the suite's app registry, which is the coupling
        # FR-021 forbids.
        source = _DEMO_URLS.read_text(encoding="utf-8")

        assert re.search(r'path\(\s*"catalogue/",\s*include\(\s*"literature\.ui\.urls"\s*\)', source)


class TestFailureReport:
    """What a failed check tells a CI log (FR-020)."""

    def test_bounds_the_body_it_reports(self):
        # The demo runs with DEBUG = True, so an unbounded body would put Django's
        # technical-500 page — settings and the request environment — into a public log.
        walk = DemoWalk("http://127.0.0.1:8000")

        with pytest.raises(SmokeCheckFailed) as excinfo:
            walk._fail("http://127.0.0.1:8000/catalogue/", 500, "unsuccessful response", "SECRET" * 1000)

        body_excerpt = str(excinfo.value).split("\n", 1)[1]
        assert len(body_excerpt) == _BODY_EXCERPT_LIMIT

    def test_names_the_url_the_status_and_the_reason(self):
        walk = DemoWalk("http://127.0.0.1:8000")

        with pytest.raises(SmokeCheckFailed) as excinfo:
            walk._fail("http://127.0.0.1:8000/catalogue/2/", 404, "unsuccessful response")

        message = str(excinfo.value)
        assert "http://127.0.0.1:8000/catalogue/2/" in message
        assert "404" in message
        assert "unsuccessful response" in message


class _FakeResponse:
    """The part of ``urlopen``'s return value ``_get`` uses."""

    def __init__(self, body, final_url):
        self._body = body
        self._final_url = final_url

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self):
        return self._body.encode()

    def geturl(self):
        return self._final_url


class TestUnauthenticatedWalk:
    """FR-005: every page on the walk is served without a login."""

    def test_a_redirect_to_a_login_page_fails_the_check(self, monkeypatch):
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda url, timeout=None: _FakeResponse("<h1>Log in</h1>", "http://127.0.0.1:8000/accounts/login/?next=/"),
        )
        walk = DemoWalk("http://127.0.0.1:8000")

        with pytest.raises(SmokeCheckFailed, match="login page"):
            walk._get("http://127.0.0.1:8000/catalogue/")

    def test_a_page_served_without_a_login_returns_its_body(self, monkeypatch):
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda url, timeout=None: _FakeResponse("<h1>Catalogue</h1>", "http://127.0.0.1:8000/catalogue/"),
        )
        walk = DemoWalk("http://127.0.0.1:8000")

        assert walk._get("http://127.0.0.1:8000/catalogue/") == "<h1>Catalogue</h1>"

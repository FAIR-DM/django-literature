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
import urllib.request
from pathlib import Path

import pytest
from django.urls import reverse

from demo.smoke import (
    _BODY_EXCERPT_LIMIT,
    _CONTRIBUTOR_LINK_RE,
    _CREATE_LINK_RE,
    _DELETE_LINK_RE,
    _EDIT_LINK_RE,
    _ITEM_LINK_RE,
    _SECOND_PAGE_LINK,
    DemoWalk,
    SmokeCheckFailed,
    _form_fields,
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
    """FR-005: every page on the walk is served without a login.

    ``_get`` reads through ``self.opener`` (T021, D-9) rather than the bare
    ``urllib.request.urlopen`` it used before the write pass — the whole walk
    needs one cookie jar so the CSRF cookie a form page sets survives into its
    POST. ``OpenerDirector.open`` is what every call goes through regardless
    of which page, so patching it at the class level is what the walk's own
    mechanism now is (plan.md D-9).
    """

    def test_a_redirect_to_a_login_page_fails_the_check(self, monkeypatch):
        monkeypatch.setattr(
            "urllib.request.OpenerDirector.open",
            lambda self, url, timeout=None: _FakeResponse("<h1>Log in</h1>", "http://127.0.0.1:8000/accounts/login/?next=/"),
        )
        walk = DemoWalk("http://127.0.0.1:8000")

        with pytest.raises(SmokeCheckFailed, match="login page"):
            walk._get("http://127.0.0.1:8000/catalogue/")

    def test_a_page_served_without_a_login_returns_its_body(self, monkeypatch):
        monkeypatch.setattr(
            "urllib.request.OpenerDirector.open",
            lambda self, url, timeout=None: _FakeResponse("<h1>Catalogue</h1>", "http://127.0.0.1:8000/catalogue/"),
        )
        walk = DemoWalk("http://127.0.0.1:8000")

        assert walk._get("http://127.0.0.1:8000/catalogue/") == "<h1>Catalogue</h1>"


class TestSharedOpener:
    """The write pass needs one cookie jar across the whole walk (T021, D-9).

    A CSRF cookie set while GETting a form page has to still be attached when
    the walk POSTs back to it — two separate ``urlopen`` calls would not share
    state, so the walk builds one ``OpenerDirector`` in ``__init__`` and every
    request goes through it.
    """

    def test_the_walk_builds_one_opener_carrying_a_cookie_processor(self):
        walk = DemoWalk("http://127.0.0.1:8000")

        assert isinstance(walk.opener, urllib.request.OpenerDirector)
        cookie_handlers = [h for h in walk.opener.handlers if isinstance(h, urllib.request.HTTPCookieProcessor)]
        assert len(cookie_handlers) == 1


class TestCreateLinkPattern:
    """The pattern the write pass follows from the catalogue list to the create form (T021)."""

    def test_matches_the_anchor_the_catalogue_list_renders(self, client, db):
        response = client.get(reverse("literature:item-list"))
        match = _CREATE_LINK_RE.search(response.content.decode())

        assert match is not None
        assert match.group("path") == reverse("literature:item-create")


class TestEditLinkPattern:
    """The pattern the write pass follows from a reference page to its edit form (T021)."""

    def test_matches_the_anchor_the_reference_page_renders(self, client, db):
        item = ItemFactory()

        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        match = _EDIT_LINK_RE.search(response.content.decode())

        assert match is not None
        assert match.group("path") == reverse("literature:item-update", kwargs={"pk": item.pk})


class TestDeleteLinkPattern:
    """The pattern the write pass follows from a reference page to its delete confirmation (T021)."""

    def test_matches_the_anchor_the_reference_page_renders(self, client, db):
        item = ItemFactory()

        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        match = _DELETE_LINK_RE.search(response.content.decode())

        assert match is not None
        assert match.group("path") == reverse("literature:item-delete", kwargs={"pk": item.pk})


class TestFormFields:
    """What the write pass posts back is exactly what the rendered form emits (T021, D-9, D-3).

    Posting a bare field dict would blank every field the walk did not name —
    the same ``construct_instance`` reason plan.md D-3 states for the front
    end itself — so the write pass has to scrape the form rather than
    construct a payload by hand. These tests are the over-HTML-parsing proof
    that the scrape is right, mirroring how ``TestItemLinkPattern`` above
    checks its regex against the markup the front end really renders.
    """

    def test_captures_the_csrf_token_and_every_named_field_on_the_create_form(self, client, db):
        response = client.get(reverse("literature:item-create"))
        fields = _form_fields(response.content.decode())

        assert fields.get("csrfmiddlewaretoken")
        assert "citation_key" in fields
        assert "title" in fields
        assert "type" in fields

    def test_a_populated_items_edit_form_carries_its_stored_values(self, client, db):
        item = ItemFactory(title="Round Trip Title", citation_key="rt-001")

        response = client.get(reverse("literature:item-update", kwargs={"pk": item.pk}))
        fields = _form_fields(response.content.decode())

        assert fields["title"] == "Round Trip Title"
        assert fields["citation_key"] == "rt-001"
        assert fields["type"] == item.type

    def test_a_textarea_fields_content_is_captured_as_its_value(self, client, db):
        item = ItemFactory(abstract="An abstract spanning\nmultiple lines.")

        response = client.get(reverse("literature:item-update", kwargs={"pk": item.pk}))
        fields = _form_fields(response.content.decode())

        assert fields["abstract"] == "An abstract spanning\nmultiple lines."

    def test_the_show_every_field_toggle_carries_no_name_and_is_not_captured(self, client, db):
        # item_form.html's <c-form.field type="checkbox" ... x-model="form.showAll" />
        # names no `name` attribute — a browser posts nothing for it, and a
        # scraper that invented one would post a field the view never declared.
        response = client.get(reverse("literature:item-create"))
        fields = _form_fields(response.content.decode())

        assert "showAll" not in fields
        assert all(name for name in fields)

    def test_the_delete_confirmation_carries_only_the_csrf_token(self, client, db):
        # require_confirmation is off (plan.md D-7): the confirmation page's
        # form has nothing to fill in, only the token to post back.
        item = ItemFactory()

        response = client.get(reverse("literature:item-delete", kwargs={"pk": item.pk}))
        fields = _form_fields(response.content.decode())

        assert list(fields) == ["csrfmiddlewaretoken"]

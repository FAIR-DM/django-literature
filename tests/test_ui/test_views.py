"""Tests for ``literature/ui/views.py``.

Article XIV: one source module, one test module — the per-view split is
expressed with classes, one per story (``TestItemListView`` for US-1,
``TestItemDetailView`` for US-2, ``TestContributorDetailView`` for US-4).
"""

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import pytest
from django.db import connection
from django.template.loader import get_template
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

import literature
from literature.choices import DateType, ItemType, NameRole
from literature.converters import from_csl_json, to_csl_json
from literature.models import Item, ItemDate, ItemIdentifier, ItemName, Name
from literature.ui.fieldgroups import FieldGroups
from tests.factories import ItemDateFactory, ItemFactory, ItemIdentifierFactory, ItemNameFactory, NameFactory


def anchor_tag(content, href):
    """The opening ``<a>`` tag addressing ``href``, so a test can assert on the
    classes it carries rather than only on the presence of the URL."""
    match = re.search(rf"<a\b[^>]*href=\"{re.escape(href)}\"[^>]*>", content)
    assert match, f"no anchor addressing {href}"
    return match.group(0)


def table_header_row(content):
    """The table's own ``<thead>...</thead>`` markup, so a column-order
    assertion reads the header row rather than the whole rendered page
    (decisions.md D16) — the filter modal renders ahead of the table and
    emits some of the same words as literal field labels."""
    match = re.search(r"<thead.*?</thead>", content, re.DOTALL)
    assert match, "no table header row"
    return match.group(0)


def rendered_page_link(content, page_number):
    """The ``href`` the rendered pagination component's own numbered link to
    ``page_number`` carries — found by reading the markup, not by
    constructing ``?page=N`` ourselves. That distinction is what T019's
    page-2 assertion turns on (plan.md D-14): the address the reader's
    click actually carries is the evidence, not one the test invents.

    Unescaped (decisions.md D13): ``{% querystring %}`` HTML-escapes the
    ``&`` joining two or more parameters, so a link carrying both ``sort``
    and ``page`` renders as ``...&amp;page=2``. Read verbatim, the test
    client parses that as a parameter literally named ``amp;page`` and no
    ``page`` value ever reaches the view."""
    match = re.search(rf'<a\b[^>]*href="([^"]*)"[^>]*>\s*{page_number}\s*</a>', content)
    assert match, f"no rendered link to page {page_number}"
    return html.unescape(match.group(1))


def rendered_sort_link(content, column_label):
    """The ``href`` a column heading's own sort link carries (T019, FR-019) —
    the address a reader's click on that heading actually carries, unescaped
    the same way ``rendered_page_link()`` is and for the same reason."""
    match = re.search(rf'<a\b[^>]*href="([^"]*)"[^>]*>\s*{re.escape(column_label)}\s*<', content)
    assert match, f"no rendered sort link for column {column_label!r}"
    return html.unescape(match.group(1))


def rendered_form_post_data(client, url, **overrides):
    """Build a POST body from a rendered page's own form at ``url``.

    Every field starts at what the form (bound or unbound) actually
    initialises it to, and whatever the Save button's own ``name``/``value``
    pair is is carried exactly as the page emits it — never assembled from a
    bare hand-typed dict. A bare dict would miss both, and would pass a
    round-trip or redirect-target assertion even against a view that dropped
    a field, or reverted ``{% block actions %}`` to the stock button that
    posts ``default_next=list`` (plan.md D-3), the rendered page actually
    posts.
    """
    response = client.get(url)
    form = response.context["form"]
    data = {name: (form[name].value() or "") for name in form.fields}
    content = response.content.decode()
    submit_button = re.search(r'<button[^>]*type="submit"[^>]*name="([^"]+)"[^>]*value="([^"]+)"', content)
    if submit_button:
        data[submit_button.group(1)] = submit_button.group(2)
    data.update(overrides)
    return data


def rendered_filter_form_data(response, **overrides):
    """Build a GET query dict from a rendered page's own filter form (T020).

    ``response.context["filter"].form`` is the same GET-bound form the
    filter modal renders — every field starts at what that form actually
    carries, a hidden field included, so submitting the result reproduces
    exactly what the modal's own ``c-form`` submits when a reader changes
    one field and clicks "Apply filters", not a hand-typed dict that could
    silently omit one."""
    form = response.context["filter"].form
    data = {name: (form[name].value() or "") for name in form.fields}
    data.update(overrides)
    return data


def update_page_post_data(client, item, **overrides):
    """Build a POST body from the rendered edit page's own bound form (T009)."""
    return rendered_form_post_data(client, reverse("literature:item-update", kwargs={"pk": item.pk}), **overrides)


def create_page_post_data(client, **overrides):
    """Build a POST body from the rendered create page's own form (T011)."""
    return rendered_form_post_data(client, reverse("literature:item-create"), **overrides)


#: Both catalogue presentations, so a "both presentations owe this" test
#: (plan.md D-11) is one parametrized method rather than two near-identical
#: ones. ``literature:item-list`` is the table since T010; the card is
#: reachable at the test urlconf's own second route (research R10).
CATALOGUE_ROUTES = ["literature:item-list", "item-list-cards"]


class TestItemListView:
    """List behaviour every catalogue presentation owes, plus the card's own
    content (FR-011, FR-012, FR-021, plan.md D-11).

    The assertions parametrized over ``CATALOGUE_ROUTES`` come from shared
    django-mvp mechanisms — pagination, the position line, the empty state —
    rather than from either view's own template, so they are genuinely two
    promises now rather than one. The rest are about the card's own
    rendering and stay pinned to its own route; the table's equivalent
    per-column behaviour is ``tests/test_ui/test_tables.py``'s own subject.
    """

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_lists_items_most_recently_added_first(self, client, db, route_name):
        older = ItemFactory(title="Older Reference")
        newer = ItemFactory(title="Newer Reference")
        response = client.get(reverse(route_name))
        content = response.content.decode()
        assert content.index("Newer Reference") < content.index("Older Reference")

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_page_holds_no_more_than_paginate_by_items_whatever_the_catalogue_size(self, client, db, route_name):
        ItemFactory.create_batch(30)
        response = client.get(reverse(route_name))
        if route_name == "literature:item-list":
            # The table route's own page (decisions.md D14): at 0.19.1
            # MVPTableViewMixin.paginate_queryset() leaves the queryset
            # whole and republishes the page from the table, so
            # object_list there is the whole catalogue, not one page of it.
            assert len(response.context["table"].page.object_list) == 24
        else:
            assert len(response.context["object_list"]) == 24

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_pagination_states_position_and_offers_navigation(self, client, db, route_name):
        ItemFactory.create_batch(30)
        response = client.get(reverse(route_name))
        content = response.content.decode()
        assert "1-24 of 30" in content
        assert 'href="?page=2"' in content

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_page_number_past_the_end_is_a_404(self, client, db, route_name):
        ItemFactory()
        response = client.get(reverse(route_name), {"page": 999})
        assert response.status_code == 404

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_empty_catalogue_renders_the_stated_empty_result(self, client, db, route_name):
        # Assert this view's own wording, not merely the presence of an empty
        # state — django-mvp's default heading ("There's nothing here yet")
        # would satisfy a looser match and hide an unwired empty state.
        response = client.get(reverse(route_name))
        assert response.status_code == 200
        content = response.content.decode()
        assert "Nothing in the catalogue yet" in content
        assert "References imported or created will appear here." in content

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_each_row_links_to_that_items_page(self, client, db, route_name):
        item = ItemFactory(title="A Linked Reference")
        response = client.get(reverse(route_name))
        content = response.content.decode()
        assert reverse("literature:item-detail", kwargs={"pk": item.pk}) in content

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_the_add_link_renders_and_points_at_the_create_page(self, client, db, route_name):
        # directory = ["create"] alone renders nothing without
        # show_create_action set (plan.md D-6) — this is the entry point
        # US-1's acceptance scenario 1 starts from.
        content = client.get(reverse(route_name)).content.decode()
        assert f'href="{reverse("literature:item-create")}"' in content

    def test_item_with_no_title_shows_its_citation_key(self, client, db):
        # The card's own single-level fallback (title -> citation_key); the
        # table's five-rung chain is tables.py's own contract, tested in
        # tests/test_ui/test_tables.py::TestTitleColumn.
        ItemFactory(title="", citation_key="FallbackKey2026")
        response = client.get(reverse("item-list-cards"))
        content = response.content.decode()
        assert "FallbackKey2026" in content

    def test_row_carries_contributors_issued_date_and_citation_key(self, client, db):
        item = ItemFactory(title="With Everything", citation_key="Everything2026")
        item_name = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        response = client.get(reverse("item-list-cards"))
        content = response.content.decode()
        assert "Everything2026" in content
        assert "2020" in content
        assert str(item_name.name) in content

    def test_row_shows_a_ranged_issued_date_at_both_ends(self, client, db):
        # FR-013 is "at the precision stored", and a range's precision is both
        # ends — the row used to drop everything after ``begin`` while the
        # reference page rendered the same date correctly (RC-002).
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2019", end="2021")
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "2019" in content
        assert "2021" in content

    def test_row_falls_back_to_a_free_text_date(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=None, literal="in press")
        assert "in press" in client.get(reverse("item-list-cards")).content.decode()

    def test_query_count_does_not_grow_with_row_count(self, client, db):
        def add_items(n):
            for _ in range(n):
                item = ItemFactory()
                ItemNameFactory(item=item)
                ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2021")

        add_items(3)
        with CaptureQueriesContext(connection) as small_catalogue:
            response = client.get(reverse("item-list-cards"))
        assert response.status_code == 200

        add_items(15)
        with CaptureQueriesContext(connection) as large_catalogue:
            response = client.get(reverse("item-list-cards"))
        assert response.status_code == 200

        assert len(large_catalogue.captured_queries) == len(small_catalogue.captured_queries)


class TestCatalogueListReadability:
    """Issue #65 — what the card list and its rows say at a glance.

    Re-pointed to the card's own route rather than deleted or loosened
    (plan.md D-11): every assertion here is about the card, and the card is
    not going away — only the default route in front of it moved.
    """

    def test_the_page_is_titled_for_what_it_holds_not_for_the_model(self, client, db):
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "Publications" in content
        assert "Items" not in content

    def test_the_position_line_names_the_collection_the_same_way_the_heading_does(self, client, db):
        # django-mvp writes this line from the model's verbose_name_plural, so
        # retitling the page alone left it reading "Showing 1-24 of 28 items"
        # directly under a heading that said Publications.
        ItemFactory.create_batch(30)
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "of 30 publications" in content
        assert "of 30 items" not in content

    def test_the_model_keeps_its_own_name(self, db):
        # The heading is the view's to choose. Renaming the model to reach it
        # would rename it in the admin, in every error message and in the
        # migration state, for a word on one page.
        assert str(Item._meta.verbose_name_plural) == "items"

    def test_the_item_type_badge_carries_the_primary_colour(self, client, db):
        ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = client.get(reverse("item-list-cards")).content.decode()
        assert re.search(r'class="badge badge-primary[^"]*">\s*Journal Article\s*<', content)

    def test_contributor_names_link_to_their_page(self, client, db):
        # The reference page has carried this link since FR-022; the row showed
        # the same names as plain text, so a reader could not tell from the
        # catalogue that a contributor had a page at all.
        item_name = ItemNameFactory(role=NameRole.AUTHOR)
        content = client.get(reverse("item-list-cards")).content.decode()
        contributor_url = reverse("literature:contributor-detail", kwargs={"pk": item_name.name.pk})
        assert f'href="{contributor_url}"' in content

    def test_a_contributor_link_underlines_on_hover(self, client, db):
        item_name = ItemNameFactory(role=NameRole.AUTHOR)
        content = client.get(reverse("item-list-cards")).content.decode()
        contributor_url = reverse("literature:contributor-detail", kwargs={"pk": item_name.name.pk})
        assert "link-hover" in anchor_tag(content, contributor_url)

    def test_the_title_link_underlines_on_hover(self, client, db):
        item = ItemFactory(title="A Followable Title")
        content = client.get(reverse("item-list-cards")).content.decode()
        item_url = reverse("literature:item-detail", kwargs={"pk": item.pk})
        assert "link-hover" in anchor_tag(content, item_url)

    def test_a_role_heading_pluralises_with_the_names_under_it(self, client, db):
        item = ItemFactory()
        for _ in range(3):
            ItemNameFactory(item=item, role=NameRole.AUTHOR)
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "Authors:" in content
        assert "Author:" not in content

    def test_a_role_heading_stays_singular_for_one_name(self, client, db):
        ItemNameFactory(role=NameRole.AUTHOR)
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "Author:" in content

    def test_the_citation_key_is_labelled(self, client, db):
        # Given a title, so the row's fallback does not also print the key
        # (the fallback is the row's heading, and is not what this labels).
        ItemFactory(title="A Titled Reference", citation_key="Labelled2026")
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "Cite key" in content
        assert content.index("Cite key") < content.index("Labelled2026")

    def test_a_row_shows_a_snippet_of_the_abstract(self, client, db):
        ItemFactory(abstract="Sediment cores record the drainage history of the basin.")
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "Sediment cores record the drainage history of the basin." in content

    def test_a_long_abstract_is_cut_to_a_snippet(self, client, db):
        ItemFactory(abstract=" ".join(f"word{n}" for n in range(60)))
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "word0" in content
        assert "word59" not in content

    def test_a_row_carrying_no_abstract_leaves_no_empty_paragraph_behind(self, client, db):
        # The snippet is a paragraph; rendered unconditionally it would leave an
        # empty one on every row of a catalogue imported without abstracts,
        # which is most of them.
        item = ItemFactory(abstract="")
        content = client.get(reverse("item-list-cards")).content.decode()
        assert re.search(r"<p[^>]*>\s*</p>", content) is None
        assert item.citation_key in content


class TestTheCardListStaysAvailable:
    """US-4 — the card presentation did not go away (FR-022, FR-023, FR-027).

    The list behaviour a project switching to this route inherits —
    ordering, page size, the empty state, the create action — is already
    asserted for both presentations by ``TestItemListView``'s
    ``CATALOGUE_ROUTES`` parametrization. This class asserts the promise
    itself: the class is reachable, the route it is pointed at renders cards
    rather than the table it no longer defaults to, the contributor page
    still presents cards, and none of that needs a template copied out of
    the package.
    """

    def test_itemlistview_is_importable_from_the_views_module(self):
        from literature.ui.views import ItemListView

        assert ItemListView.list_item_template == "literature/ui/item_list_item.html"

    def test_routing_a_url_at_it_renders_cards_not_the_table(self, client, db):
        # "<table" is unique to django-tables2's own template
        # (django_tables2/bootstrap5-mvp.html) — nothing in the card's own
        # chain renders one, so its presence or absence tells the two
        # presentations apart directly.
        ItemFactory(title="A Card-Rendered Reference")
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "<table" not in content
        assert "A Card-Rendered Reference" in content

    def test_routing_a_url_at_it_keeps_pagination_the_empty_state_and_the_create_action(self, client, db):
        # Empty state first — populating the catalogue would hide it.
        empty_content = client.get(reverse("item-list-cards")).content.decode()
        assert "Nothing in the catalogue yet" in empty_content
        assert f'href="{reverse("literature:item-create")}"' in empty_content

        ItemFactory.create_batch(30)
        populated_content = client.get(reverse("item-list-cards")).content.decode()
        assert "1-24 of 30" in populated_content
        assert 'href="?page=2"' in populated_content

    def test_the_contributor_page_still_presents_cards(self, client, db):
        contributor = NameFactory()
        item = ItemFactory(title="A Contributor Page Reference")
        ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
        content = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})).content.decode()
        assert "<table" not in content
        assert "A Contributor Page Reference" in content

    def test_no_template_is_copied_out_of_the_package_to_render_the_cards(self):
        # Every template the card chain reaches for resolves inside the
        # literature package itself, so a project routing at ItemListView
        # needs to write nothing of its own to get the page FR-022 promises.
        package_root = Path(literature.__file__).resolve().parent
        for template_name in ("literature/ui/item_list_item.html", "literature/ui/contributor_item.html"):
            origin = Path(get_template(template_name).origin.name).resolve()
            assert package_root in origin.parents, f"{template_name} resolved outside the package at {origin}"


class TestTheCardListFiltersAndSearches:
    """US-4, T022 — the card list narrows the same way the table does, now
    that it is ``MVPFilteredListView`` (plan.md D-2, FR-024).
    """

    def test_a_search_term_narrows_the_card_list(self, client, db):
        matching = ItemFactory(title="Whale Migration Patterns")
        other = ItemFactory(title="Unrelated Reference")
        content = client.get(reverse("item-list-cards"), {"q": "whale"}).content.decode()
        assert matching.title in content
        assert other.title not in content

    def test_a_filter_narrows_the_card_list(self, client, db):
        book = ItemFactory(type=ItemType.BOOK)
        article = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = client.get(reverse("item-list-cards"), {"type": ItemType.BOOK}).content.decode()
        assert book.citation_key in content
        assert article.citation_key not in content

    def test_a_sort_with_no_filter_in_force_shows_no_applied_filter_badge(self, client, db):
        # The finding this task exists for: MVPFilteredListView's own
        # get_context_data() (mvp/integrations/django_filters/views.py)
        # counts every non-empty field of filterset.form.cleaned_data, and
        # "sort" (literature/ui/filters.py ItemFilterSet.sort) is a hidden
        # field on that form carrying django-tables2's own ordering (plan.md
        # D-7) — not one of the catalogue's own filters (decisions.md D21).
        # Proven through the shared exclusion function, not a second copy of
        # the table's own override (decisions.md D20).
        ItemFactory()
        response = client.get(reverse("item-list-cards"), {"sort": "-citation_key"})
        assert not response.context.get("applied_filters")
        content = response.content.decode()
        assert "indicator-item badge badge-secondary badge-xs" not in content


class TestItemTableView:
    """The catalogue as a table — US-1 (FR-001 through FR-012, FR-021, plan.md D-2)."""

    def test_column_headers_appear_in_the_required_order(self, client, db):
        # decisions.md D16: reads the table's own header row, not the whole
        # rendered page — the filter modal (this feature's own FR-009 to
        # FR-013) renders ahead of the table and emits "Type" as a literal
        # filter-field label before the table's own "Type" column header, so
        # a page-wide substring search stopped being a faithful proxy for
        # "the table's columns sit in this order".
        content = client.get(reverse("literature:item-list")).content.decode()
        header_row = table_header_row(content)
        headers = ["Citation key", "Type", "Title", "Container title", "Authors", "Issued"]
        positions = [header_row.index(header) for header in headers]
        assert positions == sorted(positions)

    def test_no_cell_renders_stored_text_unescaped(self, client, db):
        # Every free-text column at once, on the rendered page rather than
        # on a cell: a plain column's own cell value is its raw text and the
        # escaping is the table template's, so a cell-level assertion would
        # be checking the wrong layer. All four fields below are entered
        # through this package's own write pages, which it deliberately
        # leaves open (Article V).
        payload = "<script>alert(1)</script>"
        item = ItemFactory(citation_key=payload, title=payload, container_title=payload)
        ItemNameFactory(item=item, name=NameFactory(family=payload, given=""), role=NameRole.AUTHOR)

        content = client.get(reverse("literature:item-list")).content.decode()

        assert payload not in content
        assert content.count("&lt;script&gt;alert(1)&lt;/script&gt;") == 4

    def test_a_row_carries_all_six_data_columns_for_one_reference(self, client, db):
        item = ItemFactory(
            title="A Complete Reference",
            citation_key="Complete2026",
            container_title="Journal of Everything",
            type=ItemType.ARTICLE_JOURNAL,
        )
        item_name = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "Complete2026" in content
        assert "Journal Article" in content
        assert "A Complete Reference" in content
        assert "Journal of Everything" in content
        assert str(item_name.name) in content
        assert "2020" in content

    def test_paging_to_the_next_page_renders_the_next_rows_under_the_same_headings(self, client, db):
        ItemFactory.create_batch(30)
        response = client.get(reverse("literature:item-list"), {"page": 2})
        content = response.content.decode()
        assert response.status_code == 200
        assert "Citation key" in content
        # The table's own page (decisions.md D14) — see the sibling
        # assertion above for why object_list no longer means this here.
        assert len(response.context["table"].page.object_list) == 6

    def test_query_count_does_not_grow_with_row_count(self, client, db):
        # FR-012 — proves T009's prefetches are actually being read, rather
        # than the manager (research R9): the credited-names cell filtering
        # record.item_names.filter(...) would cost one query per row.
        #
        # FR-026 — extended, not duplicated (tasks.md T012): every item's
        # title carries the same term throughout, so a search for it goes on
        # matching the whole catalogue as it grows, and the query count under
        # search is compared against itself at two sizes exactly as the
        # unfiltered count is above.
        def add_items(n):
            for _ in range(n):
                item = ItemFactory(title="Whale Reference")
                ItemNameFactory(item=item)
                ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2021")

        add_items(3)
        with CaptureQueriesContext(connection) as small_catalogue:
            response = client.get(reverse("literature:item-list"))
        assert response.status_code == 200

        add_items(15)
        with CaptureQueriesContext(connection) as large_catalogue:
            response = client.get(reverse("literature:item-list"))
        assert response.status_code == 200

        assert len(large_catalogue.captured_queries) == len(small_catalogue.captured_queries)

        with CaptureQueriesContext(connection) as small_search:
            response = client.get(reverse("literature:item-list"), {"q": "whale"})
        assert response.status_code == 200

        add_items(15)
        with CaptureQueriesContext(connection) as large_search:
            response = client.get(reverse("literature:item-list"), {"q": "whale"})
        assert response.status_code == 200

        assert len(large_search.captured_queries) == len(small_search.captured_queries)

    def test_the_edit_control_renders_and_points_at_each_rows_own_update_page(self, client, db):
        item = ItemFactory()
        content = client.get(reverse("literature:item-list")).content.decode()
        update_url = reverse("literature:item-update", kwargs={"pk": item.pk})
        assert f'href="{update_url}"' in content

    def test_the_edit_control_follows_show_update_action_like_the_reference_pages_own(self, client, db, monkeypatch):
        # FR-020 — the same CRUDDirectoryMixin flag ItemDetailView's own edit
        # action reads (literature/ui/views.py), overridden here the same way
        # a project would override it to gate the write page.
        from literature.ui.views import ItemTableView

        monkeypatch.setattr(ItemTableView, "show_update_action", False)
        item = ItemFactory()
        content = client.get(reverse("literature:item-list")).content.decode()
        update_url = reverse("literature:item-update", kwargs={"pk": item.pk})
        assert f'href="{update_url}"' not in content

    def test_the_control_and_its_target_are_reachable_with_no_authentication(self, client, db):
        # FR-020 — this feature introduces no permission check, login
        # requirement or other access control of its own. ``client`` here is
        # the plain, unauthenticated test client every other assertion in
        # this module already uses; both pages 200 for it.
        item = ItemFactory()
        assert client.get(reverse("literature:item-list")).status_code == 200
        assert client.get(reverse("literature:item-update", kwargs={"pk": item.pk})).status_code == 200

    def test_carries_search_and_filter_but_no_column_chooser(self, client, db):
        # FS-009 wrote this test's ancestor for FR-025 to lock search and
        # filter off; this feature's own FR-001 and FR-009 to FR-013 turn
        # them back on over a signed-off specification, so the assertion
        # follows the requirement rather than the old one (decisions.md D16
        # — FS-009's FR-025 is annotated as superseded in place in
        # specs/009-tabular-catalogue-view/spec.md). Still asserted against
        # the rendered page rather than only the view's own configuration,
        # and still closed in both directions, so an upstream default
        # widening the action surface is still caught.
        ItemFactory()
        response = client.get(reverse("literature:item-list"))
        content = response.content.decode()
        assert response.context["table_actions"] == ["search", "filter", "create"]
        assert 'name="q"' in content  # the search box's own input name
        assert "filterModal" in content  # the filter control's own modal id
        # No column-chooser ships in either django-tables2 or django-mvp
        # today — nothing here builds one, and the closed actions list above
        # is what would carry it if a future default introduced one.

    def test_the_search_box_submits_through_the_filter_form(self, client, db):
        # T008, research R4: the search input renders with `form="filterForm"`,
        # and `filterForm` is only declared inside `{% if filter %}` — a
        # context key only FilterView sets. Without filterset_class
        # configured, the input would be wired to a form that does not
        # exist and typing into it would do nothing. Asserted on the
        # literal markup, not merely on both controls being present, so a
        # future markup change that renamed either id would still be caught.
        ItemFactory()
        content = client.get(reverse("literature:item-list")).content.decode()
        assert 'name="q" form="filterForm"' in content
        assert 'id="filterForm"' in content
        # No column-chooser ships in either django-tables2 or django-mvp
        # today — nothing here builds one, and the closed actions list above
        # is what would carry it if a future default introduced one.

    def test_the_queryset_annotates_issued_matching_the_items_own_issued_date(self, client, db):
        # T017 — the Subquery ordering will read at T018 (plan.md D-8,
        # research R7). A join-based filter is deliberately not used, since
        # it risks row multiplication and interferes with the paginator's
        # count query.
        #
        # decisions.md D18: the annotation is a raw column value, typed
        # DateTimeField (D12) so issued__year resolves, and its seconds
        # component encodes the source date's precision rather than
        # round-tripping through PartialDateField — compared here against
        # the issued slot's own calendar date, not against a PartialDate.
        # Still discriminating: the reference also carries an accessed date
        # of 2021-01-01, so an annotation drawing from the wrong date slot
        # still fails. Nothing renders this annotation directly — the
        # rendered cell reads the prefetched ItemDate row instead
        # (literature/ui/tables.py IssuedColumn), which is where the
        # precision-and-range display rule lives.
        item = ItemFactory()
        issued_date = ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020-05-01")
        issued_date.refresh_from_db()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2021-01-01")
        response = client.get(reverse("literature:item-list"))
        (annotated_item,) = [row for row in response.context["object_list"] if row.pk == item.pk]
        assert annotated_item.issued.date() == issued_date.begin.date

    def test_the_issued_annotation_is_none_for_a_reference_with_no_issued_date(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2021-01-01")
        response = client.get(reverse("literature:item-list"))
        (annotated_item,) = [row for row in response.context["object_list"] if row.pk == item.pk]
        assert annotated_item.issued is None


class TestCatalogueSearch:
    """Searching the catalogue from an HTTP request — FR-002 through FR-005."""

    @pytest.mark.parametrize(
        "field",
        ["citation_key", "title", "title_short", "original_title", "container_title"],
    )
    def test_matches_a_term_in_each_scalar_field(self, client, db, field):
        matching = ItemFactory(**{field: "Whale Migration Patterns"})
        other = ItemFactory()
        content = client.get(reverse("literature:item-list"), {"q": "whale"}).content.decode()
        assert matching.citation_key in content
        assert other.citation_key not in content

    def test_matches_a_contributors_family_name(self, client, db):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(family="Darwin"))
        other = ItemFactory()
        content = client.get(reverse("literature:item-list"), {"q": "darwin"}).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_matches_a_contributors_given_name(self, client, db):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(given="Charles"))
        other = ItemFactory()
        content = client.get(reverse("literature:item-list"), {"q": "charles"}).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_matches_an_organizational_literal_name(self, client, db):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(family="", given="", literal="Smithsonian Institution"))
        other = ItemFactory()
        content = client.get(reverse("literature:item-list"), {"q": "smithsonian"}).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_matching_is_case_insensitive(self, client, db):
        item = ItemFactory(title="Whale Migration Patterns")
        other = ItemFactory()
        content = client.get(reverse("literature:item-list"), {"q": "WHALE"}).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_a_fragment_living_only_in_the_abstract_or_a_keyword_finds_nothing(self, client, db):
        # FR-004 — neither field is in SEARCH_FIELDS (tests/test_ui/test_filters.py
        # ::TestSearchFields already pins the declared list itself).
        ItemFactory(abstract="Discusses whale migration patterns at length.")
        ItemFactory(keyword="whale, migration")
        response = client.get(reverse("literature:item-list"), {"q": "whale"})
        assert len(response.context["table"].page.object_list) == 0

    def test_a_reference_matching_several_fields_appears_once(self, client, db):
        # FR-005, plan D-4 — the shared fragment sits in three different
        # searched paths (title, container_title, a contributor's family
        # name) at once, over a distinct row so no other match can hide a
        # duplicate.
        item = ItemFactory(title="Zzyxq Behavior", container_title="The Zzyxq Journal")
        ItemNameFactory(item=item, name=NameFactory(family="Zzyxqson"))
        response = client.get(reverse("literature:item-list"), {"q": "zzyxq"})
        matches = [row for row in response.context["table"].page.object_list if row.record.pk == item.pk]
        assert len(matches) == 1

    def test_a_one_character_fragment_matches_literally(self, client, db):
        item = ItemFactory(title="Zebra Migration")
        other = ItemFactory(title="Unrelated Reference")
        content = client.get(reverse("literature:item-list"), {"q": "Z"}).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_a_term_of_only_spaces_is_a_no_op(self, client, db):
        # FR-006 — the upstream mixin strips and checks truthiness before
        # filtering at all, so this is the empty-query no-op (FR-008) under
        # a different guise rather than a wildcard match.
        ItemFactory.create_batch(3)
        response = client.get(reverse("literature:item-list"), {"q": "   "})
        assert len(response.context["table"].page.object_list) == 3

    def test_a_percent_sign_is_matched_literally_not_as_a_wildcard(self, client, db):
        # FR-006 — "%" is the database's own multi-character wildcard. A
        # naive, unescaped `LIKE '%' || value || '%'` would match "100X..."
        # too, since the user's own "%" would itself act as a wildcard;
        # confirmed directly against this database with an unescaped raw
        # query before writing this test. Django's ORM-level icontains
        # escapes the value first, so only the literal substring matches.
        literal_match = ItemFactory(title="100% Guaranteed Results")
        decoy = ItemFactory(title="100X Guaranteed Results")
        content = client.get(reverse("literature:item-list"), {"q": "100%"}).content.decode()
        assert literal_match.citation_key in content
        assert decoy.citation_key not in content

    def test_an_underscore_is_matched_literally_not_as_a_wildcard(self, client, db):
        # FR-006 — "_" is the database's own single-character wildcard,
        # confirmed the same way as the "%" case above.
        literal_match = ItemFactory(title="Sample_ID Formation")
        decoy = ItemFactory(title="SampleXID Formation")
        content = client.get(reverse("literature:item-list"), {"q": "Sample_ID"}).content.decode()
        assert literal_match.citation_key in content
        assert decoy.citation_key not in content

    def test_a_search_matching_something_states_how_many(self, client, db):
        # FR-007 — django-mvp's own position line, which already reads the
        # table's narrowed page and paginator (no production change of this
        # feature's own): confirmed the search reduces what it counts, not
        # only what it lists.
        ItemFactory.create_batch(3)
        ItemFactory(title="Zzyxq Unique Match")
        content = client.get(reverse("literature:item-list"), {"q": "zzyxq"}).content.decode()
        assert "1-1 of 1" in content

    def test_a_search_matching_nothing_states_so_and_keeps_its_controls(self, client, db):
        # FR-028, plan.md D-8 — distinct from the genuinely-empty-catalogue
        # message below, and the search box and filter control both stay on
        # the page rather than disappearing along with the rows.
        ItemFactory.create_batch(3)
        content = client.get(reverse("literature:item-list"), {"q": "no-such-term-anywhere"}).content.decode()
        assert "No references match your search" in content
        assert "Nothing in the catalogue yet" not in content
        assert 'name="q"' in content
        assert "filterModal" in content

    def test_a_genuinely_empty_catalogue_keeps_its_own_message(self, client, db):
        # FR-028, plan.md D-8 — the two messages never appear together; this
        # is the other half of the pair above, with no query in force at all.
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "Nothing in the catalogue yet" in content
        assert "No references match your search" not in content

    @pytest.mark.parametrize("clearing_params", [{"q": ""}, {}], ids=["empty-q", "no-q"])
    def test_clearing_the_search_restores_the_unnarrowed_catalogue(self, client, db, clearing_params):
        # FR-008 — a request carrying an empty q, and one carrying no q at
        # all, each return the whole catalogue where the preceding search
        # had narrowed it. Upstream's search mixin already no-ops on an
        # empty term; this is the guard that it goes on doing so.
        ItemFactory.create_batch(5)
        narrowed = client.get(reverse("literature:item-list"), {"q": "no-such-term-anywhere"})
        assert len(narrowed.context["table"].page.object_list) == 0
        cleared = client.get(reverse("literature:item-list"), clearing_params)
        assert len(cleared.context["table"].page.object_list) == 5


class TestCatalogueFilters:
    """Each filter on its own against the table — FR-009 through FR-013.

    The filterset itself is already exercised directly in
    ``tests/test_ui/test_filters.py``; this class proves the same behaviour
    reaches an HTTP request through ``ItemTableView``, which is this story's
    own scope (plan.md D-1, D-4, D-5).
    """

    def test_type_narrows_to_the_chosen_type(self, client, db):
        book = ItemFactory(type=ItemType.BOOK)
        article = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = client.get(reverse("literature:item-list"), {"type": ItemType.BOOK}).content.decode()
        assert book.citation_key in content
        assert article.citation_key not in content

    def test_type_choices_offer_the_translatable_label_while_the_url_narrows_on_the_stored_value(self, client, db):
        # FR-010 — the select option pairs the stored slug (the value the
        # query string above narrows on) with its translated label, read
        # from the filter control itself rather than a row's own type cell,
        # which would pass even if the filter control's own choices broke.
        content = client.get(reverse("literature:item-list")).content.decode()
        assert re.search(r'<option value="article-journal"[^>]*>\s*Journal Article\s*</option>', content)

    def test_contributor_narrows_to_references_crediting_them_in_any_role(self, client, db):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(family="Darwin"), role=NameRole.EDITOR)
        other = ItemFactory()
        content = client.get(reverse("literature:item-list"), {"contributor": "darwin"}).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_a_reference_crediting_the_same_contributor_in_two_roles_is_returned_once(self, client, db):
        item = ItemFactory()
        darwin = NameFactory(family="Darwin")
        ItemNameFactory(item=item, name=darwin, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=darwin, role=NameRole.EDITOR)
        response = client.get(reverse("literature:item-list"), {"contributor": "darwin"})
        matches = [row for row in response.context["table"].page.object_list if row.record.pk == item.pk]
        assert len(matches) == 1

    def test_issued_year_narrows_on_a_year_only_stored_date(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        other = ItemFactory()
        ItemDateFactory(item=other, date_type=DateType.ISSUED, begin="2021")
        content = client.get(reverse("literature:item-list"), {"issued_year": 2020}).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_issued_year_narrows_on_a_range_beginning_that_year(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2019", end="2021")
        other = ItemFactory()
        ItemDateFactory(item=other, date_type=DateType.ISSUED, begin="2021")
        content = client.get(reverse("literature:item-list"), {"issued_year": 2019}).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_issued_year_excludes_a_reference_carrying_no_issued_date(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        undated = ItemFactory()
        content = client.get(reverse("literature:item-list"), {"issued_year": 2020}).content.decode()
        assert item.citation_key in content
        assert undated.citation_key not in content

    def test_language_narrows_on_the_stored_value(self, client, db):
        en_item = ItemFactory(language="en")
        other = ItemFactory(language="fr")
        content = client.get(reverse("literature:item-list"), {"language": "en"}).content.decode()
        assert en_item.citation_key in content
        assert other.citation_key not in content

    def test_language_choices_offer_only_values_the_catalogue_holds(self, client, db):
        ItemFactory(language="en")
        content = client.get(reverse("literature:item-list")).content.decode()
        assert re.search(r'<option value="en"[^>]*>\s*en\s*</option>', content)
        assert 'value="de"' not in content


class TestCatalogueFilterComposition:
    """Composing filters and search — FR-014, FR-015, decisions.md D6.

    "Articles or chapters, from 2019" is D6's own example: one filter
    (type) widened to either value, another (year) narrowing what that
    widened set returns.
    """

    def test_more_than_one_value_within_a_filter_widens_to_either(self, client, db):
        article = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        chapter = ItemFactory(type=ItemType.CHAPTER)
        book = ItemFactory(type=ItemType.BOOK)
        content = client.get(
            reverse("literature:item-list"), {"type": [ItemType.ARTICLE_JOURNAL, ItemType.CHAPTER]}
        ).content.decode()
        assert article.citation_key in content
        assert chapter.citation_key in content
        assert book.citation_key not in content

    def test_two_filters_narrow_to_both(self, client, db):
        matching = ItemFactory(type=ItemType.BOOK, language="en")
        wrong_type = ItemFactory(type=ItemType.ARTICLE_JOURNAL, language="en")
        wrong_language = ItemFactory(type=ItemType.BOOK, language="fr")
        content = client.get(
            reverse("literature:item-list"), {"type": ItemType.BOOK, "language": "en"}
        ).content.decode()
        assert matching.citation_key in content
        assert wrong_type.citation_key not in content
        assert wrong_language.citation_key not in content

    def test_a_filter_and_a_search_term_narrow_to_both_and_the_count_reflects_it(self, client, db):
        matching = ItemFactory(type=ItemType.BOOK, title="Whale Migration Patterns")
        wrong_type = ItemFactory(type=ItemType.ARTICLE_JOURNAL, title="Whale Migration Patterns")
        wrong_term = ItemFactory(type=ItemType.BOOK, title="Unrelated Reference")
        response = client.get(reverse("literature:item-list"), {"q": "whale", "type": ItemType.BOOK})
        content = response.content.decode()
        assert matching.citation_key in content
        assert wrong_type.citation_key not in content
        assert wrong_term.citation_key not in content
        assert "1-1 of 1" in content

    def test_widening_within_type_still_narrows_against_a_second_filter(self, client, db):
        # Both directions in one request: "articles or chapters, from 2019".
        article_2019 = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        ItemDateFactory(item=article_2019, date_type=DateType.ISSUED, begin="2019")
        chapter_2019 = ItemFactory(type=ItemType.CHAPTER)
        ItemDateFactory(item=chapter_2019, date_type=DateType.ISSUED, begin="2019")
        book_2019 = ItemFactory(type=ItemType.BOOK)
        ItemDateFactory(item=book_2019, date_type=DateType.ISSUED, begin="2019")
        article_2020 = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        ItemDateFactory(item=article_2020, date_type=DateType.ISSUED, begin="2020")
        content = client.get(
            reverse("literature:item-list"),
            {"type": [ItemType.ARTICLE_JOURNAL, ItemType.CHAPTER], "issued_year": 2019},
        ).content.decode()
        assert article_2019.citation_key in content
        assert chapter_2019.citation_key in content
        assert book_2019.citation_key not in content
        assert article_2020.citation_key not in content


class TestCatalogueFilterVisibility:
    """What is in force is visible on the page and clearable from it — FR-016.

    django-mvp's own badge (``mvp/templates/cotton/page/list/actions/filter.html``)
    reads ``applied_filters``/``applied_filter_count`` from the context, but
    only ``MVPFilteredListView.get_context_data()`` (the card list's own base,
    plan.md D-2) populates them — ``ItemTableView`` composes
    ``MVPTableViewMixin, FilterView`` instead, and never ran that method, so
    the table carried a filter control with no badge at all. Confirmed
    directly before writing these tests: an unfiltered request already
    leaves ``response.context["applied_filters"]`` at ``None``.
    """

    def test_no_badge_when_nothing_is_applied(self, client, db):
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "indicator-item badge badge-secondary badge-xs" not in content

    def test_a_filter_in_force_is_counted_and_shown_as_a_badge(self, client, db):
        ItemFactory(type=ItemType.BOOK)
        response = client.get(reverse("literature:item-list"), {"type": ItemType.BOOK})
        assert response.context["applied_filter_count"] == 1
        content = response.content.decode()
        assert '<span class="indicator-item badge badge-secondary badge-xs">1</span>' in content

    def test_two_filters_in_force_are_both_counted(self, client, db):
        ItemFactory(type=ItemType.BOOK, language="en")
        response = client.get(reverse("literature:item-list"), {"type": ItemType.BOOK, "language": "en"})
        assert response.context["applied_filter_count"] == 2
        content = response.content.decode()
        assert '<span class="indicator-item badge badge-secondary badge-xs">2</span>' in content

    def test_a_search_term_alone_carries_no_filter_badge(self, client, db):
        # The badge belongs to the Filter button specifically (FR-016 governs
        # both controls, but django-mvp's own count is filter-only) — `q` is
        # not one of `self.filterset.filters`, so it never reaches
        # `filterset.form.cleaned_data`.
        ItemFactory(title="Whale Migration Patterns")
        content = client.get(reverse("literature:item-list"), {"q": "whale"}).content.decode()
        assert "indicator-item badge badge-secondary badge-xs" not in content

    def test_the_chosen_value_stays_selected_on_the_rendered_control(self, client, db):
        ItemFactory(type=ItemType.BOOK)
        content = client.get(reverse("literature:item-list"), {"type": ItemType.BOOK}).content.decode()
        assert re.search(r'<option value="book"[^>]*\sselected[^>]*>\s*Book\s*</option>', content)

    @pytest.mark.parametrize("clearing_params", [{"type": ""}, {}], ids=["empty-type", "no-params"])
    def test_clearing_a_filter_restores_the_unfiltered_catalogue(self, client, db, clearing_params):
        matching = ItemFactory(type=ItemType.BOOK)
        other = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        narrowed = client.get(reverse("literature:item-list"), {"type": ItemType.BOOK})
        assert len(narrowed.context["table"].page.object_list) == 1
        cleared = client.get(reverse("literature:item-list"), clearing_params)
        cleared_pks = {row.record.pk for row in cleared.context["table"].page.object_list}
        assert cleared_pks == {matching.pk, other.pk}


class TestCatalogueFilterValidation:
    """Invalid and unmatched filter values — FR-017, decisions.md D7.

    Two cases and only two: a declared filter's value matching nothing, and
    a declared filter's value that fails validation. Both already narrow to
    nothing through the adopted components — django-filter's own ``strict``
    default (``BaseFilterView.get()``) returns an empty queryset for an
    invalid bound form, and an unmatched value is simply a filter that
    matches no row — so this task proves the behaviour rather than building
    it.
    """

    def test_an_unmatched_value_of_a_declared_filter_states_no_matches(self, client, db):
        ItemFactory(language="en")
        response = client.get(reverse("literature:item-list"), {"language": "zz"})
        content = response.content.decode()
        assert response.status_code == 200
        assert len(response.context["table"].page.object_list) == 0
        assert "No references match your search" in content

    def test_an_invalid_value_of_a_declared_filter_states_no_matches(self, client, db):
        ItemFactory()
        response = client.get(reverse("literature:item-list"), {"issued_year": "notanumber"})
        content = response.content.decode()
        assert response.status_code == 200
        assert len(response.context["table"].page.object_list) == 0
        assert "No references match your search" in content

    def test_neither_case_falls_back_to_the_unfiltered_catalogue(self, client, db):
        ItemFactory.create_batch(3, language="en")
        unmatched = client.get(reverse("literature:item-list"), {"language": "zz"})
        assert len(unmatched.context["table"].page.object_list) == 0
        invalid = client.get(reverse("literature:item-list"), {"issued_year": "notanumber"})
        assert len(invalid.context["table"].page.object_list) == 0

    def test_an_address_carrying_an_undeclared_key_is_ignored_not_rejected(self, client, db):
        # FR-017 reads on a filter *value*, not an undefined key: a Django
        # form simply ignores data it has no field for, so an address like
        # this is neither of the two cases above, and this feature
        # deliberately builds no rejection mechanism for it (tasks.md T016).
        # Pinned as what actually happens — 200, no exception, the
        # catalogue unnarrowed — not as a contract this feature owns.
        item = ItemFactory()
        response = client.get(reverse("literature:item-list"), {"bogus": "xyz"})
        assert response.status_code == 200
        assert [row.record.pk for row in response.context["table"].page.object_list] == [item.pk]


#: One item-building override per plain sortable column, cycled by index so
#: 30 references get 30 distinct, independently-sortable values (T019).
#: "type" cycles a fixed set of stored slugs rather than a unique value per
#: item — sorting is still monotonic across ties, and it doubles as FR-017's
#: check that ordering follows the stored slug, not the translated label.
PLAIN_SORTABLE_COLUMN_OVERRIDES = {
    "citation_key": lambda n: {"citation_key": f"Key{n:03d}"},
    "title": lambda n: {"title": f"Title{n:03d}"},
    "container_title": lambda n: {"container_title": f"Container{n:03d}"},
    "type": lambda n: {"type": [ItemType.ARTICLE, ItemType.BOOK, ItemType.CHAPTER][n % 3]},
}


class TestCatalogueOrdering:
    """Sorting the catalogue from an HTTP request — FR-013 through FR-018 (plan.md D-8, research R7)."""

    def catalogue_column_values(self, client, column, sort_param=None):
        """Every reference's ``column`` value, gathered across both pages of
        a 30-row catalogue — proving a sort is applied to the whole
        queryset rather than only to whichever rows a page happens to
        show.

        Reads ``table.page`` rather than the plain ``object_list`` context
        key: ``SingleTableMixin`` sorts and paginates its own copy of the
        queryset independently of ``MVPListViewMixin``'s, and ``object_list``
        never reflects the sort at all.
        """
        values = []
        params = {"sort": sort_param} if sort_param else {}
        for page in (1, 2):
            response = client.get(reverse("literature:item-list"), {**params, "page": page})
            values += [getattr(row.record, column) for row in response.context["table"].page.object_list]
        return values

    @pytest.mark.parametrize("column", sorted(PLAIN_SORTABLE_COLUMN_OVERRIDES))
    def test_ascending_sort_orders_the_whole_catalogue_not_only_the_current_page(self, client, db, column):
        # 30 references over a 24-row page (FR-014, FR-016).
        for n in range(30):
            ItemFactory(**PLAIN_SORTABLE_COLUMN_OVERRIDES[column](n))
        values = self.catalogue_column_values(client, column, sort_param=column)
        assert len(values) == 30
        assert values == sorted(values)

    def test_ascending_sort_by_issued_date_keeps_undated_references_last(self, client, db):
        # FR-018 — read through the HTTP sort param rather than only through
        # order_issued directly (TestIssuedOrdering already covers that).
        dated_keys = []
        for n in range(20):
            item = ItemFactory(citation_key=f"Dated{n:03d}")
            ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=str(2000 + n))
            dated_keys.append(item.citation_key)
        undated_keys = {ItemFactory(citation_key=f"Undated{n:03d}").citation_key for n in range(10)}
        citation_keys = self.catalogue_column_values(client, "citation_key", sort_param="issued")
        assert citation_keys[:20] == dated_keys
        assert set(citation_keys[20:]) == undated_keys

    def test_sort_direction_reverses_on_a_second_request(self, client, db):
        for n in range(30):
            ItemFactory(citation_key=f"Key{n:03d}")
        ascending = self.catalogue_column_values(client, "citation_key", sort_param="citation_key")
        descending = self.catalogue_column_values(client, "citation_key", sort_param="-citation_key")
        assert ascending == list(reversed(descending))
        assert ascending != descending

    def test_sort_by_the_contributors_column_is_refused(self, client, db):
        # FR-015 — the credited-names cell has no single value to order on.
        first = ItemFactory(citation_key="First")
        second = ItemFactory(citation_key="Second")
        response = client.get(reverse("literature:item-list"), {"sort": "contributors"})
        assert response.status_code == 200
        # Refused, not errored: django-tables2 silently drops an order_by
        # alias naming a non-orderable column, so the table keeps its
        # default newest-first order rather than raising or reordering.
        citation_keys = [row.record.citation_key for row in response.context["table"].page.object_list]
        assert citation_keys == [second.citation_key, first.citation_key]

    def test_sort_by_the_actions_column_is_refused(self, client, db):
        # FR-015 — a control, not data, has no single value to order on.
        first = ItemFactory(citation_key="First")
        second = ItemFactory(citation_key="Second")
        response = client.get(reverse("literature:item-list"), {"sort": "actions"})
        assert response.status_code == 200
        citation_keys = [row.record.citation_key for row in response.context["table"].page.object_list]
        assert citation_keys == [second.citation_key, first.citation_key]

    def test_sort_survives_following_the_rendered_link_to_page_2(self, client, db):
        # citation_key runs the opposite way to creation order, so a sort by
        # -citation_key produces a different row order than the catalogue's
        # default (-created) — a test where the two coincide would pass
        # whether or not the followed link actually carried the sort.
        for n in range(30):
            ItemFactory(citation_key=f"Key{29 - n:03d}")
        list_url = reverse("literature:item-list")
        first_page = client.get(list_url, {"sort": "-citation_key"})
        second_page_href = rendered_page_link(first_page.content.decode(), 2)
        second_page = client.get(urljoin(list_url, second_page_href))
        first_page_records = [row.record for row in first_page.context["table"].page.object_list]
        second_page_records = [row.record for row in second_page.context["table"].page.object_list]
        # Still descending across the page boundary.
        assert second_page_records[0].citation_key < first_page_records[-1].citation_key


class TestCatalogueStateSurvivesAPageMove:
    """A search and a filter each survive a page move too, and all three
    survive together — FR-018, closing #88 alongside the sort case above.

    Followed through the page's own rendered link (``rendered_page_link()``,
    decisions.md D13), never a hand-built ``?page=2`` — asserted on the
    second page's own results, not merely on the shape of the link that
    reached it.
    """

    def test_a_search_survives_following_the_rendered_link_to_page_2(self, client, db):
        for n in range(30):
            ItemFactory(title=f"Whale Migration {n:03d}")
        ItemFactory.create_batch(5, title="Unrelated Reference")
        list_url = reverse("literature:item-list")
        first_page = client.get(list_url, {"q": "whale"})
        first_page_records = [row.record for row in first_page.context["table"].page.object_list]
        second_page_href = rendered_page_link(first_page.content.decode(), 2)
        second_page = client.get(urljoin(list_url, second_page_href))
        second_page_records = [row.record for row in second_page.context["table"].page.object_list]
        assert second_page_records
        # Not merely "narrowed" — the second page's own rows, distinct from
        # the first's. A ?page=2 read as the literal parameter "amp;page"
        # falls back to page one, which would satisfy the narrowing
        # assertion below without ever proving a page move happened.
        assert {r.pk for r in second_page_records}.isdisjoint({r.pk for r in first_page_records})
        assert all("Whale Migration" in record.title for record in second_page_records)

    def test_a_filter_survives_following_the_rendered_link_to_page_2(self, client, db):
        ItemFactory.create_batch(30, type=ItemType.BOOK)
        ItemFactory.create_batch(5, type=ItemType.ARTICLE_JOURNAL)
        list_url = reverse("literature:item-list")
        first_page = client.get(list_url, {"type": ItemType.BOOK})
        first_page_records = [row.record for row in first_page.context["table"].page.object_list]
        second_page_href = rendered_page_link(first_page.content.decode(), 2)
        second_page = client.get(urljoin(list_url, second_page_href))
        second_page_records = [row.record for row in second_page.context["table"].page.object_list]
        assert second_page_records
        assert {r.pk for r in second_page_records}.isdisjoint({r.pk for r in first_page_records})
        assert all(record.type == ItemType.BOOK for record in second_page_records)

    def test_a_search_a_filter_and_a_sort_all_survive_together_following_the_rendered_link_to_page_2(self, client, db):
        for n in range(30):
            ItemFactory(type=ItemType.BOOK, title=f"Whale Migration {n:03d}", citation_key=f"Key{29 - n:03d}")
        ItemFactory.create_batch(5, type=ItemType.ARTICLE_JOURNAL, title="Whale Migration Decoy")
        ItemFactory.create_batch(5, type=ItemType.BOOK, title="Unrelated Reference")
        list_url = reverse("literature:item-list")
        params = {"q": "whale", "type": ItemType.BOOK, "sort": "-citation_key"}
        first_page = client.get(list_url, params)
        first_page_records = [row.record for row in first_page.context["table"].page.object_list]
        second_page_href = rendered_page_link(first_page.content.decode(), 2)
        second_page = client.get(urljoin(list_url, second_page_href))
        second_page_records = [row.record for row in second_page.context["table"].page.object_list]
        assert second_page_records
        assert all("Whale Migration" in record.title for record in second_page_records)
        assert all(record.type == ItemType.BOOK for record in second_page_records)
        assert second_page_records[0].citation_key < first_page_records[-1].citation_key


class TestCatalogueStateSurvivesAChangeOfSort:
    """A search and a filter survive a change of sort from a column heading,
    and the new sort orders what they narrowed, not the whole catalogue —
    FR-019. This direction already works; pinned here before T020 touches
    the filter form for the opposite direction.
    """

    def test_search_and_a_filter_survive_a_change_of_sort_from_a_column_heading(self, client, db):
        matching_high = ItemFactory(type=ItemType.BOOK, title="Whale Migration Zeta", citation_key="KeyZ")
        matching_low = ItemFactory(type=ItemType.BOOK, title="Whale Migration Alpha", citation_key="KeyA")
        wrong_type = ItemFactory(type=ItemType.ARTICLE_JOURNAL, title="Whale Migration Beta", citation_key="KeyB")
        wrong_term = ItemFactory(type=ItemType.BOOK, title="Unrelated Reference", citation_key="KeyC")
        list_url = reverse("literature:item-list")
        first_page = client.get(list_url, {"q": "whale", "type": ItemType.BOOK})
        sort_href = rendered_sort_link(first_page.content.decode(), "Citation key")
        sorted_response = client.get(urljoin(list_url, sort_href))
        sorted_records = [row.record for row in sorted_response.context["table"].page.object_list]
        # Narrowed to the two matches, not the whole four-row catalogue —
        # the search and the filter are both still in force.
        assert {r.pk for r in sorted_records} == {matching_high.pk, matching_low.pk}
        assert wrong_type.pk not in {r.pk for r in sorted_records}
        assert wrong_term.pk not in {r.pk for r in sorted_records}
        # Ordered by the clicked column, over only the narrowed set.
        assert [r.citation_key for r in sorted_records] == [matching_low.citation_key, matching_high.citation_key]


class TestCatalogueStateSurvivesAChangeOfFilter:
    """The sort survives a change of filter, carried as a hidden field on
    ``ItemFilterSet``'s own form — plan.md D-7, decisions.md D-20's own
    correction. The opposite direction from T019: there the sort came from
    a column heading and django-tables2 already carried the rest of the
    address; here the filter modal is our own GET form, and submitting it
    replaces the query string with only what that form's own fields carry.
    """

    def test_sort_survives_a_change_of_filter_submitted_from_the_filter_form(self, client, db):
        # citation_key runs the opposite way to creation order, so a sort
        # by -citation_key produces a different row order than the
        # catalogue's default (-created) — same reasoning as T017/T019's
        # own fixtures, and for the same reason: a test where the two
        # coincide would pass whether or not the sort actually survived.
        older_last_key = ItemFactory(type=ItemType.BOOK, citation_key="KeyZ")
        newer_first_key = ItemFactory(type=ItemType.BOOK, citation_key="KeyA")
        ItemFactory(type=ItemType.ARTICLE_JOURNAL, citation_key="KeyM")
        list_url = reverse("literature:item-list")
        first_response = client.get(list_url, {"sort": "-citation_key"})
        form_data = rendered_filter_form_data(first_response, type=ItemType.BOOK)
        filtered_response = client.get(list_url, form_data)
        filtered_records = [row.record for row in filtered_response.context["table"].page.object_list]
        # Narrowed to the two BOOK rows, and still ordered by -citation_key
        # (KeyZ before KeyA) — the catalogue's default (-created) would
        # order them the other way (newer_first_key before older_last_key).
        assert filtered_records == [older_last_key, newer_first_key]

    def test_an_active_sort_is_not_counted_or_shown_as_an_applied_filter(self, client, db):
        ItemFactory(type=ItemType.BOOK)
        list_url = reverse("literature:item-list")
        unsorted = client.get(list_url, {"type": ItemType.BOOK})
        sorted_ = client.get(list_url, {"type": ItemType.BOOK, "sort": "-citation_key"})
        assert sorted_.context["applied_filter_count"] == unsorted.context["applied_filter_count"]
        assert set(sorted_.context["applied_filters"]) == set(unsorted.context["applied_filters"])
        badge_re = r'<span class="indicator-item badge badge-secondary badge-xs">(\d+)</span>'
        sorted_badge = re.search(badge_re, sorted_.content.decode())
        unsorted_badge = re.search(badge_re, unsorted.content.decode())
        assert sorted_badge.group(1) == unsorted_badge.group(1)

    def test_a_sort_alone_carries_no_filter_badge(self, client, db):
        ItemFactory()
        content = client.get(reverse("literature:item-list"), {"sort": "-citation_key"}).content.decode()
        assert "indicator-item badge badge-secondary badge-xs" not in content


class TestCatalogueStateSurvivesReopeningTheAddress:
    """A narrowed catalogue can be bookmarked and reopened to the same
    result (FR-022, SC-004): the state lives in the address itself, not in
    a session, so a second, entirely unrelated client reaching the same
    address gets the same narrowed catalogue back.
    """

    def test_a_bookmarked_address_reopens_to_the_same_narrowed_result(self, db):
        matching = ItemFactory(type=ItemType.BOOK, title="Whale Migration Patterns")
        ItemFactory(type=ItemType.ARTICLE_JOURNAL, title="Whale Migration Patterns")
        ItemFactory(type=ItemType.BOOK, title="Unrelated Reference")
        list_url = reverse("literature:item-list")
        params = {"q": "whale", "type": ItemType.BOOK}
        # Two independent clients, no cookies shared between them — if the
        # narrowing lived in a session rather than the address, the second
        # would come back to the unfiltered catalogue instead.
        first_visit = Client().get(list_url, params)
        reopened = Client().get(list_url, params)
        first_pks = {row.record.pk for row in first_visit.context["table"].page.object_list}
        reopened_pks = {row.record.pk for row in reopened.context["table"].page.object_list}
        assert first_pks == {matching.pk}
        assert reopened_pks == first_pks


class TestItemCreateView:
    """Enter a reference by hand — US-1 (FR-001 through FR-011)."""

    def test_page_renders_and_the_type_select_carries_the_alpine_scoping(self, client, db):
        response = client.get(reverse("literature:item-create"))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'x-model="form.itemType"' in content
        assert 'x-init="form.itemType = $el.value"' in content

    def test_with_no_type_chosen_every_group_but_the_type_fields_own_is_guarded(self, client, db):
        # FR-002 — with no type chosen, only the type field itself has no
        # x-show guard; every one of the thirteen groups does, so nothing
        # else on a blank page shows.
        content = client.get(reverse("literature:item-create")).content.decode()
        for group in FieldGroups.GROUPS:
            assert f"includes('{group}')" in content
        assert content.count("x-show=") == len(FieldGroups.GROUPS)

    def test_posting_a_valid_form_stores_exactly_what_was_posted(self, client, db):
        data = create_page_post_data(
            client, type=ItemType.ARTICLE_JOURNAL, citation_key="Doe2024", title="A Handwritten Reference"
        )
        client.post(reverse("literature:item-create"), data)
        item = Item.objects.get(citation_key="Doe2024")
        assert item.type == ItemType.ARTICLE_JOURNAL
        assert item.title == "A Handwritten Reference"

    def test_posting_a_valid_form_redirects_to_the_new_items_detail_page(self, client, db):
        data = create_page_post_data(client, type=ItemType.ARTICLE_JOURNAL, citation_key="Redirect2024")
        response = client.post(reverse("literature:item-create"), data)
        item = Item.objects.get(citation_key="Redirect2024")
        assert response.status_code == 302
        assert response.url == reverse("literature:item-detail", kwargs={"pk": item.pk})

    def test_posting_without_a_type_stores_nothing_and_names_the_field(self, client, db):
        data = create_page_post_data(client, type="", citation_key="NoType2024")
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 200
        assert not Item.objects.filter(citation_key="NoType2024").exists()
        assert "type" in response.context["form"].errors

    def test_posting_without_a_citation_key_stores_nothing_and_names_the_field(self, client, db):
        data = create_page_post_data(client, type=ItemType.ARTICLE_JOURNAL, citation_key="")
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 200
        assert Item.objects.count() == 0
        assert "citation_key" in response.context["form"].errors

    def test_a_duplicate_citation_key_is_stored_unchanged_with_no_warning(self, client, db):
        # FR-007 — citation_key is not globally unique; a colliding key is a
        # fact the store holds, never a validation error.
        # citation_key deliberately avoids the word "duplicate" itself, so the
        # no-warning assertion below cannot pass by accident on the key's own text.
        ItemFactory(citation_key="Repeated2024")
        data = create_page_post_data(client, type=ItemType.ARTICLE_JOURNAL, citation_key="Repeated2024")
        response = client.post(reverse("literature:item-create"), data, follow=True)
        assert Item.objects.filter(citation_key="Repeated2024").count() == 2
        content = response.content.decode().lower()
        assert "already exists" not in content
        assert "duplicate" not in content

    def test_a_created_items_detail_page_renders_with_no_contributors_dates_or_identifiers(self, client, db):
        data = create_page_post_data(client, type=ItemType.ARTICLE_JOURNAL, citation_key="Bare2024")
        response = client.post(reverse("literature:item-create"), data, follow=True)
        assert response.status_code == 200
        assert response.context["contributor_groups"] == []
        assert response.context["identifiers"] == []


class TestItemUpdateView:
    """Correct a reference that is wrong — US-2 (FR-009 through FR-014)."""

    def test_saving_an_unchanged_form_leaves_every_stored_field_identical(self, client, db):
        # SC-003 — the whole no-loss guarantee, and the most valuable test in
        # the feature. A value in every scalar field the form carries, plus
        # the two JSON fields it never carries (categories, custom — D-4),
        # must survive an unchanged round trip through the rendered edit
        # form. created/modified are auto_now_add/auto_now and change on
        # every save by design (DR-010), so they are excluded on purpose,
        # not by oversight.
        from literature.ui.forms import FORM_FIELDS

        values = {}
        for name in FORM_FIELDS:
            if name == "type":
                continue
            field = Item._meta.get_field(name)
            # Underscore-joined, not space-joined: Django's CharField strips
            # surrounding whitespace by default, and a value truncated to a
            # short max_length (e.g. "language", "year_suffix" at 10) could
            # otherwise land mid-space and silently lose it on the POST
            # round trip for a reason unrelated to what this test checks.
            raw = f"value_for_{name}"
            values[name] = raw[: field.max_length] if field.max_length else raw
        values["type"] = ItemType.ARTICLE_JOURNAL
        values["categories"] = ["cat-a", "cat-b"]
        values["custom"] = {"foo": "bar"}

        item = ItemFactory(**values)

        def snapshot():
            return {
                field.name: getattr(item, field.name)
                for field in Item._meta.get_fields()
                if hasattr(field, "attname") and not field.primary_key and field.name not in ("created", "modified")
            }

        before = snapshot()

        data = update_page_post_data(client, item)
        response = client.post(reverse("literature:item-update", kwargs={"pk": item.pk}), data)
        assert response.status_code == 302

        item.refresh_from_db()
        assert snapshot() == before

    def test_a_populated_field_outside_the_types_own_groups_is_forced_visible(self, client, db):
        # FR-010 — "legal" is not one of ARTICLE_JOURNAL's own groups
        # (container, numbering), so a value already stored in it has to be
        # forced visible rather than left behind the type guard.
        assert "legal" not in FieldGroups.TYPE_GROUPS[ItemType.ARTICLE_JOURNAL]
        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL, authority="Held Authority")
        response = client.get(reverse("literature:item-update", kwargs={"pk": item.pk}))
        content = response.content.decode()
        assert 'id="id_authority"' in content
        forced_groups = json.loads(response.context["forced_groups_json"])
        assert "legal" in forced_groups

    def test_changing_the_item_type_on_post_retains_values_in_groups_the_new_type_does_not_use(self, client, db):
        # FR-014 — WEBPAGE's own groups are just "container"; "legal" is not
        # among them, so authority must still round-trip unchanged.
        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL, authority="Held Authority")
        data = update_page_post_data(client, item, type=ItemType.WEBPAGE)
        client.post(reverse("literature:item-update", kwargs={"pk": item.pk}), data)
        item.refresh_from_db()
        assert item.type == ItemType.WEBPAGE
        assert item.authority == "Held Authority"

    def test_the_type_select_renders_the_items_stored_type_as_selected(self, client, db):
        # The failure T006's x-init prevents: without it x-model would
        # deselect the stored type at Alpine's own initialisation, but the
        # server-rendered HTML this test reads is unaffected by that bug —
        # this asserts the bound ModelForm renders the right initial option
        # regardless.
        item = ItemFactory(type=ItemType.BOOK)
        content = client.get(reverse("literature:item-update", kwargs={"pk": item.pk})).content.decode()
        assert re.search(rf'<option value="{re.escape(item.type)}"[^>]*selected', content)

    def test_saving_through_the_form_leaves_contributor_date_and_identifier_rows_unchanged(
        self, client, populated_item
    ):
        # FR-012 — ItemForm carries none of these; the guarantee is that a
        # save through it never touches them at all.
        item = populated_item

        def rows():
            return (
                [(row.pk, row.name_id, row.role, row.order) for row in item.item_names.all()],
                [(row.pk, row.date_type, row.begin, row.end) for row in item.item_dates.all()],
                [(row.pk, row.type, row.value) for row in item.item_identifiers.all()],
            )

        before = rows()
        data = update_page_post_data(client, item)
        client.post(reverse("literature:item-update", kwargs={"pk": item.pk}), data)
        assert rows() == before


class TestCreatePageRendersTheTailwindPack:
    """plan.md D-5 — CRISPY_TEMPLATE_PACK = "tailwind" is a setting; this
    asserts what the create page's own markup actually is, not the setting's
    value. A test on the setting alone would pass even if something between
    the setting and the page (a missing app, an overridden template) left a
    different pack's markup on the wire."""

    def test_a_text_input_carries_the_tailwind_packs_label_markup(self, client, db):
        content = client.get(reverse("literature:item-create")).content.decode()
        # crispy_tailwind's field.html wraps every label in this exact,
        # hard-coded class string; the pack this repo carried before D-5
        # (bootstrap4-shaped markup) uses "form-label"/"form-control" instead.
        assert 'class="block text-gray-700 text-sm font-bold mb-2"' in content
        assert "form-label" not in content
        assert "form-control" not in content


class TestItemDetailView:
    """The reference page — FR-019 through FR-026."""

    def test_carried_fields_appear_and_absent_fields_do_not(self, client, db):
        item = ItemFactory(title="Full Record", volume="12", issue="")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        volume_label = item._meta.get_field("volume").verbose_name
        issue_label = item._meta.get_field("issue").verbose_name
        assert f">{volume_label}</h6>" in content
        assert "12" in content
        # issue is blank on this item — its label must not appear at all (FR-021).
        assert f">{issue_label}</h6>" not in content

    def test_carried_fields_match_the_scalar_fields_helper(self, client, db):
        item = ItemFactory(title="Full Record", volume="12", issue="")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        labels = {str(label) for label, _ in response.context["scalar_fields"]}
        assert str(item._meta.get_field("volume").verbose_name) in labels
        assert str(item._meta.get_field("issue").verbose_name) not in labels

    def test_contributors_grouped_by_role_and_in_stored_order(self, client, db):
        item = ItemFactory()
        first_author = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        second_author = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        editor = ItemNameFactory(item=item, role=NameRole.EDITOR)
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        assert (
            content.index(str(first_author.name))
            < content.index(str(second_author.name))
            < content.index(str(editor.name))
        )

    def test_item_type_reads_as_its_label_not_its_stored_slug(self, client, db):
        # The same field on the catalogue badge reads "Journal Article"; the
        # scalar grid used to show the raw CSL slug beside it (RC-003).
        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk})).content.decode()
        assert "Journal Article" in content
        assert "article-journal" not in content

    def test_year_only_date_renders_at_its_own_precision(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="1998")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        assert "1998" in content
        assert "1998-01-01" not in content

    def test_full_date_renders_at_its_own_precision(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="1998-03-14")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        assert "1998-03-14" in response.content.decode()

    def test_range_date_shown_as_a_range(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.EVENT_DATE, begin="2020-01-01", end="2020-01-05")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        assert "2020-01-01" in content
        assert "2020-01-05" in content

    def test_identifiers_show_their_type_including_types_the_store_does_not_recognise(self, client, db):
        item = ItemFactory()
        ItemIdentifierFactory(item=item, type="ARK", value="ark:/12345/x")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        assert "ARK" in content
        assert "ark:/12345/x" in content

    def test_identifier_addressing_a_resolvable_location_is_followable(self, client, db):
        item = ItemFactory()
        ItemIdentifierFactory(item=item, type="URL", value="https://example.org/paper")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        assert 'href="https://example.org/paper"' in response.content.decode()

    def test_identifier_carrying_a_script_scheme_is_never_followable(self, client, db):
        # An unrecognised identifier type skips format validation entirely
        # (FR-017), so the value reaching this page is arbitrary stored text.
        item = ItemFactory()
        payload = "javascript://%0aalert(document.cookie)"
        ItemIdentifierFactory(item=item, type="CUSTOM", value=payload)
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        assert f'href="{payload}"' not in content
        assert 'href="javascript' not in content
        # Still shown in full, just as text rather than as a link.
        assert payload in content

    def test_missing_item_is_a_404(self, client, db):
        response = client.get(reverse("literature:item-detail", kwargs={"pk": 999999}))
        assert response.status_code == 404

    def test_renders_without_contributors_dates_or_identifiers(self, client, db):
        item = ItemFactory()
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        assert response.status_code == 200

    @pytest.mark.parametrize("item_type", ItemType.values)
    def test_renders_for_every_item_type(self, client, db, item_type):
        item = ItemFactory(type=item_type)
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        assert response.status_code == 200

    def test_breadcrumb_links_to_the_catalogue_by_its_resolved_url(self, client, db):
        # The plain MVPDetailView.crud_views mapping is un-namespaced, so
        # reverse('item-list') raises NoReverseMatch under this app's
        # namespaced urls.py — this is the regression the brief's
        # correction exists to prevent (see plan.md, resolve_crud_url).
        item = ItemFactory()
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        catalogue_url = reverse("literature:item-list")
        assert f'href="{catalogue_url}"' in content

    def test_contributor_names_link_to_their_page(self, client, db):
        # FR-022 — the only reachability path into the contributor page
        # (US-4) is a link from here.
        item = ItemFactory()
        item_name = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        contributor_url = reverse("literature:contributor-detail", kwargs={"pk": item_name.name.pk})
        assert f'href="{contributor_url}"' in content

    def test_the_edit_action_renders_and_points_at_the_update_page(self, client, db):
        # DR-001 — directory alone renders nothing without show_update_action
        # (plan.md D-6, D-8). ItemDeleteView is US-3's own task, so no
        # Delete action assertion belongs here yet.
        item = ItemFactory()
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        update_url = reverse("literature:item-update", kwargs={"pk": item.pk})
        assert f'href="{update_url}"' in content

    def test_the_delete_action_renders_and_points_at_the_delete_page(self, client, db):
        # T018 named this assertion; US2 could not write it because turning
        # show_delete_action on before its route existed would have raised
        # NoReverseMatch on every reference page (decisions.md D13).
        # ItemDeleteView and its route are US-3's own task.
        item = ItemFactory()
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        delete_url = reverse("literature:item-delete", kwargs={"pk": item.pk})
        assert f'href="{delete_url}"' in content


class TestReferencePageReadability:
    """Issue #65 — the reference page's share of the same pass."""

    def test_the_breadcrumb_back_to_the_catalogue_reads_the_same_as_the_catalogue(self, client, db):
        item = ItemFactory()
        content = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk})).content.decode()
        catalogue_url = reverse("literature:item-list")
        assert re.search(rf'href="{re.escape(catalogue_url)}"[^>]*>\s*Publications', content)
        assert "Items" not in content

    def test_a_contributor_link_underlines_on_hover(self, client, db):
        item = ItemFactory()
        item_name = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        content = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk})).content.decode()
        contributor_url = reverse("literature:contributor-detail", kwargs={"pk": item_name.name.pk})
        assert "link-hover" in anchor_tag(content, contributor_url)

    def test_a_role_heading_pluralises_with_the_names_under_it(self, client, db):
        item = ItemFactory()
        for _ in range(2):
            ItemNameFactory(item=item, role=NameRole.EDITOR)
        content = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk})).content.decode()
        assert ">Editors</h6>" in content

    def test_a_role_heading_stays_singular_for_one_name(self, client, db):
        item = ItemFactory()
        ItemNameFactory(item=item, role=NameRole.EDITOR)
        content = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk})).content.decode()
        assert ">Editor</h6>" in content


class TestItemDeleteView:
    """Remove a reference that does not belong — US-3 (FR-017 through FR-020)."""

    def test_get_renders_a_confirmation_naming_the_reference_and_deletes_nothing(self, client, db):
        item = ItemFactory(title="A Reference Marked For Removal")
        response = client.get(reverse("literature:item-delete", kwargs={"pk": item.pk}))
        assert response.status_code == 200
        assert "A Reference Marked For Removal" in response.content.decode()
        assert Item.objects.filter(pk=item.pk).exists()

    def test_declining_returns_to_the_references_own_page_and_the_item_still_exists(self, client, db):
        # FR-018, US-3 scenario 2 — MVPDeleteView.get_back_url() falls back to
        # the catalogue list, and the detail page's own delete link carries no
        # ?back (only the update page's does), so declining would otherwise
        # strand the reader on the catalogue instead of the reference they
        # chose not to remove (plan.md D-7).
        item = ItemFactory()
        response = client.get(reverse("literature:item-delete", kwargs={"pk": item.pk}))
        detail_url = reverse("literature:item-detail", kwargs={"pk": item.pk})
        assert response.context["back_url"] == detail_url
        assert f'href="{detail_url}"' in response.content.decode()
        assert Item.objects.filter(pk=item.pk).exists()

    def test_an_inherited_back_parameter_is_honoured_ahead_of_the_reference_page(self, client, db):
        # get_back_url() honours a validated ?back first (D-7) — only once
        # that is absent does it fall through to the reference's own page.
        item = ItemFactory()
        response = client.get(reverse("literature:item-delete", kwargs={"pk": item.pk}), {"back": "/catalogue/"})
        assert response.context["back_url"] == "/catalogue/"

    def test_post_removes_the_item_with_its_names_dates_and_identifiers_and_redirects_to_the_catalogue(
        self, client, populated_item
    ):
        item = populated_item
        item_name_pk = item.item_names.get().pk
        item_date_pk = item.item_dates.get().pk
        item_identifier_pk = item.item_identifiers.get().pk

        response = client.post(reverse("literature:item-delete", kwargs={"pk": item.pk}))

        assert response.status_code == 302
        assert response.url == reverse("literature:item-list")
        assert not Item.objects.filter(pk=item.pk).exists()
        assert not ItemName.objects.filter(pk=item_name_pk).exists()
        assert not ItemDate.objects.filter(pk=item_date_pk).exists()
        assert not ItemIdentifier.objects.filter(pk=item_identifier_pk).exists()

    def test_names_survive_deletion_whether_or_not_credited_elsewhere(self, client, db):
        # FR-020 — nothing points from Item to Name directly, only ItemName
        # rows cascade, so this is already true of the model; the test
        # asserts the guarantee rather than any code that implements it
        # (plan.md D-7). Covers both a contributor still credited elsewhere
        # and one left credited on nothing, whose own page still has to
        # render (FR-037/FR-038 rely on the Name row itself surviving).
        item = ItemFactory()
        other_item = ItemFactory()
        shared_contributor = NameFactory()
        solo_contributor = NameFactory()
        ItemNameFactory(item=item, name=shared_contributor, role=NameRole.AUTHOR)
        ItemNameFactory(item=other_item, name=shared_contributor, role=NameRole.EDITOR)
        ItemNameFactory(item=item, name=solo_contributor, role=NameRole.AUTHOR)

        client.post(reverse("literature:item-delete", kwargs={"pk": item.pk}))

        assert Name.objects.filter(pk=shared_contributor.pk).exists()
        assert Name.objects.filter(pk=solo_contributor.pk).exists()

        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": solo_contributor.pk}))
        assert response.status_code == 200
        assert "Not credited on anything yet" in response.content.decode()

    def test_removing_the_last_reference_leaves_the_catalogue_rendering_its_empty_state(self, client, db):
        item = ItemFactory()
        client.post(reverse("literature:item-delete", kwargs={"pk": item.pk}))
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "Nothing in the catalogue yet" in content

    def test_unknown_pk_is_a_404(self, client, db):
        response = client.get(reverse("literature:item-delete", kwargs={"pk": 999999}))
        assert response.status_code == 404


class TestContributorDetailView:
    """The contributor page — FR-032 through FR-038."""

    def test_renders_neither_a_search_box_nor_a_filter_button(self, client, db):
        # FR-025, plan.md D-6 — ItemListView's own base class change (T022)
        # would otherwise hand this page a search box and four filters,
        # since it used to subclass ItemListView directly.
        contributor = NameFactory()
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'name="q"' not in content
        assert "filterModal" not in content

    def test_credits_listed_with_roles(self, client, db):
        contributor = NameFactory()
        item = ItemFactory(title="Credited Work")
        ItemNameFactory(item=item, name=contributor, role=NameRole.EDITOR)
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        content = response.content.decode()
        assert "Credited Work" in content
        assert str(NameRole.EDITOR.label) in content

    def test_credit_row_carries_what_a_catalogue_row_carries(self, client, db):
        # FR-034 defers to FR-013 for a credit row's content, so the row shows
        # the item's own contributors as well as the role this contributor
        # held on it — the roles are additional, not a replacement.
        contributor = NameFactory(family="Rowe", given="A")
        coauthor = NameFactory(family="Peralta", given="B")
        item = ItemFactory(title="Jointly Written Work", citation_key="rowe2021joint")
        ItemNameFactory(item=item, name=contributor, role=NameRole.EDITOR)
        ItemNameFactory(item=item, name=coauthor, role=NameRole.AUTHOR)
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2021")

        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        content = response.content.decode()

        assert "Jointly Written Work" in content
        assert str(coauthor) in content
        assert str(NameRole.AUTHOR.label) in content
        assert "rowe2021joint" in content
        assert "2021" in content
        assert str(item.get_type_display()) in content

    def test_the_credit_row_states_the_roles_as_this_contributors_own(self, client, db):
        # FR-035. The row's inherited contributor line already prints every
        # role anyone held on the item, so asserting a role label alone passes
        # even with this contributor's own credit line deleted. Assert the
        # line that attributes those roles to the contributor whose page it is.
        contributor = NameFactory()
        item = ItemFactory()
        ItemNameFactory(item=item, name=contributor, role=NameRole.EDITOR)
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        assert "Credited as" in response.content.decode()

    def test_breadcrumb_links_to_the_catalogue_by_its_resolved_url(self, client, db):
        # The model-derived crud_views entry would be 'name-list', a route
        # this app does not have.
        contributor = NameFactory()
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        assert f'href="{reverse("literature:item-list")}"' in response.content.decode()

    def test_breadcrumb_to_the_catalogue_reads_as_the_catalogue_page_is_titled(self, client, db):
        # Issue #65. This breadcrumb builds its own text rather than inheriting
        # the list view's, so a heading changed in one place and not the other
        # would have the same link read two ways in one journey.
        contributor = NameFactory()
        content = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})).content.decode()
        assert re.search(rf'href="{re.escape(reverse("literature:item-list"))}"[^>]*>\s*Publications', content)

    def test_item_held_under_two_roles_appears_once_carrying_both(self, client, db):
        contributor = NameFactory()
        item = ItemFactory(title="Dual Role Work")
        ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=contributor, role=NameRole.EDITOR)
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        content = response.content.decode()
        assert content.count("Dual Role Work") == 1
        assert str(NameRole.AUTHOR.label) in content
        assert str(NameRole.EDITOR.label) in content

    def test_list_paginates_in_the_catalogues_order(self, client, db):
        contributor = NameFactory()
        older = ItemFactory(title="Older Credit")
        newer = ItemFactory(title="Newer Credit")
        ItemNameFactory(item=older, name=contributor, role=NameRole.AUTHOR)
        ItemNameFactory(item=newer, name=contributor, role=NameRole.AUTHOR)
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        content = response.content.decode()
        assert content.index("Newer Credit") < content.index("Older Credit")

    def test_page_holds_no_more_than_paginate_by_items_whatever_the_credit_count(self, client, db):
        contributor = NameFactory()
        for _ in range(30):
            item = ItemFactory()
            ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        assert len(response.context["page_obj"]) == 24

    def test_page_number_past_the_end_is_a_404(self, client, db):
        contributor = NameFactory()
        item = ItemFactory()
        ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}),
            {"page": 999},
        )
        assert response.status_code == 404

    def test_institutional_name_renders_unsplit(self, client, db):
        contributor = NameFactory(family="", given="", literal="Some Research Institute")
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        assert response.status_code == 200
        assert "Some Research Institute" in response.content.decode()

    def test_contributor_with_no_credits_renders_the_stated_empty_result(self, client, db):
        contributor = NameFactory()
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        assert response.status_code == 200
        content = response.content.decode()
        assert "Not credited on anything yet" in content
        assert "This contributor has no credited references in the catalogue." in content

    def test_missing_contributor_is_a_404(self, client, db):
        response = client.get(reverse("literature:contributor-detail", kwargs={"pk": 999999}))
        assert response.status_code == 404

    def test_two_records_with_identical_names_keep_separate_pages(self, client, db):
        first = NameFactory(family="Smith", given="J")
        second = NameFactory(family="Smith", given="J")
        first_item = ItemFactory(title="First Smiths Work")
        second_item = ItemFactory(title="Second Smiths Work")
        ItemNameFactory(item=first_item, name=first, role=NameRole.AUTHOR)
        ItemNameFactory(item=second_item, name=second, role=NameRole.AUTHOR)

        first_response = client.get(reverse("literature:contributor-detail", kwargs={"pk": first.pk}))
        first_content = first_response.content.decode()
        assert "First Smiths Work" in first_content
        assert "Second Smiths Work" not in first_content

        second_response = client.get(reverse("literature:contributor-detail", kwargs={"pk": second.pk}))
        second_content = second_response.content.decode()
        assert "Second Smiths Work" in second_content
        assert "First Smiths Work" not in second_content

    def test_query_count_does_not_grow_with_credit_count(self, client, db):
        contributor = NameFactory()

        def add_credits(n):
            for _ in range(n):
                item = ItemFactory()
                ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
                ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2021")

        add_credits(3)
        with CaptureQueriesContext(connection) as small_credit_list:
            response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        assert response.status_code == 200

        add_credits(15)
        with CaptureQueriesContext(connection) as large_credit_list:
            response = client.get(reverse("literature:contributor-detail", kwargs={"pk": contributor.pk}))
        assert response.status_code == 200

        assert len(large_credit_list.captured_queries) == len(small_credit_list.captured_queries)


class TestCSLRoundTrip:
    """SC-006 — a reference entered by hand reaches the same CSL round-trip
    fidelity standard as an imported one (Article IX). No new mechanism:
    this exercises the create view (US-1) and the converters
    (tests/test_converters.py's own subject) together, which nothing else
    covers."""

    def test_an_item_entered_through_the_create_view_round_trips_through_csl_json(self, client, db):
        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="HandEntered2024",
            title="A Representative Reference",
            container_title="Journal of Testing",
            volume="12",
            issue="3",
            page="100-110",
            abstract="An abstract with representative content.",
            language="en",
        )
        client.post(reverse("literature:item-create"), data)
        original = Item.objects.get(citation_key="HandEntered2024")

        original_csl = to_csl_json(original)
        round_tripped = from_csl_json(original_csl)
        round_tripped_csl = to_csl_json(round_tripped)

        # Every CSL key round-trips unchanged, "id" (citation_key) included: the original is
        # still in the store and its key is stored again as given, not rewritten (ADR 0023).
        assert round_tripped_csl == original_csl


class AlpineScopeParser(HTMLParser):
    """Capture the parsed ``x-init`` that seeds the form's Alpine scope.

    Parsed, not grepped. The page carrying a substring proves nothing about
    what a browser receives: a raw double quote inside a double-quoted
    attribute closes it, so the JSON that follows becomes a run of junk
    attribute names while every substring a test might look for is still
    present in the body.
    """

    def __init__(self):
        super().__init__()
        self.attr_count: int | None = None
        self.x_init: str | None = None

    def handle_starttag(self, tag, attrs):
        as_dict = dict(attrs)
        if tag == "div" and "typeGroups" in (as_dict.get("x-init") or ""):
            self.attr_count = len(attrs)
            self.x_init = as_dict["x-init"]


def alpine_scope(body):
    parser = AlpineScopeParser()
    parser.feed(body)
    return parser


class TestTheFormsAlpineScopeSurvivesTheHtmlParser:
    """The type scoping is inert unless the browser can read its own seed data.

    Every other test of this page asserts on the response body as text, and a
    malformed attribute leaves that text unchanged — which is how the page
    shipped for four stories with its scoping expression truncated at the
    first brace and every group permanently visible.
    """

    def test_the_create_pages_scope_element_carries_exactly_one_attribute(self, client, db):
        parser = alpine_scope(client.get(reverse("literature:item-create")).content.decode())
        assert parser.attr_count == 1, "the scope element gained attributes, which means the JSON broke out of x-init"

    def test_the_create_pages_type_map_parses_and_covers_every_item_type(self, client, db):
        parser = alpine_scope(client.get(reverse("literature:item-create")).content.decode())
        assigned = parser.x_init.split("form.typeGroups = ", 1)[1].rsplit(";", 1)[0]
        assert json.loads(assigned).keys() == {t.value for t in ItemType}

    def test_the_edit_pages_forced_groups_parse(self, client, db):
        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL, scale="1:50000")
        parser = alpine_scope(client.get(reverse("literature:item-update", kwargs={"pk": item.pk})).content.decode())
        assert parser.attr_count == 1
        assigned = parser.x_init.split("form.forcedGroups = ", 1)[1].strip()
        assert "physical" in json.loads(assigned), "a populated off-type group must reach the browser as forced-visible"


class TestSurroundingWhitespaceSurvivesACorrection:
    """SC-003 promises a save that changes nothing leaves the record identical.

    Django's ``CharField`` strips by default, and the CSL JSON import path
    does not, so a stored value with edges is reachable and would come back
    trimmed by a save the reader did not think changed anything.
    """

    def test_a_trailing_newline_and_padding_survive_an_unchanged_save(self, client, db):
        item = ItemFactory(
            type=ItemType.BOOK,
            title="  Padded Title  ",
            abstract="Line one\n\nLine two\n",
        )
        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item.pk}),
            update_page_post_data(client, item),
        )
        assert response.status_code == 302
        item.refresh_from_db()
        assert item.title == "  Padded Title  "
        assert item.abstract == "Line one\n\nLine two\n"

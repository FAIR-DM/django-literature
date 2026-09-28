"""Tests for ``literature/ui/views.py``."""

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import pytest
from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
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
from literature.ui.staging import StagedUpload
from tests.factories import (
    ItemDateFactory,
    ItemFactory,
    ItemIdentifierFactory,
    ItemNameFactory,
    NameFactory,
)

#: Real, single-entry fixtures rather than hand-rolled minimal ones — one
#: DOI-bearing article, shared by the BibTeX and RIS upload scenarios below.
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

#: A minimal, valid RIS entry. Not ``tests/data/publication.ris``, whose ``Y2``
#: tag ("1/26/2023") trips a date-parsing defect in ``literature.importers.ris``.
RIS_ONE_GOOD_ENTRY = """TY  - JOUR
AU  - Doe, Jane
TI  - A Working RIS Reference
PY  - 2020
JO  - Journal of Testing
ER  -
"""

#: A RIS file mixing an entry that converts with one the format's contract
#: refuses: the second record's missing ``TY`` tag is ``RISFormat``'s own
#: documented ``EntryError``, not an incidental malformation.
RIS_ONE_GOOD_ONE_BAD = """TY  - JOUR
AU  - Doe, Jane
TI  - A Working RIS Reference
PY  - 2020
JO  - Journal of Testing
ER  -

AU  - Roe, Jan
T1  - A Record With No Reference Type
ER  -
"""


def table_header_row(content):
    """Return the table's ``<thead>`` markup.

    The filter modal renders ahead of the table and repeats some column names as field labels.
    """
    match = re.search(r"<thead.*?</thead>", content, re.DOTALL)
    assert match, "no table header row"
    return match.group(0)


def rendered_page_link(content, page_number):
    """Return the unescaped ``href`` of the rendered link to ``page_number``.

    Read from the markup, so the test follows the address a reader's click carries. Unescaped
    because ``{% querystring %}`` writes ``&amp;page=2``, which the test client would read as a
    parameter named ``amp;page``.
    """
    match = re.search(rf'<a\b[^>]*href="([^"]*)"[^>]*>\s*{page_number}\s*</a>', content)
    assert match, f"no rendered link to page {page_number}"
    return html.unescape(match.group(1))


def rendered_sort_link(content, column_label):
    """Return the unescaped ``href`` of a column heading's rendered sort link."""
    match = re.search(
        rf'<a\b[^>]*href="([^"]*)"[^>]*>\s*{re.escape(column_label)}\s*<', content
    )
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
    posts ``default_next=list``, the rendered page actually
    posts.

    Also carries every inline row-set's own management form and each of its
    rows' current field values — a Django formset raises on a
    POST missing its management form entirely, and a POST that resubmits an
    existing row's fields blank would either fail that row's own validation
    or blank the row, neither of which is "no change" for a test that never
    meant to touch the contributor, date or identifier sets at all.
    """
    response = client.get(url)
    form = response.context["form"]
    data = {name: (form[name].value() or "") for name in form.fields}
    for inline in response.context.get("inlines", []):
        management_form = inline.management_form
        for name in management_form.fields:
            data[management_form[name].html_name] = management_form[name].value()
        for row_form in inline.forms:
            for name in row_form.fields:
                data[row_form[name].html_name] = row_form[name].value() or ""
    content = response.content.decode()
    submit_button = re.search(
        r'<button[^>]*type="submit"[^>]*name="([^"]+)"[^>]*value="([^"]+)"', content
    )
    if submit_button:
        data[submit_button.group(1)] = submit_button.group(2)
    data.update(overrides)
    return data


def rendered_filter_form_data(response, **overrides):
    """Build a GET query dict from a rendered page's own filter form.

    Starts from what the bound form carries, hidden fields included, so it submits exactly what
    the filter modal would.
    """
    form = response.context["filter"].form
    data = {name: (form[name].value() or "") for name in form.fields}
    data.update(overrides)
    return data


def update_page_post_data(client, item, **overrides):
    """Build a POST body from the rendered edit page's own bound form."""
    return rendered_form_post_data(
        client, reverse("literature:item-update", kwargs={"pk": item.pk}), **overrides
    )


def create_page_post_data(client, **overrides):
    """Build a POST body from the rendered create page's own form."""
    return rendered_form_post_data(
        client, reverse("literature:item-create"), **overrides
    )


#: Both catalogue presentations, so a "both presentations owe this" test
#: is one parametrized method rather than two near-identical
#: ones. ``literature:item-list`` is the table; the card is
#: reachable at the test urlconf's own second route.
CATALOGUE_ROUTES = ["literature:item-list", "item-list-cards"]


class TestItemListView:
    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_lists_items_most_recently_added_first(self, client, db, route_name):
        older = ItemFactory(title="Older Reference")
        newer = ItemFactory(title="Newer Reference")
        response = client.get(reverse(route_name))
        content = response.content.decode()
        assert content.index("Newer Reference") < content.index("Older Reference")

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_page_holds_no_more_than_paginate_by_items_whatever_the_catalogue_size(
        self, client, db, route_name
    ):
        ItemFactory.create_batch(30)
        response = client.get(reverse(route_name))
        if route_name == "literature:item-list":
            # The table route's own page: at 0.19.1
            # MVPTableViewMixin.paginate_queryset() leaves the queryset
            # whole and republishes the page from the table, so
            # object_list there is the whole catalogue, not one page of it.
            assert len(response.context["table"].page.object_list) == 24
        else:
            assert len(response.context["object_list"]) == 24

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_pagination_states_position_and_offers_navigation(
        self, client, db, route_name
    ):
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
    def test_each_row_links_to_that_items_page(self, client, db, route_name):
        item = ItemFactory(title="A Linked Reference")
        response = client.get(reverse(route_name))
        content = response.content.decode()
        assert reverse("literature:item-detail", kwargs={"pk": item.pk}) in content

    @pytest.mark.parametrize("route_name", CATALOGUE_ROUTES)
    def test_the_add_link_renders_and_points_at_the_create_page(
        self, client, db, route_name
    ):
        # directory = ["create"] alone renders nothing without
        # show_create_action set.
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
        # A range's precision is both ends — the row used to drop everything after ``begin`` while the
        # reference page rendered the same date correctly.
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2019", end="2021")
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "2019" in content
        assert "2021" in content

    def test_row_falls_back_to_a_free_text_date(self, client, db):
        item = ItemFactory()
        ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin=None, literal="in press"
        )
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

        assert len(large_catalogue.captured_queries) == len(
            small_catalogue.captured_queries
        )


class TestCatalogueListReadability:
    def test_the_model_keeps_its_own_name(self, db):
        # The heading is the view's to choose. Renaming the model to reach it
        # would rename it in the admin, in every error message and in the
        # migration state, for a word on one page.
        assert str(Item._meta.verbose_name_plural) == "items"

    def test_contributor_names_link_to_their_page(self, client, db):
        # The reference page carries this link; the row once showed
        # the same names as plain text, so a reader could not tell from the
        # catalogue that a contributor had a page at all.
        item_name = ItemNameFactory(role=NameRole.AUTHOR)
        content = client.get(reverse("item-list-cards")).content.decode()
        contributor_url = reverse(
            "literature:contributor-detail", kwargs={"pk": item_name.name.pk}
        )
        assert f'href="{contributor_url}"' in content

    def test_a_row_shows_a_snippet_of_the_abstract(self, client, db):
        ItemFactory(abstract="Sediment cores record the drainage history of the basin.")
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "Sediment cores record the drainage history of the basin." in content

    def test_a_long_abstract_is_cut_to_a_snippet(self, client, db):
        ItemFactory(abstract=" ".join(f"word{n}" for n in range(60)))
        content = client.get(reverse("item-list-cards")).content.decode()
        assert "word0" in content
        assert "word59" not in content

    def test_a_row_carrying_no_abstract_leaves_no_empty_paragraph_behind(
        self, client, db
    ):
        # The snippet is a paragraph; rendered unconditionally it would leave an
        # empty one on every row of a catalogue imported without abstracts,
        # which is most of them.
        item = ItemFactory(abstract="")
        content = client.get(reverse("item-list-cards")).content.decode()
        assert re.search(r"<p[^>]*>\s*</p>", content) is None
        assert item.citation_key in content


class TestTheCardListStaysAvailable:
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

    def test_routing_a_url_at_it_keeps_pagination_and_the_create_action(
        self, client, db
    ):
        # Empty state first — populating the catalogue would hide it.
        empty_content = client.get(reverse("item-list-cards")).content.decode()
        assert f'href="{reverse("literature:item-create")}"' in empty_content

        ItemFactory.create_batch(30)
        populated_content = client.get(reverse("item-list-cards")).content.decode()
        assert "1-24 of 30" in populated_content
        assert 'href="?page=2"' in populated_content

    def test_the_contributor_page_still_presents_cards(self, client, db):
        contributor = NameFactory()
        item = ItemFactory(title="A Contributor Page Reference")
        ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
        content = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        ).content.decode()
        assert "<table" not in content
        assert "A Contributor Page Reference" in content

    def test_no_template_is_copied_out_of_the_package_to_render_the_cards(self):
        # Every template the card chain reaches for resolves inside the
        # literature package itself, so a project routing at ItemListView
        # needs to write nothing of its own to get the card list.
        package_root = Path(literature.__file__).resolve().parent
        for template_name in (
            "literature/ui/item_list_item.html",
            "literature/ui/contributor_item.html",
        ):
            origin = Path(get_template(template_name).origin.name).resolve()
            assert package_root in origin.parents, (
                f"{template_name} resolved outside the package at {origin}"
            )


class TestTheCardListFiltersAndSearches:
    def test_a_search_term_narrows_the_card_list(self, client, db):
        matching = ItemFactory(title="Whale Migration Patterns")
        other = ItemFactory(title="Unrelated Reference")
        content = client.get(
            reverse("item-list-cards"), {"q": "whale"}
        ).content.decode()
        assert matching.title in content
        assert other.title not in content

    def test_a_filter_narrows_the_card_list(self, client, db):
        book = ItemFactory(type=ItemType.BOOK)
        article = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = client.get(
            reverse("item-list-cards"), {"type": ItemType.BOOK}
        ).content.decode()
        assert book.citation_key in content
        assert article.citation_key not in content

    def test_a_sort_with_no_filter_in_force_shows_no_applied_filter_badge(
        self, client, db
    ):
        # MVPFilteredListView's own
        # get_context_data() (mvp/integrations/django_filters/views.py)
        # counts every non-empty field of filterset.form.cleaned_data, and
        # "sort" (literature/ui/filters.py ItemFilterSet.sort) is a hidden
        # field on that form carrying django-tables2's own ordering — not one of the catalogue's own filters.
        # Proven through the shared exclusion function, not a second copy of
        # the table's own override.
        ItemFactory()
        response = client.get(reverse("item-list-cards"), {"sort": "-citation_key"})
        assert not response.context.get("applied_filters")
        content = response.content.decode()
        assert "indicator-item badge badge-secondary badge-xs" not in content


def catalogue_pks(route_name, params):
    """Return the primary keys a request against ``route_name`` narrows to."""
    response = Client().get(reverse(route_name), params)
    if route_name == "literature:item-list":
        return {row.record.pk for row in response.context["table"].page.object_list}
    return {obj.pk for obj in response.context["object_list"]}


class TestBothPresentationsReturnTheSameReferences:
    @pytest.fixture
    def catalogue(self, db):
        matching = ItemFactory(
            title="Whale Migration Patterns", type=ItemType.BOOK, language="en"
        )
        ItemDateFactory(item=matching, date_type=DateType.ISSUED, begin="2020")
        ItemNameFactory(item=matching, name=NameFactory(family="Darwin"))
        other = ItemFactory(
            title="Unrelated Reference", type=ItemType.ARTICLE_JOURNAL, language="fr"
        )
        ItemDateFactory(item=other, date_type=DateType.ISSUED, begin="2021")
        return matching, other

    @pytest.mark.parametrize(
        "params",
        [
            {"q": "whale"},
            {"type": ItemType.BOOK},
            {"contributor": "darwin"},
            {"language": "en"},
            {"issued_year": 2020},
            {"q": "whale", "type": ItemType.BOOK},
        ],
        ids=[
            "search",
            "type",
            "contributor",
            "language",
            "issued_year",
            "search-and-filter",
        ],
    )
    def test_the_two_routes_narrow_to_the_same_references(self, catalogue, params):
        matching, _other = catalogue
        table_pks = catalogue_pks("literature:item-list", params)
        card_pks = catalogue_pks("item-list-cards", params)
        assert table_pks == card_pks == {matching.pk}


class TestItemTableView:
    def test_column_headers_appear_in_the_required_order(self, client, db):
        # Reads the table's own header row, not the whole
        # rendered page — the filter modal renders ahead of the table and emits "Type" as a literal
        # filter-field label before the table's own "Type" column header, so
        # a page-wide substring search stopped being a faithful proxy for
        # "the table's columns sit in this order".
        content = client.get(reverse("literature:item-list")).content.decode()
        header_row = table_header_row(content)
        headers = [
            "Citation key",
            "Type",
            "Title",
            "Container title",
            "Authors",
            "Issued",
        ]
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
        ItemNameFactory(
            item=item, name=NameFactory(family=payload, given=""), role=NameRole.AUTHOR
        )

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
        assert str(ItemType.ARTICLE_JOURNAL.label) in content
        assert "A Complete Reference" in content
        assert "Journal of Everything" in content
        assert str(item_name.name) in content
        assert "2020" in content

    def test_paging_to_the_next_page_renders_the_next_rows_under_the_same_headings(
        self, client, db
    ):
        ItemFactory.create_batch(30)
        response = client.get(reverse("literature:item-list"), {"page": 2})
        content = response.content.decode()
        assert response.status_code == 200
        assert "Citation key" in content
        # The table's own page — see the sibling
        # assertion above for why object_list no longer means this here.
        assert len(response.context["table"].page.object_list) == 6

    def test_query_count_does_not_grow_with_row_count(self, client, db):
        # Proves the view's prefetches are actually being read, rather
        # than the manager: the credited-names cell filtering
        # record.item_names.filter(...) would cost one query per row.
        #
        # Extended, not duplicated: every item's
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

        assert len(large_catalogue.captured_queries) == len(
            small_catalogue.captured_queries
        )

        with CaptureQueriesContext(connection) as small_search:
            response = client.get(reverse("literature:item-list"), {"q": "whale"})
        assert response.status_code == 200

        add_items(15)
        with CaptureQueriesContext(connection) as large_search:
            response = client.get(reverse("literature:item-list"), {"q": "whale"})
        assert response.status_code == 200

        assert len(large_search.captured_queries) == len(small_search.captured_queries)

    def test_the_edit_control_renders_and_points_at_each_rows_own_update_page(
        self, client, db
    ):
        item = ItemFactory()
        content = client.get(reverse("literature:item-list")).content.decode()
        update_url = reverse("literature:item-update", kwargs={"pk": item.pk})
        assert f'href="{update_url}"' in content

    def test_the_edit_control_follows_show_update_action_like_the_reference_pages_own(
        self, client, db, monkeypatch
    ):
        # The same CRUDDirectoryMixin flag ItemDetailView's own edit
        # action reads (literature/ui/views.py), overridden here the same way
        # a project would override it to gate the write page.
        from literature.ui.views import ItemTableView

        monkeypatch.setattr(ItemTableView, "show_update_action", False)
        item = ItemFactory()
        content = client.get(reverse("literature:item-list")).content.decode()
        update_url = reverse("literature:item-update", kwargs={"pk": item.pk})
        assert f'href="{update_url}"' not in content

    def test_the_control_and_its_target_are_reachable_with_no_authentication(
        self, client, db
    ):
        # This feature introduces no permission check, login
        # requirement or other access control of its own. ``client`` here is
        # the plain, unauthenticated test client every other assertion in
        # this module already uses; both pages 200 for it.
        item = ItemFactory()
        assert client.get(reverse("literature:item-list")).status_code == 200
        assert (
            client.get(
                reverse("literature:item-update", kwargs={"pk": item.pk})
            ).status_code
            == 200
        )

    def test_carries_search_and_filter_but_no_column_chooser(self, client, db):
        # FS-010 turned search and filter back on after FS-009 locked them off.
        # Asserted against the rendered page and closed in both directions, so
        # an upstream default widening the action surface is still caught.
        ItemFactory()
        response = client.get(reverse("literature:item-list"))
        content = response.content.decode()
        assert response.context["table_actions"] == [
            "search",
            "filter",
            "create",
            "import",
        ]
        assert 'name="q"' in content  # the search box's own input name
        assert "filterModal" in content  # the filter control's own modal id
        # No column-chooser ships in either django-tables2 or django-mvp
        # today — nothing here builds one, and the closed actions list above
        # is what would carry it if a future default introduced one.

    def test_the_toolbar_renders_the_views_own_list_and_not_the_packaged_default(
        self, client, db, monkeypatch
    ):
        # The gate on the seam itself. django-mvp 0.19.2 deleted
        # ``MVPTableViewMixin.actions`` and the ``table_actions`` context key
        # its ``table_view.html`` rendered the row from (upstream commit
        # dfa7c3a), and the packaged template now renders
        # ``<c-page.list.actions />`` bare, so the component's own c-vars
        # default wins and nothing a view declares reaches the page. That
        # removal blanked "import" off the catalogue toolbar without a single
        # test going red on the mechanism — the three tests that did fail all
        # assert an outcome, so any of them could be satisfied by a different
        # route while the view's list stayed unread.
        #
        # This asserts the connection instead: a list set on the view and
        # nothing else decides what renders. Set to "import" alone, the
        # packaged default's search box and filter modal must be absent —
        # under the default they are both present whatever the view says,
        # which is exactly the red this reinstates.
        from literature.ui.views import ItemTableView

        monkeypatch.setattr(ItemTableView, "table_actions", ["import"])
        ItemFactory()
        content = client.get(reverse("literature:item-list")).content.decode()
        assert f'href="{reverse("literature:item-import")}"' in content
        assert 'name="q"' not in content  # the search box's own input name
        assert "filterModal" not in content  # the filter control's own modal id

    def test_the_search_box_submits_through_the_filter_form(self, client, db):
        # The search input renders with `form="filterForm"`,
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

    def test_the_queryset_annotates_issued_matching_the_items_own_issued_date(
        self, client, db
    ):
        # The issued sort reads this Subquery annotation. A join-based filter is deliberately not used, since
        # it risks row multiplication and interferes with the paginator's
        # count query.
        #
        # The annotation is a raw column value, typed
        # DateTimeField so issued__year resolves, and its seconds
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
        issued_date = ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin="2020-05-01"
        )
        issued_date.refresh_from_db()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2021-01-01")
        response = client.get(reverse("literature:item-list"))
        (annotated_item,) = [
            row for row in response.context["object_list"] if row.pk == item.pk
        ]
        assert annotated_item.issued.date() == issued_date.begin.date

    def test_the_issued_annotation_is_none_for_a_reference_with_no_issued_date(
        self, client, db
    ):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2021-01-01")
        response = client.get(reverse("literature:item-list"))
        (annotated_item,) = [
            row for row in response.context["object_list"] if row.pk == item.pk
        ]
        assert annotated_item.issued is None


class TestCatalogueImportAction:
    def test_the_table_catalogue_carries_a_link_to_the_import_route(self, client, db):
        content = client.get(reverse("literature:item-list")).content.decode()
        assert f'href="{reverse("literature:item-import")}"' in content

    def test_the_card_catalogue_carries_the_same_link(self, client, db):
        content = client.get(reverse("item-list-cards")).content.decode()
        assert f'href="{reverse("literature:item-import")}"' in content

    def test_the_contributor_page_carries_no_import_link(self, client, db):
        contributor = NameFactory()
        content = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        ).content.decode()
        assert f'href="{reverse("literature:item-import")}"' not in content

    def test_the_table_catalogue_still_renders_search_filter_and_create(
        self, client, db
    ):
        content = client.get(reverse("literature:item-list")).content.decode()
        assert 'name="q"' in content
        assert "filterModal" in content
        assert f'href="{reverse("literature:item-create")}"' in content

    def test_the_card_catalogue_still_renders_search_filter_and_create(
        self, client, db
    ):
        content = client.get(reverse("item-list-cards")).content.decode()
        assert 'name="q"' in content
        assert "filterModal" in content
        assert f'href="{reverse("literature:item-create")}"' in content


class TestCatalogueSearch:
    @pytest.mark.parametrize(
        "field",
        ["citation_key", "title", "title_short", "original_title", "container_title"],
    )
    def test_matches_a_term_in_each_scalar_field(self, client, db, field):
        matching = ItemFactory(**{field: "Whale Migration Patterns"})
        other = ItemFactory()
        content = client.get(
            reverse("literature:item-list"), {"q": "whale"}
        ).content.decode()
        assert matching.citation_key in content
        assert other.citation_key not in content

    def test_matches_a_contributors_family_name(self, client, db):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(family="Darwin"))
        other = ItemFactory()
        content = client.get(
            reverse("literature:item-list"), {"q": "darwin"}
        ).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_matches_a_contributors_given_name(self, client, db):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(given="Charles"))
        other = ItemFactory()
        content = client.get(
            reverse("literature:item-list"), {"q": "charles"}
        ).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_matches_an_organizational_literal_name(self, client, db):
        item = ItemFactory()
        ItemNameFactory(
            item=item,
            name=NameFactory(family="", given="", literal="Smithsonian Institution"),
        )
        other = ItemFactory()
        content = client.get(
            reverse("literature:item-list"), {"q": "smithsonian"}
        ).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_matching_is_case_insensitive(self, client, db):
        item = ItemFactory(title="Whale Migration Patterns")
        other = ItemFactory()
        content = client.get(
            reverse("literature:item-list"), {"q": "WHALE"}
        ).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_a_fragment_living_only_in_the_abstract_or_a_keyword_finds_nothing(
        self, client, db
    ):
        # Neither field is in SEARCH_FIELDS (tests/test_ui/test_filters.py
        # ::TestSearchFields already pins the declared list itself).
        ItemFactory(abstract="Discusses whale migration patterns at length.")
        ItemFactory(keyword="whale, migration")
        response = client.get(reverse("literature:item-list"), {"q": "whale"})
        assert len(response.context["table"].page.object_list) == 0

    def test_a_reference_matching_several_fields_appears_once(self, client, db):
        # The shared fragment sits in three different
        # searched paths (title, container_title, a contributor's family
        # name) at once, over a distinct row so no other match can hide a
        # duplicate.
        item = ItemFactory(title="Zzyxq Behavior", container_title="The Zzyxq Journal")
        ItemNameFactory(item=item, name=NameFactory(family="Zzyxqson"))
        response = client.get(reverse("literature:item-list"), {"q": "zzyxq"})
        matches = [
            row
            for row in response.context["table"].page.object_list
            if row.record.pk == item.pk
        ]
        assert len(matches) == 1

    def test_a_one_character_fragment_matches_literally(self, client, db):
        item = ItemFactory(title="Zebra Migration")
        other = ItemFactory(title="Unrelated Reference")
        content = client.get(
            reverse("literature:item-list"), {"q": "Z"}
        ).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_a_term_of_only_spaces_is_a_no_op(self, client, db):
        # The upstream mixin strips and checks truthiness before
        # filtering at all, so this is the empty-query no-op under
        # a different guise rather than a wildcard match.
        ItemFactory.create_batch(3)
        response = client.get(reverse("literature:item-list"), {"q": "   "})
        assert len(response.context["table"].page.object_list) == 3

    def test_a_percent_sign_is_matched_literally_not_as_a_wildcard(self, client, db):
        # "%" is the database's own multi-character wildcard. A
        # naive, unescaped `LIKE '%' || value || '%'` would match "100X..."
        # too, since the user's own "%" would itself act as a wildcard;
        # confirmed directly against this database with an unescaped raw
        # query before writing this test. Django's ORM-level icontains
        # escapes the value first, so only the literal substring matches.
        literal_match = ItemFactory(title="100% Guaranteed Results")
        decoy = ItemFactory(title="100X Guaranteed Results")
        content = client.get(
            reverse("literature:item-list"), {"q": "100%"}
        ).content.decode()
        assert literal_match.citation_key in content
        assert decoy.citation_key not in content

    def test_an_underscore_is_matched_literally_not_as_a_wildcard(self, client, db):
        # "_" is the database's own single-character wildcard,
        # confirmed the same way as the "%" case above.
        literal_match = ItemFactory(title="Sample_ID Formation")
        decoy = ItemFactory(title="SampleXID Formation")
        content = client.get(
            reverse("literature:item-list"), {"q": "Sample_ID"}
        ).content.decode()
        assert literal_match.citation_key in content
        assert decoy.citation_key not in content

    def test_a_search_matching_something_states_how_many(self, client, db):
        # django-mvp's own position line, which already reads the
        # table's narrowed page and paginator (no production change of this
        # feature's own): confirmed the search reduces what it counts, not
        # only what it lists.
        ItemFactory.create_batch(3)
        ItemFactory(title="Zzyxq Unique Match")
        content = client.get(
            reverse("literature:item-list"), {"q": "zzyxq"}
        ).content.decode()
        assert "1-1 of 1" in content

    def test_a_search_matching_nothing_keeps_its_controls(self, client, db):
        ItemFactory.create_batch(3)
        content = client.get(
            reverse("literature:item-list"), {"q": "no-such-term-anywhere"}
        ).content.decode()
        assert 'name="q"' in content
        assert "filterModal" in content

    @pytest.mark.parametrize(
        "clearing_params", [{"q": ""}, {}], ids=["empty-q", "no-q"]
    )
    def test_clearing_the_search_restores_the_unnarrowed_catalogue(
        self, client, db, clearing_params
    ):
        # A request carrying an empty q, and one carrying no q at
        # all, each return the whole catalogue where the preceding search
        # had narrowed it. Upstream's search mixin already no-ops on an
        # empty term; this is the guard that it goes on doing so.
        ItemFactory.create_batch(5)
        narrowed = client.get(
            reverse("literature:item-list"), {"q": "no-such-term-anywhere"}
        )
        assert len(narrowed.context["table"].page.object_list) == 0
        cleared = client.get(reverse("literature:item-list"), clearing_params)
        assert len(cleared.context["table"].page.object_list) == 5


class TestCatalogueFilters:
    def test_type_narrows_to_the_chosen_type(self, client, db):
        book = ItemFactory(type=ItemType.BOOK)
        article = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = client.get(
            reverse("literature:item-list"), {"type": ItemType.BOOK}
        ).content.decode()
        assert book.citation_key in content
        assert article.citation_key not in content

    def test_type_choices_offer_the_translatable_label_while_the_url_narrows_on_the_stored_value(
        self, client, db
    ):
        # Read from the filter control, not a row's type cell, which would
        # pass even if the control's own choices broke.
        content = client.get(reverse("literature:item-list")).content.decode()
        label = re.escape(str(ItemType.ARTICLE_JOURNAL.label))
        assert re.search(
            rf'<option value="article-journal"[^>]*>\s*{label}\s*</option>', content
        )

    def test_contributor_narrows_to_references_crediting_them_in_any_role(
        self, client, db
    ):
        item = ItemFactory()
        ItemNameFactory(
            item=item, name=NameFactory(family="Darwin"), role=NameRole.EDITOR
        )
        other = ItemFactory()
        content = client.get(
            reverse("literature:item-list"), {"contributor": "darwin"}
        ).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_a_reference_crediting_the_same_contributor_in_two_roles_is_returned_once(
        self, client, db
    ):
        item = ItemFactory()
        darwin = NameFactory(family="Darwin")
        ItemNameFactory(item=item, name=darwin, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=darwin, role=NameRole.EDITOR)
        response = client.get(
            reverse("literature:item-list"), {"contributor": "darwin"}
        )
        matches = [
            row
            for row in response.context["table"].page.object_list
            if row.record.pk == item.pk
        ]
        assert len(matches) == 1

    def test_issued_year_narrows_on_a_year_only_stored_date(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        other = ItemFactory()
        ItemDateFactory(item=other, date_type=DateType.ISSUED, begin="2021")
        content = client.get(
            reverse("literature:item-list"), {"issued_year": 2020}
        ).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_issued_year_narrows_on_a_range_beginning_that_year(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2019", end="2021")
        other = ItemFactory()
        ItemDateFactory(item=other, date_type=DateType.ISSUED, begin="2021")
        content = client.get(
            reverse("literature:item-list"), {"issued_year": 2019}
        ).content.decode()
        assert item.citation_key in content
        assert other.citation_key not in content

    def test_issued_year_excludes_a_reference_carrying_no_issued_date(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        undated = ItemFactory()
        content = client.get(
            reverse("literature:item-list"), {"issued_year": 2020}
        ).content.decode()
        assert item.citation_key in content
        assert undated.citation_key not in content

    def test_language_narrows_on_the_stored_value(self, client, db):
        en_item = ItemFactory(language="en")
        other = ItemFactory(language="fr")
        content = client.get(
            reverse("literature:item-list"), {"language": "en"}
        ).content.decode()
        assert en_item.citation_key in content
        assert other.citation_key not in content

    def test_language_choices_offer_only_values_the_catalogue_holds(self, client, db):
        ItemFactory(language="en")
        content = client.get(reverse("literature:item-list")).content.decode()
        assert re.search(r'<option value="en"[^>]*>\s*en\s*</option>', content)
        assert 'value="de"' not in content


class TestCatalogueFilterComposition:
    def test_more_than_one_value_within_a_filter_widens_to_either(self, client, db):
        article = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        chapter = ItemFactory(type=ItemType.CHAPTER)
        book = ItemFactory(type=ItemType.BOOK)
        content = client.get(
            reverse("literature:item-list"),
            {"type": [ItemType.ARTICLE_JOURNAL, ItemType.CHAPTER]},
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

    def test_a_filter_and_a_search_term_narrow_to_both_and_the_count_reflects_it(
        self, client, db
    ):
        matching = ItemFactory(type=ItemType.BOOK, title="Whale Migration Patterns")
        wrong_type = ItemFactory(
            type=ItemType.ARTICLE_JOURNAL, title="Whale Migration Patterns"
        )
        wrong_term = ItemFactory(type=ItemType.BOOK, title="Unrelated Reference")
        response = client.get(
            reverse("literature:item-list"), {"q": "whale", "type": ItemType.BOOK}
        )
        content = response.content.decode()
        assert matching.citation_key in content
        assert wrong_type.citation_key not in content
        assert wrong_term.citation_key not in content
        assert "1-1 of 1" in content

    def test_widening_within_type_still_narrows_against_a_second_filter(
        self, client, db
    ):
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
    def test_no_badge_when_nothing_is_applied(self, client, db):
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "indicator-item badge badge-secondary badge-xs" not in content

    def test_a_filter_in_force_is_counted_and_shown_as_a_badge(self, client, db):
        ItemFactory(type=ItemType.BOOK)
        response = client.get(reverse("literature:item-list"), {"type": ItemType.BOOK})
        assert response.context["applied_filter_count"] == 1
        content = response.content.decode()
        assert (
            '<span class="indicator-item badge badge-secondary badge-xs">1</span>'
            in content
        )

    def test_two_filters_in_force_are_both_counted(self, client, db):
        ItemFactory(type=ItemType.BOOK, language="en")
        response = client.get(
            reverse("literature:item-list"), {"type": ItemType.BOOK, "language": "en"}
        )
        assert response.context["applied_filter_count"] == 2
        content = response.content.decode()
        assert (
            '<span class="indicator-item badge badge-secondary badge-xs">2</span>'
            in content
        )

    def test_a_search_term_alone_carries_no_filter_badge(self, client, db):
        # The badge belongs to the Filter button specifically (django-mvp's own
        # count is filter-only) — `q` is
        # not one of `self.filterset.filters`, so it never reaches
        # `filterset.form.cleaned_data`.
        ItemFactory(title="Whale Migration Patterns")
        content = client.get(
            reverse("literature:item-list"), {"q": "whale"}
        ).content.decode()
        assert "indicator-item badge badge-secondary badge-xs" not in content

    def test_the_chosen_value_stays_selected_on_the_rendered_control(self, client, db):
        ItemFactory(type=ItemType.BOOK)
        content = client.get(
            reverse("literature:item-list"), {"type": ItemType.BOOK}
        ).content.decode()
        assert re.search(
            r'<option value="book"[^>]*\sselected[^>]*>\s*Book\s*</option>', content
        )

    @pytest.mark.parametrize(
        "clearing_params", [{"type": ""}, {}], ids=["empty-type", "no-params"]
    )
    def test_clearing_a_filter_restores_the_unfiltered_catalogue(
        self, client, db, clearing_params
    ):
        matching = ItemFactory(type=ItemType.BOOK)
        other = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        narrowed = client.get(reverse("literature:item-list"), {"type": ItemType.BOOK})
        assert len(narrowed.context["table"].page.object_list) == 1
        cleared = client.get(reverse("literature:item-list"), clearing_params)
        cleared_pks = {
            row.record.pk for row in cleared.context["table"].page.object_list
        }
        assert cleared_pks == {matching.pk, other.pk}


class TestCatalogueFilterValidation:
    def test_an_unmatched_value_of_a_declared_filter_matches_nothing(self, client, db):
        ItemFactory(language="en")
        response = client.get(reverse("literature:item-list"), {"language": "zz"})
        assert response.status_code == 200
        assert len(response.context["table"].page.object_list) == 0

    def test_an_invalid_value_of_a_declared_filter_matches_nothing(self, client, db):
        ItemFactory()
        response = client.get(
            reverse("literature:item-list"), {"issued_year": "notanumber"}
        )
        assert response.status_code == 200
        assert len(response.context["table"].page.object_list) == 0

    def test_neither_case_falls_back_to_the_unfiltered_catalogue(self, client, db):
        ItemFactory.create_batch(3, language="en")
        unmatched = client.get(reverse("literature:item-list"), {"language": "zz"})
        assert len(unmatched.context["table"].page.object_list) == 0
        invalid = client.get(
            reverse("literature:item-list"), {"issued_year": "notanumber"}
        )
        assert len(invalid.context["table"].page.object_list) == 0

    def test_an_address_carrying_an_undeclared_key_is_ignored_not_rejected(
        self, client, db
    ):
        # Validation reads a filter *value*, not an undefined key: a Django
        # form simply ignores data it has no field for, so an address like
        # this is neither of the two cases above, and this feature
        # deliberately builds no rejection mechanism for it.
        # Pinned as what actually happens — 200, no exception, the
        # catalogue unnarrowed — not as a contract this feature owns.
        item = ItemFactory()
        response = client.get(reverse("literature:item-list"), {"bogus": "xyz"})
        assert response.status_code == 200
        assert [
            row.record.pk for row in response.context["table"].page.object_list
        ] == [item.pk]


#: One item-building override per plain sortable column, cycled by index so
#: 30 references get 30 distinct, independently-sortable values.
#: "type" cycles a fixed set of stored slugs rather than a unique value per
#: item — sorting is still monotonic across ties, and it doubles as the
#: check that ordering follows the stored slug, not the translated label.
PLAIN_SORTABLE_COLUMN_OVERRIDES = {
    "citation_key": lambda n: {"citation_key": f"Key{n:03d}"},
    "title": lambda n: {"title": f"Title{n:03d}"},
    "container_title": lambda n: {"container_title": f"Container{n:03d}"},
    "type": lambda n: {
        "type": [ItemType.ARTICLE, ItemType.BOOK, ItemType.CHAPTER][n % 3]
    },
}


class TestCatalogueOrdering:
    def catalogue_column_values(self, client, column, sort_param=None):
        """Return every reference's ``column`` value across both pages of the catalogue.

        Reads ``table.page``: ``SingleTableMixin`` sorts its own copy of the queryset, and
        ``object_list`` never reflects the sort.
        """
        values = []
        params = {"sort": sort_param} if sort_param else {}
        for page in (1, 2):
            response = client.get(
                reverse("literature:item-list"), {**params, "page": page}
            )
            values += [
                getattr(row.record, column)
                for row in response.context["table"].page.object_list
            ]
        return values

    @pytest.mark.parametrize("column", sorted(PLAIN_SORTABLE_COLUMN_OVERRIDES))
    def test_ascending_sort_orders_the_whole_catalogue_not_only_the_current_page(
        self, client, db, column
    ):
        # 30 references over a 24-row page.
        for n in range(30):
            ItemFactory(**PLAIN_SORTABLE_COLUMN_OVERRIDES[column](n))
        values = self.catalogue_column_values(client, column, sort_param=column)
        assert len(values) == 30
        assert values == sorted(values)

    def test_ascending_sort_by_issued_date_keeps_undated_references_last(
        self, client, db
    ):
        # Read through the HTTP sort param rather than only through
        # order_issued directly (TestIssuedOrdering already covers that).
        dated_keys = []
        for n in range(20):
            item = ItemFactory(citation_key=f"Dated{n:03d}")
            ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=str(2000 + n))
            dated_keys.append(item.citation_key)
        undated_keys = {
            ItemFactory(citation_key=f"Undated{n:03d}").citation_key for n in range(10)
        }
        citation_keys = self.catalogue_column_values(
            client, "citation_key", sort_param="issued"
        )
        assert citation_keys[:20] == dated_keys
        assert set(citation_keys[20:]) == undated_keys

    def test_sort_direction_reverses_on_a_second_request(self, client, db):
        for n in range(30):
            ItemFactory(citation_key=f"Key{n:03d}")
        ascending = self.catalogue_column_values(
            client, "citation_key", sort_param="citation_key"
        )
        descending = self.catalogue_column_values(
            client, "citation_key", sort_param="-citation_key"
        )
        assert ascending == list(reversed(descending))
        assert ascending != descending

    def test_sort_by_the_contributors_column_is_refused(self, client, db):
        # The credited-names cell has no single value to order on.
        first = ItemFactory(citation_key="First")
        second = ItemFactory(citation_key="Second")
        response = client.get(reverse("literature:item-list"), {"sort": "contributors"})
        assert response.status_code == 200
        # Refused, not errored: django-tables2 silently drops an order_by
        # alias naming a non-orderable column, so the table keeps its
        # default newest-first order rather than raising or reordering.
        citation_keys = [
            row.record.citation_key
            for row in response.context["table"].page.object_list
        ]
        assert citation_keys == [second.citation_key, first.citation_key]

    def test_sort_by_the_actions_column_is_refused(self, client, db):
        # A control, not data, has no single value to order on.
        first = ItemFactory(citation_key="First")
        second = ItemFactory(citation_key="Second")
        response = client.get(reverse("literature:item-list"), {"sort": "actions"})
        assert response.status_code == 200
        citation_keys = [
            row.record.citation_key
            for row in response.context["table"].page.object_list
        ]
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
        first_page_records = [
            row.record for row in first_page.context["table"].page.object_list
        ]
        second_page_records = [
            row.record for row in second_page.context["table"].page.object_list
        ]
        # Still descending across the page boundary.
        assert second_page_records[0].citation_key < first_page_records[-1].citation_key


class TestCatalogueStateSurvivesAPageMove:
    def test_a_search_survives_following_the_rendered_link_to_page_2(self, client, db):
        for n in range(30):
            ItemFactory(title=f"Whale Migration {n:03d}")
        ItemFactory.create_batch(5, title="Unrelated Reference")
        list_url = reverse("literature:item-list")
        first_page = client.get(list_url, {"q": "whale"})
        first_page_records = [
            row.record for row in first_page.context["table"].page.object_list
        ]
        second_page_href = rendered_page_link(first_page.content.decode(), 2)
        second_page = client.get(urljoin(list_url, second_page_href))
        second_page_records = [
            row.record for row in second_page.context["table"].page.object_list
        ]
        assert second_page_records
        # Not merely "narrowed" — the second page's own rows, distinct from
        # the first's. A ?page=2 read as the literal parameter "amp;page"
        # falls back to page one, which would satisfy the narrowing
        # assertion below without ever proving a page move happened.
        assert {r.pk for r in second_page_records}.isdisjoint(
            {r.pk for r in first_page_records}
        )
        assert all("Whale Migration" in record.title for record in second_page_records)

    def test_a_filter_survives_following_the_rendered_link_to_page_2(self, client, db):
        ItemFactory.create_batch(30, type=ItemType.BOOK)
        ItemFactory.create_batch(5, type=ItemType.ARTICLE_JOURNAL)
        list_url = reverse("literature:item-list")
        first_page = client.get(list_url, {"type": ItemType.BOOK})
        first_page_records = [
            row.record for row in first_page.context["table"].page.object_list
        ]
        second_page_href = rendered_page_link(first_page.content.decode(), 2)
        second_page = client.get(urljoin(list_url, second_page_href))
        second_page_records = [
            row.record for row in second_page.context["table"].page.object_list
        ]
        assert second_page_records
        assert {r.pk for r in second_page_records}.isdisjoint(
            {r.pk for r in first_page_records}
        )
        assert all(record.type == ItemType.BOOK for record in second_page_records)

    def test_a_search_a_filter_and_a_sort_all_survive_together_following_the_rendered_link_to_page_2(
        self, client, db
    ):
        for n in range(30):
            ItemFactory(
                type=ItemType.BOOK,
                title=f"Whale Migration {n:03d}",
                citation_key=f"Key{29 - n:03d}",
            )
        ItemFactory.create_batch(
            5, type=ItemType.ARTICLE_JOURNAL, title="Whale Migration Decoy"
        )
        ItemFactory.create_batch(5, type=ItemType.BOOK, title="Unrelated Reference")
        list_url = reverse("literature:item-list")
        params = {"q": "whale", "type": ItemType.BOOK, "sort": "-citation_key"}
        first_page = client.get(list_url, params)
        first_page_records = [
            row.record for row in first_page.context["table"].page.object_list
        ]
        second_page_href = rendered_page_link(first_page.content.decode(), 2)
        second_page = client.get(urljoin(list_url, second_page_href))
        second_page_records = [
            row.record for row in second_page.context["table"].page.object_list
        ]
        assert second_page_records
        assert all("Whale Migration" in record.title for record in second_page_records)
        assert all(record.type == ItemType.BOOK for record in second_page_records)
        assert second_page_records[0].citation_key < first_page_records[-1].citation_key


class TestCatalogueStateSurvivesAPageMoveOnTheCardList:
    def test_a_search_survives_following_the_rendered_link_to_page_2(self, client, db):
        for n in range(30):
            ItemFactory(title=f"Whale Migration {n:03d}")
        ItemFactory.create_batch(5, title="Unrelated Reference")
        list_url = reverse("item-list-cards")
        first_page = client.get(list_url, {"q": "whale"})
        first_page_records = list(first_page.context["object_list"])
        second_page_href = rendered_page_link(first_page.content.decode(), 2)
        second_page = client.get(urljoin(list_url, second_page_href))
        second_page_records = list(second_page.context["object_list"])
        assert second_page_records
        assert {r.pk for r in second_page_records}.isdisjoint(
            {r.pk for r in first_page_records}
        )
        assert all("Whale Migration" in record.title for record in second_page_records)

    def test_a_filter_survives_following_the_rendered_link_to_page_2(self, client, db):
        ItemFactory.create_batch(30, type=ItemType.BOOK)
        ItemFactory.create_batch(5, type=ItemType.ARTICLE_JOURNAL)
        list_url = reverse("item-list-cards")
        first_page = client.get(list_url, {"type": ItemType.BOOK})
        first_page_records = list(first_page.context["object_list"])
        second_page_href = rendered_page_link(first_page.content.decode(), 2)
        second_page = client.get(urljoin(list_url, second_page_href))
        second_page_records = list(second_page.context["object_list"])
        assert second_page_records
        assert {r.pk for r in second_page_records}.isdisjoint(
            {r.pk for r in first_page_records}
        )
        assert all(record.type == ItemType.BOOK for record in second_page_records)


class TestCatalogueStateSurvivesAChangeOfSort:
    def test_search_and_a_filter_survive_a_change_of_sort_from_a_column_heading(
        self, client, db
    ):
        matching_high = ItemFactory(
            type=ItemType.BOOK, title="Whale Migration Zeta", citation_key="KeyZ"
        )
        matching_low = ItemFactory(
            type=ItemType.BOOK, title="Whale Migration Alpha", citation_key="KeyA"
        )
        wrong_type = ItemFactory(
            type=ItemType.ARTICLE_JOURNAL,
            title="Whale Migration Beta",
            citation_key="KeyB",
        )
        wrong_term = ItemFactory(
            type=ItemType.BOOK, title="Unrelated Reference", citation_key="KeyC"
        )
        list_url = reverse("literature:item-list")
        first_page = client.get(list_url, {"q": "whale", "type": ItemType.BOOK})
        sort_href = rendered_sort_link(first_page.content.decode(), "Citation key")
        sorted_response = client.get(urljoin(list_url, sort_href))
        sorted_records = [
            row.record for row in sorted_response.context["table"].page.object_list
        ]
        # Narrowed to the two matches, not the whole four-row catalogue —
        # the search and the filter are both still in force.
        assert {r.pk for r in sorted_records} == {matching_high.pk, matching_low.pk}
        assert wrong_type.pk not in {r.pk for r in sorted_records}
        assert wrong_term.pk not in {r.pk for r in sorted_records}
        # Ordered by the clicked column, over only the narrowed set.
        assert [r.citation_key for r in sorted_records] == [
            matching_low.citation_key,
            matching_high.citation_key,
        ]


class TestCatalogueStateSurvivesAChangeOfFilter:
    def test_sort_survives_a_change_of_filter_submitted_from_the_filter_form(
        self, client, db
    ):
        # citation_key runs the opposite way to creation order, so a sort
        # by -citation_key produces a different row order than the
        # catalogue's default (-created), for the same reason as the sort
        # fixtures above: a test where the two
        # coincide would pass whether or not the sort actually survived.
        older_last_key = ItemFactory(type=ItemType.BOOK, citation_key="KeyZ")
        newer_first_key = ItemFactory(type=ItemType.BOOK, citation_key="KeyA")
        ItemFactory(type=ItemType.ARTICLE_JOURNAL, citation_key="KeyM")
        list_url = reverse("literature:item-list")
        first_response = client.get(list_url, {"sort": "-citation_key"})
        form_data = rendered_filter_form_data(first_response, type=ItemType.BOOK)
        filtered_response = client.get(list_url, form_data)
        filtered_records = [
            row.record for row in filtered_response.context["table"].page.object_list
        ]
        # Narrowed to the two BOOK rows, and still ordered by -citation_key
        # (KeyZ before KeyA) — the catalogue's default (-created) would
        # order them the other way (newer_first_key before older_last_key).
        assert filtered_records == [older_last_key, newer_first_key]

    def test_an_active_sort_is_not_counted_or_shown_as_an_applied_filter(
        self, client, db
    ):
        ItemFactory(type=ItemType.BOOK)
        list_url = reverse("literature:item-list")
        unsorted = client.get(list_url, {"type": ItemType.BOOK})
        sorted_ = client.get(list_url, {"type": ItemType.BOOK, "sort": "-citation_key"})
        assert (
            sorted_.context["applied_filter_count"]
            == unsorted.context["applied_filter_count"]
        )
        assert set(sorted_.context["applied_filters"]) == set(
            unsorted.context["applied_filters"]
        )
        badge_re = (
            r'<span class="indicator-item badge badge-secondary badge-xs">(\d+)</span>'
        )
        sorted_badge = re.search(badge_re, sorted_.content.decode())
        unsorted_badge = re.search(badge_re, unsorted.content.decode())
        assert sorted_badge.group(1) == unsorted_badge.group(1)

    def test_a_sort_alone_carries_no_filter_badge(self, client, db):
        ItemFactory()
        content = client.get(
            reverse("literature:item-list"), {"sort": "-citation_key"}
        ).content.decode()
        assert "indicator-item badge badge-secondary badge-xs" not in content


class TestCatalogueStateSurvivesReopeningTheAddress:
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
        first_pks = {
            row.record.pk for row in first_visit.context["table"].page.object_list
        }
        reopened_pks = {
            row.record.pk for row in reopened.context["table"].page.object_list
        }
        assert first_pks == {matching.pk}
        assert reopened_pks == first_pks


class TestItemCreateView:
    def test_page_renders_and_the_type_select_carries_the_alpine_scoping(
        self, client, db
    ):
        response = client.get(reverse("literature:item-create"))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'x-model="form.itemType"' in content
        assert 'x-init="form.itemType = $el.value"' in content

    def test_with_no_type_chosen_every_group_but_the_type_fields_own_is_guarded(
        self, client, db
    ):
        # With no type chosen, only the type field itself has no
        # x-show guard; every one of the thirteen groups does, so nothing
        # else among the scalar-field groups shows. Scoped to the
        # `typeGroups` guard specifically: the page's contributor,
        # date and identifier rows carry their own unrelated `x-show`, one
        # per row, for the removed-row state — a raw page-wide count would
        # conflate the two.
        content = client.get(reverse("literature:item-create")).content.decode()
        for group in FieldGroups.GROUPS:
            assert f"includes('{group}')" in content
        assert content.count("form.typeGroups[form.itemType]") == len(
            FieldGroups.GROUPS
        )

    def test_posting_a_valid_form_stores_exactly_what_was_posted(self, client, db):
        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="Doe2024",
            title="A Handwritten Reference",
        )
        client.post(reverse("literature:item-create"), data)
        item = Item.objects.get(citation_key="Doe2024")
        assert item.type == ItemType.ARTICLE_JOURNAL
        assert item.title == "A Handwritten Reference"

    def test_posting_a_valid_form_redirects_to_the_new_items_detail_page(
        self, client, db
    ):
        data = create_page_post_data(
            client, type=ItemType.ARTICLE_JOURNAL, citation_key="Redirect2024"
        )
        response = client.post(reverse("literature:item-create"), data)
        item = Item.objects.get(citation_key="Redirect2024")
        assert response.status_code == 302
        assert response.url == reverse("literature:item-detail", kwargs={"pk": item.pk})

    def test_posting_without_a_type_stores_nothing_and_names_the_field(
        self, client, db
    ):
        data = create_page_post_data(client, type="", citation_key="NoType2024")
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 200
        assert not Item.objects.filter(citation_key="NoType2024").exists()
        assert "type" in response.context["form"].errors

    def test_posting_without_a_citation_key_stores_nothing_and_names_the_field(
        self, client, db
    ):
        data = create_page_post_data(
            client, type=ItemType.ARTICLE_JOURNAL, citation_key=""
        )
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 200
        assert Item.objects.count() == 0
        assert "citation_key" in response.context["form"].errors

    def test_a_duplicate_citation_key_is_stored_unchanged(self, client, db):
        # citation_key is not globally unique; a colliding key is a fact the
        # store holds, never a validation error.
        ItemFactory(citation_key="Repeated2024")
        data = create_page_post_data(
            client, type=ItemType.ARTICLE_JOURNAL, citation_key="Repeated2024"
        )
        client.post(reverse("literature:item-create"), data)
        assert Item.objects.filter(citation_key="Repeated2024").count() == 2

    def test_a_created_items_detail_page_renders_with_no_contributors_dates_or_identifiers(
        self, client, db
    ):
        data = create_page_post_data(
            client, type=ItemType.ARTICLE_JOURNAL, citation_key="Bare2024"
        )
        response = client.post(reverse("literature:item-create"), data, follow=True)
        assert response.status_code == 200
        assert response.context["contributor_groups"] == []
        assert response.context["identifiers"] == []


class TestItemFormInlineSets:
    def test_the_create_page_renders_all_three_inline_sets(self, client, db):
        content = client.get(reverse("literature:item-create")).content.decode()
        assert 'name="item_names-TOTAL_FORMS"' in content
        assert 'name="item_dates-TOTAL_FORMS"' in content
        assert 'name="item_identifiers-TOTAL_FORMS"' in content

    def test_the_update_page_renders_all_three_inline_sets(self, client, db):
        item = ItemFactory()
        content = client.get(
            reverse("literature:item-update", kwargs={"pk": item.pk})
        ).content.decode()
        assert 'name="item_names-TOTAL_FORMS"' in content
        assert 'name="item_dates-TOTAL_FORMS"' in content
        assert 'name="item_identifiers-TOTAL_FORMS"' in content

    def test_a_new_identifier_row_saves_in_the_same_transaction_as_the_reference(
        self, client, db
    ):
        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="WithIdentifier2024",
            **{
                "item_identifiers-0-type": "DOI",
                "item_identifiers-0-value": "10.1234/inline-test",
            },
        )
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 302
        item = Item.objects.get(citation_key="WithIdentifier2024")
        assert ItemIdentifier.objects.filter(
            item=item, type="DOI", value="10.1234/inline-test"
        ).exists()

    def test_an_invalid_parent_form_saves_no_identifier_and_keeps_the_typed_value_on_the_page(
        self, client, db
    ):
        # A rejected save leaves the catalogue exactly as it was,
        # and returns the form carrying what was entered.
        data = create_page_post_data(
            client,
            type="",  # invalid — rejects the parent form itself
            citation_key="NoType2024",
            **{
                "item_identifiers-0-type": "DOI",
                "item_identifiers-0-value": "10.1234/should-not-save",
            },
        )
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 200
        assert not ItemIdentifier.objects.filter(
            value="10.1234/should-not-save"
        ).exists()
        assert "10.1234/should-not-save" in response.content.decode()

    def test_an_invalid_date_row_reports_its_own_error_and_saves_nothing(
        self, client, db
    ):
        # An inline set's own error blocks the whole save,
        # not just its own rows, since all three formsets and the parent
        # form are validated with all_valid() and share one transaction.
        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="BadDate2024",
            **{
                "item_dates-0-date_type": DateType.EVENT_DATE,
                "item_dates-0-begin": "not-a-date",
            },
        )
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 200
        assert not Item.objects.filter(citation_key="BadDate2024").exists()
        assert "not-a-date" in response.content.decode()
        inlines = {formset.prefix: formset for formset in response.context["inlines"]}
        assert inlines["item_dates"].forms[0].errors


class TestDateRows:
    def test_a_type_leading_only_with_issued_can_be_given_an_accessed_date_without_leaving_the_form(
        self, client, db
    ):
        # MAP leads with no extra date slots of its own;
        # the accessed date is reached by naming the slot on the
        # set's own added row, not by a second page.
        item = ItemFactory(type=ItemType.MAP)
        data = update_page_post_data(
            client,
            item,
            **{
                "item_dates-TOTAL_FORMS": "2",
                "item_dates-1-date_type": DateType.ACCESSED,
                "item_dates-1-begin": "2023",
                "item_dates-1-end": "",
            },
        )
        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item.pk}), data
        )
        assert response.status_code == 302, (
            response.context["form"].errors if response.status_code != 302 else None
        )
        assert item.item_dates.filter(date_type=DateType.ACCESSED).exists()

    def test_clearing_a_date_removes_it_and_no_other_slot_moves(self, client, db):
        item = ItemFactory(type=ItemType.MAP)
        kept = ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        removed = ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2021")

        data = update_page_post_data(client, item)
        removed_row_prefix = next(
            name.rsplit("-id", 1)[0]
            for name, value in data.items()
            if name.startswith("item_dates-")
            and name.endswith("-id")
            and str(value) == str(removed.pk)
        )
        data[f"{removed_row_prefix}-DELETE"] = "on"

        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item.pk}), data
        )
        assert response.status_code == 302, (
            response.context["form"].errors if response.status_code != 302 else None
        )

        assert not ItemDate.objects.filter(pk=removed.pk).exists()
        kept.refresh_from_db()
        assert kept.date_type == DateType.ISSUED
        assert str(kept.begin) == "2020"


class TestContributorRows:
    def test_a_contributor_with_only_an_unparsed_name_saves(self, client, db):
        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="OrgAuthor2024",
            **{
                "item_names-0-role": NameRole.AUTHOR,
                "item_names-0-literal": "United Nations",
            },
        )
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 302, (
            response.context["form"].errors if response.status_code != 302 else None
        )
        item = Item.objects.get(citation_key="OrgAuthor2024")
        (item_name,) = item.item_names.all()
        assert item_name.name.literal == "United Nations"

    def test_a_contributor_with_neither_family_nor_unparsed_name_is_rejected(
        self, client, db
    ):
        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="NoNameAuthor2024",
            **{
                "item_names-0-role": NameRole.AUTHOR,
                "item_names-0-given": "Jane",
            },
        )
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 200
        assert not Item.objects.filter(citation_key="NoNameAuthor2024").exists()
        assert not Name.objects.filter(given="Jane").exists()

    def test_entering_a_name_matching_one_already_stored_creates_a_second_record(
        self, client, db
    ):
        # Crediting the same spelling across two references never
        # changes what the first reference's stored record is credited on.
        existing_item = ItemFactory()
        existing_link = ItemNameFactory(
            item=existing_item, name=NameFactory(family="Doe", given="Jane")
        )

        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="SecondDoe2024",
            **{
                "item_names-0-role": NameRole.AUTHOR,
                "item_names-0-family": "Doe",
                "item_names-0-given": "Jane",
            },
        )
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 302

        assert Name.objects.filter(family="Doe", given="Jane").count() == 2
        new_item = Item.objects.get(citation_key="SecondDoe2024")
        (new_link,) = new_item.item_names.all()
        assert new_link.name_id != existing_link.name_id

        existing_link.name.refresh_from_db()
        assert existing_link.name.family == "Doe"
        assert existing_item.item_names.filter(pk=existing_link.pk).exists()

    def test_the_same_name_entered_twice_in_one_role_stores_two_records(
        self, client, db
    ):
        # The interface never merges a repeated spelling within one role.
        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="TwoSameAuthors2024",
            **{
                "item_names-TOTAL_FORMS": "2",
                "item_names-0-role": NameRole.AUTHOR,
                "item_names-0-family": "Doe",
                "item_names-0-given": "Jane",
                "item_names-1-role": NameRole.AUTHOR,
                "item_names-1-family": "Doe",
                "item_names-1-given": "Jane",
            },
        )
        client.post(reverse("literature:item-create"), data)
        assert Name.objects.filter(family="Doe", given="Jane").count() == 2
        item = Item.objects.get(citation_key="TwoSameAuthors2024")
        assert item.item_names.count() == 2

    def test_editing_a_contributor_shared_by_import_never_rewrites_the_other_reference(
        self, client, db
    ):
        # The import path shares Name records
        # via get_or_create (literature/converters.py:_import_name_variable),
        # so two references imported with an identically spelled author are
        # already crediting the same record before either is ever edited
        # through this form. Editing one must not silently rename the other.
        def csl_item(citation_key):
            return {
                "id": citation_key,
                "type": "article-journal",
                "title": f"Title for {citation_key}",
                "author": [{"family": "Shared", "given": "Sam"}],
            }

        item_a = from_csl_json(csl_item("ImportA2024"))
        item_b = from_csl_json(csl_item("ImportB2024"))
        (link_a,) = item_a.item_names.all()
        (link_b,) = item_b.item_names.all()
        assert link_a.name_id == link_b.name_id  # the shared record the defect corrupts

        data = update_page_post_data(
            client,
            item_a,
            **{
                "item_names-0-family": "Changed",
            },
        )
        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item_a.pk}), data
        )
        assert response.status_code == 302

        link_b.name.refresh_from_db()
        assert link_b.name.family == "Shared"  # untouched

        link_a.refresh_from_db()
        assert link_a.name.family == "Changed"
        assert (
            link_a.name_id != link_b.name_id
        )  # repointed to a new record, not shared any more

    def test_editing_a_contributor_credited_on_nothing_else_updates_it_in_place(
        self, client, db
    ):
        # Nothing else observes the difference, so a
        # new record would only orphan the old one.
        item = ItemFactory()
        link = ItemNameFactory(
            item=item, name=NameFactory(family="Original", given="Sam")
        )
        original_name_id = link.name_id

        data = update_page_post_data(
            client, item, **{"item_names-0-family": "Corrected"}
        )
        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item.pk}), data
        )
        assert response.status_code == 302

        link.refresh_from_db()
        assert link.name_id == original_name_id
        assert link.name.family == "Corrected"

    def test_reordering_one_role_leaves_every_other_role_untouched(self, client, db):
        # A submission of 1, 1, 3 within one role becomes a
        # coherent sequence; a second role's own positions are untouched.
        item = ItemFactory()
        author_a = ItemNameFactory(
            item=item, role=NameRole.AUTHOR, name=NameFactory(family="A")
        )
        author_b = ItemNameFactory(
            item=item, role=NameRole.AUTHOR, name=NameFactory(family="B")
        )
        editor = ItemNameFactory(
            item=item, role=NameRole.EDITOR, name=NameFactory(family="E")
        )
        assert author_a.order == 0
        assert author_b.order == 1
        assert editor.order == 0

        # rendered_form_post_data indexes rows in queryset order (item, role,
        # order): 0 and 1 are the two authors, 2 is the editor. Swap the
        # authors' positions; leave the editor's own ORDER value as rendered.
        data = update_page_post_data(client, item)
        data["item_names-0-ORDER"] = "2"
        data["item_names-1-ORDER"] = "1"
        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item.pk}), data
        )
        assert response.status_code == 302, (
            response.context["form"].errors if response.status_code != 302 else None
        )

        author_a.refresh_from_db()
        author_b.refresh_from_db()
        editor.refresh_from_db()
        assert author_a.order > author_b.order  # A now follows B
        assert editor.order == 0  # the other role's own position is untouched

    def test_contributor_rows_are_grouped_by_role_on_the_page(self, client, db):
        # An ungrouped list showing positions 0, 0, 1, 2, 0 reads as
        # broken. The set renders through the packaged formset component,
        # which draws no role heading of its own, so this no longer asserts
        # a heading — it asserts the behaviour that actually ships:
        # ContributorInline.sort_forms() keeps one role's rows adjacent, and
        # each row's own role field, its first column, names the role
        # directly.
        item = ItemFactory()
        ItemNameFactory(item=item, role=NameRole.AUTHOR, name=NameFactory(family="A"))
        ItemNameFactory(item=item, role=NameRole.AUTHOR, name=NameFactory(family="B"))
        ItemNameFactory(item=item, role=NameRole.EDITOR, name=NameFactory(family="E"))
        content = client.get(
            reverse("literature:item-update", kwargs={"pk": item.pk})
        ).content.decode()

        # One <select name="item_names-N-role"> per rendered row, including
        # the unfilled extra row; that row's selected <option> is what names
        # its role now, in place of the heading the fork used to draw.
        role_selects = re.findall(
            r'name="item_names-\d+-role".*?</select>', content, re.DOTALL
        )
        selected_roles = [
            match.group(1)
            for block in role_selects
            if (match := re.search(r'<option value="([^"]+)"\s+selected', block))
        ]
        assert selected_roles == [NameRole.AUTHOR, NameRole.AUTHOR, NameRole.EDITOR]

    def test_no_ordering_across_roles_is_offered(self, client, db):
        # An author and an editor may share the same submitted
        # ORDER value with no collision, since each role is its own scope.
        item = ItemFactory()
        author = ItemNameFactory(
            item=item, role=NameRole.AUTHOR, name=NameFactory(family="A")
        )
        editor = ItemNameFactory(
            item=item, role=NameRole.EDITOR, name=NameFactory(family="E")
        )

        data = update_page_post_data(client, item)
        data["item_names-0-ORDER"] = "0"
        data["item_names-1-ORDER"] = "0"
        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item.pk}), data
        )
        assert response.status_code == 302

        author.refresh_from_db()
        editor.refresh_from_db()
        assert author.order == 0
        assert editor.order == 0
        assert item.item_names.filter(role=NameRole.AUTHOR).count() == 1
        assert item.item_names.filter(role=NameRole.EDITOR).count() == 1

    def test_removing_a_contributor_removes_the_link_and_never_the_name(
        self, client, db
    ):
        item = ItemFactory()
        link = ItemNameFactory(item=item, name=NameFactory(family="Survivor"))
        name_id = link.name_id

        data = update_page_post_data(client, item, **{"item_names-0-DELETE": "on"})
        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item.pk}), data
        )
        assert response.status_code == 302

        assert not ItemName.objects.filter(pk=link.pk).exists()
        assert Name.objects.filter(pk=name_id).exists()

    def test_a_contributor_removed_from_everything_still_has_its_own_page_listing_nothing(
        self, client, db
    ):
        # A contributor credited on nothing still has a page.
        item = ItemFactory()
        link = ItemNameFactory(item=item, name=NameFactory(family="LoneCredit"))
        name_id = link.name_id

        data = update_page_post_data(client, item, **{"item_names-0-DELETE": "on"})
        client.post(reverse("literature:item-update", kwargs={"pk": item.pk}), data)

        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": name_id})
        )
        assert response.status_code == 200
        assert list(response.context["object_list"]) == []

    def test_a_save_rejected_elsewhere_on_the_form_leaves_no_name_record_behind(
        self, client, db
    ):
        # The failure a naive implementation produces:
        # records created while processing the form and orphaned when
        # validation fails elsewhere. Rejected here by the parent form's own
        # missing citation_key, with a fully valid contributor row alongside it.
        before = set(Name.objects.values_list("pk", flat=True))
        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="",
            **{
                "item_names-0-role": NameRole.AUTHOR,
                "item_names-0-family": "ShouldNotPersist",
                "item_names-0-given": "Nobody",
            },
        )
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 200
        assert set(Name.objects.values_list("pk", flat=True)) == before
        assert not Name.objects.filter(family="ShouldNotPersist").exists()
        content = response.content.decode()
        assert 'value="ShouldNotPersist"' in content

    def test_editing_a_contributor_row_unchanged_writes_nothing(self, client, db):
        item = ItemFactory()
        link = ItemNameFactory(
            item=item, name=NameFactory(family="Steady", given="Sam")
        )
        original_name_id = link.name_id
        original_modified = link.name.modified

        data = update_page_post_data(client, item)
        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item.pk}), data
        )
        assert response.status_code == 302

        link.refresh_from_db()
        assert link.name_id == original_name_id
        assert link.name.family == "Steady"
        assert link.name.modified == original_modified


class TestContributorDatalist:
    def test_the_create_page_offers_stored_family_names_as_suggestions(
        self, client, db
    ):
        NameFactory(family="Aardvark")
        content = client.get(reverse("literature:item-create")).content.decode()
        assert '<option value="Aardvark">' in content

    def test_the_family_input_references_the_datalist(self, client, db):
        content = client.get(reverse("literature:item-create")).content.decode()
        match = re.search(r'<input[^>]*name="item_names-0-family"[^>]*>', content)
        assert match, "no rendered family input"
        list_match = re.search(r'list="([^"]+)"', match.group(0))
        assert list_match, "family input carries no list= attribute"
        assert f'<datalist id="{list_match.group(1)}"' in content

    def test_accepting_a_suggestion_posts_text_and_nothing_identifying(
        self, client, db
    ):
        # The datalist's own option carries no id, no name pk, nothing but
        # the text a browser fills the input with on acceptance.
        NameFactory(family="Aardvark")
        content = client.get(reverse("literature:item-create")).content.decode()
        assert re.search(r'<option value="Aardvark">\s*</option>', content)

    def test_a_name_absent_from_the_list_is_accepted_the_same_as_one_present_in_it(
        self, client, db
    ):
        NameFactory(family="Aardvark")
        data = create_page_post_data(
            client,
            type=ItemType.ARTICLE_JOURNAL,
            citation_key="NotSuggested2024",
            **{
                "item_names-0-role": NameRole.AUTHOR,
                "item_names-0-family": "NeverStoredBefore",
            },
        )
        response = client.post(reverse("literature:item-create"), data)
        assert response.status_code == 302
        item = Item.objects.get(citation_key="NotSuggested2024")
        assert item.item_names.get().name.family == "NeverStoredBefore"


class TestItemImportView:
    def test_get_renders_the_form_page_with_a_format_choice_and_a_file_control(
        self, client, db
    ):
        response = client.get(reverse("literature:item-import"))
        assert response.status_code == 200
        content = response.content.decode()
        assert "<select" in content
        assert 'name="format"' in content
        assert 'type="file"' in content

    def test_a_valid_bibtex_upload_creates_the_reference_and_responds_with_the_report(
        self, client, db
    ):
        with (DATA_DIR / "publication.bib").open("rb") as handle:
            upload = SimpleUploadedFile("publication.bib", handle.read())
        response = client.post(
            reverse("literature:item-import"),
            {"format": "bibtex", "file": upload, "skip_preview": "on"},
        )

        assert response.status_code == 200  # a report page, never a redirect
        assert Item.objects.filter(citation_key="10.1093/gji/ggz376").exists()

    def test_the_response_carries_the_counts_and_one_row_per_entry_in_source_order(
        self, client, db
    ):
        with (DATA_DIR / "publication.bib").open("rb") as handle:
            upload = SimpleUploadedFile("publication.bib", handle.read())
        response = client.post(
            reverse("literature:item-import"),
            {"format": "bibtex", "file": upload, "skip_preview": "on"},
        )

        report = response.context["report"]
        assert report.total == 1
        assert report.created == 1
        assert [row.position for row in report.rows] == [1]

    def test_a_created_row_links_to_its_reference(self, client, db):
        with (DATA_DIR / "publication.bib").open("rb") as handle:
            upload = SimpleUploadedFile("publication.bib", handle.read())
        response = client.post(
            reverse("literature:item-import"),
            {"format": "bibtex", "file": upload, "skip_preview": "on"},
        )

        item = Item.objects.get(citation_key="10.1093/gji/ggz376")
        content = response.content.decode()
        assert (
            f'href="{reverse("literature:item-detail", kwargs={"pk": item.pk})}"'
            in content
        )

    def test_the_same_file_uploaded_as_ris_behaves_the_same_way(self, client, db):
        upload = SimpleUploadedFile("publication.ris", RIS_ONE_GOOD_ENTRY.encode())
        response = client.post(
            reverse("literature:item-import"),
            {"format": "ris", "file": upload, "skip_preview": "on"},
        )

        assert response.status_code == 200
        assert response.context["report"].created == 1
        assert response.context["report"].total == 1

    def test_a_file_mixing_a_converting_entry_with_a_failing_one_reports_each_correctly(
        self, client, db
    ):
        upload = SimpleUploadedFile("mixed.ris", RIS_ONE_GOOD_ONE_BAD.encode())
        response = client.post(
            reverse("literature:item-import"),
            {"format": "ris", "file": upload, "skip_preview": "on"},
        )

        report = response.context["report"]
        assert report.created == 1
        assert report.failed == 1
        assert Item.objects.filter(title="A Working RIS Reference").exists()
        assert not Item.objects.filter(title="A Record With No Reference Type").exists()

    def test_the_report_is_not_paginated(self, client, db):
        upload = SimpleUploadedFile("mixed.ris", RIS_ONE_GOOD_ONE_BAD.encode())
        response = client.post(
            reverse("literature:item-import"),
            {"format": "ris", "file": upload, "skip_preview": "on"},
        )
        assert (
            "page_obj" not in response.context or response.context["page_obj"] is None
        )


class TestItemImportViewRejects:
    def test_no_file_attached_redisplays_the_form_with_a_reason_and_imports_nothing(
        self, client, db
    ):
        response = client.post(reverse("literature:item-import"), {"format": "bibtex"})
        assert response.status_code == 200  # form_invalid renders, never redirects
        assert response.context["form"].errors["file"]
        assert Item.objects.count() == 0

    def test_no_format_chosen_redisplays_the_form_with_a_reason_and_imports_nothing(
        self, client, db
    ):
        with (DATA_DIR / "publication.bib").open("rb") as handle:
            upload = SimpleUploadedFile("publication.bib", handle.read())
        response = client.post(reverse("literature:item-import"), {"file": upload})
        assert response.status_code == 200
        assert response.context["form"].errors["format"]
        assert Item.objects.count() == 0

    def test_an_empty_file_is_reported_with_a_reason_and_no_server_error(
        self, client, db
    ):
        upload = SimpleUploadedFile("empty.bib", b"")
        response = client.post(
            reverse("literature:item-import"), {"format": "bibtex", "file": upload}
        )
        assert response.status_code == 200
        assert response.context["form"].errors["file"]
        assert Item.objects.count() == 0

    def test_a_file_the_chosen_format_cannot_read_carries_the_formats_own_reason(
        self, client, db
    ):
        # RIS content submitted as bibtex — bibtexparser finds no "@type{" block.
        # A valid form submission previews by default now, so
        # the failure surfaces on the preview address reached by redirect,
        # not on this response directly.
        upload = SimpleUploadedFile("wrong-format.bib", RIS_ONE_GOOD_ENTRY.encode())
        response = client.post(
            reverse("literature:item-import"), {"format": "bibtex", "file": upload}
        )
        assert response.status_code == 302
        report = client.get(response.url).context["report"]
        assert report.failed == 1
        # The format's own sentence, not a Python exception's repr. Asserting
        # only that a reason is present would pass on the "TypeError: cannot
        # use a string pattern on a bytes-like object" this feature's first
        # phase existed to remove, which is the regression worth catching.
        assert (
            report.rows[0].reason == "No BibTeX entries found. Is this a BibTeX file?"
        )
        assert Item.objects.count() == 0

    def test_undecodable_bytes_are_reported_and_no_server_error_is_raised(
        self, client, db
    ):
        upload = SimpleUploadedFile("bad-bytes.ris", b"\x80\x81\x82")
        response = client.post(
            reverse("literature:item-import"), {"format": "ris", "file": upload}
        )
        assert response.status_code == 302
        report = client.get(response.url).context["report"]
        assert report.failed == 1
        # Names the encoding attempted and the offset that broke, which is
        # what a reader can act on — and again, not an exception's repr.
        assert (
            report.rows[0].reason
            == "Could not decode this file as utf-8: invalid byte at offset 0."
        )
        assert Item.objects.count() == 0


class TestItemImportPreviewPage:
    def _submit(self, client, filename="publication.bib", format_name="bibtex"):
        with (DATA_DIR / filename).open("rb") as handle:
            upload = SimpleUploadedFile(filename, handle.read())
        return client.post(
            reverse("literature:item-import"), {"format": format_name, "file": upload}
        )

    def test_submitting_the_form_redirects_to_the_preview_address(self, client, db):
        response = self._submit(client)
        assert response.status_code == 302
        assert response.url == reverse("literature:item-import-preview")

    def test_the_redirect_imports_nothing(self, client, db):
        self._submit(client)
        assert Item.objects.count() == 0

    def test_a_get_of_the_preview_rebuilds_the_report_from_the_staged_file(
        self, client, db
    ):
        self._submit(client)
        response = client.get(reverse("literature:item-import-preview"))
        assert response.status_code == 200
        report = response.context["report"]
        assert report.total == 1
        assert report.created == 1
        assert [row.position for row in report.rows] == [1]
        assert Item.objects.count() == 0

    def test_reloading_the_preview_shows_the_same_thing_and_imports_nothing(
        self, client, db
    ):
        # Not a raw content comparison: {% csrf_token %} mints a fresh masked
        # token on every render, so two otherwise-identical responses never
        # match byte for byte. The report itself is what "the same thing"
        # means here.
        self._submit(client)
        first = client.get(reverse("literature:item-import-preview")).context["report"]
        second = client.get(reverse("literature:item-import-preview")).context["report"]
        assert [row.position for row in first.rows] == [
            row.position for row in second.rows
        ]
        assert first.created == second.created == 1
        assert Item.objects.count() == 0

    def test_reaching_it_with_nothing_staged_does_not_raise(self, client, db):
        response = client.get(reverse("literature:item-import-preview"))
        assert response.status_code == 200

    def test_the_session_holds_the_staged_token_and_format(self, client, db):
        self._submit(client)
        assert client.session["literature_import_token"]
        assert client.session["literature_import_format"] == "bibtex"

    def test_the_preview_page_does_not_contain_the_token(self, client, db):
        self._submit(client)
        token = client.session["literature_import_token"]
        content = client.get(reverse("literature:item-import-preview")).content.decode()
        assert token not in content

    def test_a_file_the_chosen_format_cannot_read_previews_as_a_failure(
        self, client, db
    ):
        upload = SimpleUploadedFile("wrong-format.bib", RIS_ONE_GOOD_ENTRY.encode())
        client.post(
            reverse("literature:item-import"), {"format": "bibtex", "file": upload}
        )
        response = client.get(reverse("literature:item-import-preview"))
        report = response.context["report"]
        assert report.failed == 1
        assert report.created == 0

    def test_submitting_to_the_preview_address_is_refused_not_a_server_error(
        self, client, db
    ):
        # Nothing on the page submits here — confirm and restart each have
        # their own address — so a submission is a refusal, not a crash.
        self._submit(client)
        response = client.post(reverse("literature:item-import-preview"), {})
        assert response.status_code == 405


class TestItemImportRestart:
    def _submit(self, client, filename="publication.bib", format_name="bibtex"):
        with (DATA_DIR / filename).open("rb") as handle:
            upload = SimpleUploadedFile(filename, handle.read())
        return client.post(
            reverse("literature:item-import"), {"format": format_name, "file": upload}
        )

    def test_restarting_discards_the_staged_file_and_lands_on_an_empty_form(
        self, client, db
    ):
        self._submit(client)
        token = client.session["literature_import_token"]
        response = client.post(reverse("literature:item-import-restart"))
        assert response.status_code == 302
        assert response.url == reverse("literature:item-import")
        assert StagedUpload().open(token) is None
        assert "literature_import_token" not in client.session

    def test_restarting_with_nothing_staged_still_lands_on_the_empty_form(
        self, client, db
    ):
        response = client.post(reverse("literature:item-import-restart"))
        assert response.status_code == 302
        assert response.url == reverse("literature:item-import")


class TestItemImportConfirm:
    def _preview(self, client, filename="publication.bib", format_name="bibtex"):
        with (DATA_DIR / filename).open("rb") as handle:
            upload = SimpleUploadedFile(filename, handle.read())
        client.post(
            reverse("literature:item-import"), {"format": format_name, "file": upload}
        )
        return client.get(reverse("literature:item-import-preview"))

    def _preview_bytes(self, client, content, filename, format_name):
        upload = SimpleUploadedFile(filename, content)
        client.post(
            reverse("literature:item-import"), {"format": format_name, "file": upload}
        )
        return client.get(reverse("literature:item-import-preview"))

    def _confirm_fields(self, preview):
        """What the preview page's own confirm control posts back."""
        content = preview.content.decode()
        confirm = content[content.index(reverse("literature:item-import-confirm")) :]
        return dict(re.findall(r'name="(preview)"[^>]*value="([^"]*)"', confirm))

    def test_confirming_redirects_to_the_catalogue(self, client, db):
        preview = self._preview(client)
        response = client.post(
            reverse("literature:item-import-confirm"), self._confirm_fields(preview)
        )
        assert response.status_code == 302
        assert response.url == reverse("literature:item-list")

    def test_confirming_imports_the_staged_file_and_matches_the_preview(
        self, client, db
    ):
        preview = self._preview(client)
        client.post(
            reverse("literature:item-import-confirm"), self._confirm_fields(preview)
        )
        assert Item.objects.filter(citation_key="10.1093/gji/ggz376").exists()
        assert Item.objects.count() == preview.context["report"].created

    def test_confirming_leaves_one_success_message(self, client, db):
        preview = self._preview(client)
        response = client.post(
            reverse("literature:item-import-confirm"),
            self._confirm_fields(preview),
            follow=True,
        )
        assert [m.level for m in get_messages(response.wsgi_request)] == [
            messages.SUCCESS
        ]

    def test_following_the_redirect_consumes_the_message(self, client, db):
        preview = self._preview(client)
        client.post(
            reverse("literature:item-import-confirm"),
            self._confirm_fields(preview),
            follow=True,
        )
        second_visit = client.get(reverse("literature:item-list"))
        assert list(get_messages(second_visit.wsgi_request)) == []

    def test_the_reader_is_not_asked_for_the_file_again(self, client, db):
        preview = self._preview(client)
        # No file and no format: what the confirm control posts back names
        # only which preview the page was showing, which reaches nothing on
        # its own.
        fields = self._confirm_fields(preview)
        assert set(fields) == {"preview"}
        client.post(reverse("literature:item-import-confirm"), fields)
        assert Item.objects.count() == 1

    def test_the_staged_file_is_gone_afterwards(self, client, db):
        preview = self._preview(client)
        token = client.session["literature_import_token"]
        client.post(
            reverse("literature:item-import-confirm"), self._confirm_fields(preview)
        )
        assert StagedUpload().open(token) is None

    def test_a_confirmation_from_a_session_that_staged_nothing_imports_nothing(
        self, client, db
    ):
        response = client.post(reverse("literature:item-import-confirm"), follow=True)
        assert response.status_code == 200
        assert Item.objects.count() == 0

    def test_a_confirmation_from_a_different_session_imports_nothing(self, client, db):
        # A file staged by one session is not reachable through another.
        self._preview(client)
        other_client = Client()
        response = other_client.post(
            reverse("literature:item-import-confirm"), follow=True
        )
        assert response.status_code == 200
        assert Item.objects.count() == 0

    def test_a_confirmation_whose_staged_file_has_been_swept_imports_nothing(
        self, client, db
    ):
        self._preview(client)
        token = client.session["literature_import_token"]
        # Simulate a sweep having already removed it, without waiting on
        # the retention window StagedUpload.sweep() itself is tested against
        # (tests/test_ui/test_staging.py) — the confirm view's own job is to
        # cope with the file already being gone, however that happened.
        StagedUpload().discard(token)

        response = client.post(reverse("literature:item-import-confirm"), follow=True)
        assert response.status_code == 200
        assert Item.objects.count() == 0

    def test_confirming_a_superseded_preview_imports_nothing(self, client, db):
        # Two previews from one session — a second tab, or going back and
        # submitting again. The first tab still shows the first preview and
        # its confirm control. Following it must not import the second file:
        # what commits is what was previewed, or nothing.
        stale = self._preview(client)
        self._preview_bytes(client, RIS_ONE_GOOD_ENTRY.encode(), "second.ris", "ris")

        response = client.post(
            reverse("literature:item-import-confirm"),
            self._confirm_fields(stale),
            follow=True,
        )

        assert response.status_code == 200
        assert Item.objects.count() == 0

    def test_a_superseded_previews_file_is_not_left_staged(self, client, db):
        # The reader can no longer reach it, so nothing should be holding it
        # on disk for the retention window.
        self._preview(client)
        superseded = client.session["literature_import_token"]
        self._preview_bytes(client, RIS_ONE_GOOD_ENTRY.encode(), "second.ris", "ris")
        assert StagedUpload().open(superseded) is None

    def test_a_second_confirmation_of_the_same_token_imports_nothing(self, client, db):
        preview = self._preview(client)
        fields = self._confirm_fields(preview)
        client.post(reverse("literature:item-import-confirm"), fields)
        assert Item.objects.count() == 1
        client.post(reverse("literature:item-import-confirm"), fields, follow=True)
        assert Item.objects.count() == 1


class TestItemImportSkipPreview:
    def test_ticking_the_skip_control_imports_in_one_step(self, client, db):
        with (DATA_DIR / "publication.bib").open("rb") as handle:
            upload = SimpleUploadedFile("publication.bib", handle.read())
        response = client.post(
            reverse("literature:item-import"),
            {"format": "bibtex", "file": upload, "skip_preview": "on"},
        )
        assert response.status_code == 200
        assert Item.objects.filter(citation_key="10.1093/gji/ggz376").exists()

    def test_the_report_carries_no_confirm_control(self, client, db):
        with (DATA_DIR / "publication.bib").open("rb") as handle:
            upload = SimpleUploadedFile("publication.bib", handle.read())
        response = client.post(
            reverse("literature:item-import"),
            {"format": "bibtex", "file": upload, "skip_preview": "on"},
        )
        content = response.content.decode()
        # The upload form the page carries above its results is a different
        # form, submitting a new file to a new run.
        assert f'action="{reverse("literature:item-import-confirm")}"' not in content

    def test_skipping_the_preview_stages_nothing(self, client, db):
        with (DATA_DIR / "publication.bib").open("rb") as handle:
            upload = SimpleUploadedFile("publication.bib", handle.read())
        client.post(
            reverse("literature:item-import"),
            {"format": "bibtex", "file": upload, "skip_preview": "on"},
        )
        assert "literature_import_token" not in client.session

    def test_importing_in_one_step_discards_a_file_staged_before_it(self, client, db):
        # An earlier preview left a file staged. Importing something else in
        # one step supersedes it just as previewing again would: the reader
        # cannot reach that preview any more, so nothing should still hold
        # its file — least of all a confirm that would import it a second
        # time on top of what they have just done.
        staged = SimpleUploadedFile(
            "staged.bib",
            b"@book{StagedEarlier2020, title={Staged Earlier}, year={2020}}",
        )
        client.post(
            reverse("literature:item-import"), {"format": "bibtex", "file": staged}
        )
        preview_id = (
            client.get(reverse("literature:item-import-preview"))
            .context["confirm_form"]["preview"]
            .value()
        )

        one_step = SimpleUploadedFile(
            "one-step.bib",
            b"@book{OneStepLater2021, title={One Step Later}, year={2021}}",
        )
        client.post(
            reverse("literature:item-import"),
            {"format": "bibtex", "file": one_step, "skip_preview": "on"},
        )
        after_one_step = set(Item.objects.values_list("citation_key", flat=True))
        assert after_one_step == {"OneStepLater2021"}
        assert "literature_import_token" not in client.session

        client.post(reverse("literature:item-import-confirm"), {"preview": preview_id})
        assert (
            set(Item.objects.values_list("citation_key", flat=True)) == after_one_step
        )


class TestItemUpdateView:
    def test_saving_an_unchanged_form_leaves_every_stored_field_identical(
        self, client, db
    ):
        # The whole no-loss guarantee, and the most valuable test in
        # the feature. A value in every scalar field the form carries, plus
        # the two JSON fields it never carries (categories, custom),
        # must survive an unchanged round trip through the rendered edit
        # form. created/modified are auto_now_add/auto_now and change on
        # every save by design, so they are excluded on purpose,
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
                if hasattr(field, "attname")
                and not field.primary_key
                and field.name not in ("created", "modified")
            }

        before = snapshot()

        data = update_page_post_data(client, item)
        response = client.post(
            reverse("literature:item-update", kwargs={"pk": item.pk}), data
        )
        assert response.status_code == 302

        item.refresh_from_db()
        assert snapshot() == before

    def test_a_populated_field_outside_the_types_own_groups_is_forced_visible(
        self, client, db
    ):
        # "legal" is not one of ARTICLE_JOURNAL's own groups
        # (container, numbering), so a value already stored in it has to be
        # forced visible rather than left behind the type guard.
        assert "legal" not in FieldGroups.TYPE_GROUPS[ItemType.ARTICLE_JOURNAL]
        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL, authority="Held Authority")
        response = client.get(reverse("literature:item-update", kwargs={"pk": item.pk}))
        content = response.content.decode()
        assert 'id="id_authority"' in content
        forced_groups = json.loads(response.context["forced_groups_json"])
        assert "legal" in forced_groups

    def test_changing_the_item_type_on_post_retains_values_in_groups_the_new_type_does_not_use(
        self, client, db
    ):
        # WEBPAGE's own groups are just "container"; "legal" is not
        # among them, so authority must still round-trip unchanged.
        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL, authority="Held Authority")
        data = update_page_post_data(client, item, type=ItemType.WEBPAGE)
        client.post(reverse("literature:item-update", kwargs={"pk": item.pk}), data)
        item.refresh_from_db()
        assert item.type == ItemType.WEBPAGE
        assert item.authority == "Held Authority"

    def test_the_type_select_renders_the_items_stored_type_as_selected(
        self, client, db
    ):
        # The failure the select's x-init prevents: without it x-model would
        # deselect the stored type at Alpine's own initialisation, but the
        # server-rendered HTML this test reads is unaffected by that bug —
        # this asserts the bound ModelForm renders the right initial option
        # regardless.
        item = ItemFactory(type=ItemType.BOOK)
        content = client.get(
            reverse("literature:item-update", kwargs={"pk": item.pk})
        ).content.decode()
        assert re.search(
            rf'<option value="{re.escape(item.type)}"[^>]*selected', content
        )

    def test_saving_through_the_form_leaves_contributor_date_and_identifier_rows_unchanged(
        self, client, populated_item
    ):
        # ItemForm carries none of these; the guarantee is that a
        # save through it never touches them at all.
        item = populated_item

        def rows():
            return (
                [
                    (row.pk, row.name_id, row.role, row.order)
                    for row in item.item_names.all()
                ],
                [
                    (row.pk, row.date_type, row.begin, row.end)
                    for row in item.item_dates.all()
                ],
                [(row.pk, row.type, row.value) for row in item.item_identifiers.all()],
            )

        before = rows()
        data = update_page_post_data(client, item)
        client.post(reverse("literature:item-update", kwargs={"pk": item.pk}), data)
        assert rows() == before


class TestItemDetailView:
    def test_carried_fields_appear_and_absent_fields_do_not(self, client, db):
        item = ItemFactory(title="Full Record", volume="12", issue="")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        volume_label = item._meta.get_field("volume").verbose_name
        issue_label = item._meta.get_field("issue").verbose_name
        assert f">{volume_label}</h6>" in content
        assert "12" in content
        # issue is blank on this item — its label must not appear at all.
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
        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = client.get(
            reverse("literature:item-detail", kwargs={"pk": item.pk})
        ).content.decode()
        assert str(ItemType.ARTICLE_JOURNAL.label) in content
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
        ItemDateFactory(
            item=item,
            date_type=DateType.EVENT_DATE,
            begin="2020-01-01",
            end="2020-01-05",
        )
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        assert "2020-01-01" in content
        assert "2020-01-05" in content

    def test_identifiers_show_their_type_including_types_the_store_does_not_recognise(
        self, client, db
    ):
        item = ItemFactory()
        ItemIdentifierFactory(item=item, type="ARK", value="ark:/12345/x")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        assert "ARK" in content
        assert "ark:/12345/x" in content

    def test_identifier_addressing_a_resolvable_location_is_followable(
        self, client, db
    ):
        item = ItemFactory()
        ItemIdentifierFactory(item=item, type="URL", value="https://example.org/paper")
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        assert 'href="https://example.org/paper"' in response.content.decode()

    def test_identifier_carrying_a_script_scheme_is_never_followable(self, client, db):
        # An unrecognised identifier type skips format validation entirely,
        # so the value reaching this page is arbitrary stored text.
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
        # namespaced urls.py; resolve_crud_url is what prevents that.
        item = ItemFactory()
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        catalogue_url = reverse("literature:item-list")
        assert f'href="{catalogue_url}"' in content

    def test_contributor_names_link_to_their_page(self, client, db):
        # The only reachability path into the contributor page
        # is a link from here.
        item = ItemFactory()
        item_name = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        contributor_url = reverse(
            "literature:contributor-detail", kwargs={"pk": item_name.name.pk}
        )
        assert f'href="{contributor_url}"' in content

    def test_the_edit_action_renders_and_points_at_the_update_page(self, client, db):
        # Directory alone renders nothing without show_update_action.
        item = ItemFactory()
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        update_url = reverse("literature:item-update", kwargs={"pk": item.pk})
        assert f'href="{update_url}"' in content

    def test_the_delete_action_renders_and_points_at_the_delete_page(self, client, db):
        item = ItemFactory()
        response = client.get(reverse("literature:item-detail", kwargs={"pk": item.pk}))
        content = response.content.decode()
        delete_url = reverse("literature:item-delete", kwargs={"pk": item.pk})
        assert f'href="{delete_url}"' in content


class TestItemDeleteView:
    def test_get_renders_a_confirmation_naming_the_reference_and_deletes_nothing(
        self, client, db
    ):
        item = ItemFactory(title="A Reference Marked For Removal")
        response = client.get(reverse("literature:item-delete", kwargs={"pk": item.pk}))
        assert response.status_code == 200
        assert "A Reference Marked For Removal" in response.content.decode()
        assert Item.objects.filter(pk=item.pk).exists()

    def test_declining_returns_to_the_references_own_page_and_the_item_still_exists(
        self, client, db
    ):
        # MVPDeleteView.get_back_url() falls back to
        # the catalogue list, and the detail page's own delete link carries no
        # ?back (only the update page's does), so declining would otherwise
        # strand the reader on the catalogue instead of the reference they
        # chose not to remove.
        item = ItemFactory()
        response = client.get(reverse("literature:item-delete", kwargs={"pk": item.pk}))
        detail_url = reverse("literature:item-detail", kwargs={"pk": item.pk})
        assert response.context["back_url"] == detail_url
        assert f'href="{detail_url}"' in response.content.decode()
        assert Item.objects.filter(pk=item.pk).exists()

    def test_an_inherited_back_parameter_is_honoured_ahead_of_the_reference_page(
        self, client, db
    ):
        # get_back_url() honours a validated ?back first — only once
        # that is absent does it fall through to the reference's own page.
        item = ItemFactory()
        response = client.get(
            reverse("literature:item-delete", kwargs={"pk": item.pk}),
            {"back": "/catalogue/"},
        )
        assert response.context["back_url"] == "/catalogue/"

    def test_post_removes_the_item_with_its_names_dates_and_identifiers_and_redirects_to_the_catalogue(
        self, client, populated_item
    ):
        item = populated_item
        item_name_pk = item.item_names.get().pk
        item_date_pk = item.item_dates.get().pk
        item_identifier_pk = item.item_identifiers.get().pk

        response = client.post(
            reverse("literature:item-delete", kwargs={"pk": item.pk})
        )

        assert response.status_code == 302
        assert response.url == reverse("literature:item-list")
        assert not Item.objects.filter(pk=item.pk).exists()
        assert not ItemName.objects.filter(pk=item_name_pk).exists()
        assert not ItemDate.objects.filter(pk=item_date_pk).exists()
        assert not ItemIdentifier.objects.filter(pk=item_identifier_pk).exists()

    def test_names_survive_deletion_whether_or_not_credited_elsewhere(self, client, db):
        # Nothing points from Item to Name directly, only ItemName
        # rows cascade, so this is already true of the model; the test
        # asserts the guarantee rather than any code that implements it.
        # Covers both a contributor still credited elsewhere
        # and one left credited on nothing, whose own page still has to
        # render.
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

        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": solo_contributor.pk})
        )
        assert response.status_code == 200

    def test_unknown_pk_is_a_404(self, client, db):
        response = client.get(reverse("literature:item-delete", kwargs={"pk": 999999}))
        assert response.status_code == 404


class TestContributorDetailView:
    def test_renders_neither_a_search_box_nor_a_filter_button(self, client, db):
        # ItemListView's own base class change
        # would otherwise hand this page a search box and four filters,
        # since it used to subclass ItemListView directly.
        contributor = NameFactory()
        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert 'name="q"' not in content
        assert "filterModal" not in content

    def test_credits_listed_with_roles(self, client, db):
        contributor = NameFactory()
        item = ItemFactory(title="Credited Work")
        ItemNameFactory(item=item, name=contributor, role=NameRole.EDITOR)
        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        )
        content = response.content.decode()
        assert "Credited Work" in content
        assert str(NameRole.EDITOR.label) in content

    def test_credit_row_carries_what_a_catalogue_row_carries(self, client, db):
        # A credit row carries what a catalogue row does, so the row shows
        # the item's own contributors as well as the role this contributor
        # held on it — the roles are additional, not a replacement.
        contributor = NameFactory(family="Rowe", given="A")
        coauthor = NameFactory(family="Peralta", given="B")
        item = ItemFactory(title="Jointly Written Work", citation_key="rowe2021joint")
        ItemNameFactory(item=item, name=contributor, role=NameRole.EDITOR)
        ItemNameFactory(item=item, name=coauthor, role=NameRole.AUTHOR)
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2021")

        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        )
        content = response.content.decode()

        assert "Jointly Written Work" in content
        assert str(coauthor) in content
        assert str(NameRole.AUTHOR.label) in content
        assert "rowe2021joint" in content
        assert "2021" in content
        assert str(item.get_type_display()) in content

    def test_breadcrumb_links_to_the_catalogue_by_its_resolved_url(self, client, db):
        # The model-derived crud_views entry would be 'name-list', a route
        # this app does not have.
        contributor = NameFactory()
        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        )
        assert f'href="{reverse("literature:item-list")}"' in response.content.decode()

    def test_item_held_under_two_roles_appears_once_carrying_both(self, client, db):
        contributor = NameFactory()
        item = ItemFactory(title="Dual Role Work")
        ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=contributor, role=NameRole.EDITOR)
        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        )
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
        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        )
        content = response.content.decode()
        assert content.index("Newer Credit") < content.index("Older Credit")

    def test_page_holds_no_more_than_paginate_by_items_whatever_the_credit_count(
        self, client, db
    ):
        contributor = NameFactory()
        for _ in range(30):
            item = ItemFactory()
            ItemNameFactory(item=item, name=contributor, role=NameRole.AUTHOR)
        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        )
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
        contributor = NameFactory(
            family="", given="", literal="Some Research Institute"
        )
        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
        )
        assert response.status_code == 200
        assert "Some Research Institute" in response.content.decode()

    def test_missing_contributor_is_a_404(self, client, db):
        response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": 999999})
        )
        assert response.status_code == 404

    def test_two_records_with_identical_names_keep_separate_pages(self, client, db):
        first = NameFactory(family="Smith", given="J")
        second = NameFactory(family="Smith", given="J")
        first_item = ItemFactory(title="First Smiths Work")
        second_item = ItemFactory(title="Second Smiths Work")
        ItemNameFactory(item=first_item, name=first, role=NameRole.AUTHOR)
        ItemNameFactory(item=second_item, name=second, role=NameRole.AUTHOR)

        first_response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": first.pk})
        )
        first_content = first_response.content.decode()
        assert "First Smiths Work" in first_content
        assert "Second Smiths Work" not in first_content

        second_response = client.get(
            reverse("literature:contributor-detail", kwargs={"pk": second.pk})
        )
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
            response = client.get(
                reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
            )
        assert response.status_code == 200

        add_credits(15)
        with CaptureQueriesContext(connection) as large_credit_list:
            response = client.get(
                reverse("literature:contributor-detail", kwargs={"pk": contributor.pk})
            )
        assert response.status_code == 200

        assert len(large_credit_list.captured_queries) == len(
            small_credit_list.captured_queries
        )


class TestCSLRoundTrip:
    def test_an_item_entered_through_the_create_view_round_trips_through_csl_json(
        self, client, db
    ):
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
    # A malformed attribute leaves the response text unchanged, so only parsing it the
    # way a browser does catches a truncated scope.

    def test_the_create_pages_scope_element_carries_exactly_one_attribute(
        self, client, db
    ):
        parser = alpine_scope(
            client.get(reverse("literature:item-create")).content.decode()
        )
        assert parser.attr_count == 1, (
            "the scope element gained attributes, which means the JSON broke out of x-init"
        )

    def test_the_create_pages_type_map_parses_and_covers_every_item_type(
        self, client, db
    ):
        parser = alpine_scope(
            client.get(reverse("literature:item-create")).content.decode()
        )
        assigned = parser.x_init.split("form.typeGroups = ", 1)[1].rsplit(";", 1)[0]
        assert json.loads(assigned).keys() == {t.value for t in ItemType}

    def test_the_edit_pages_forced_groups_parse(self, client, db):
        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL, scale="1:50000")
        parser = alpine_scope(
            client.get(
                reverse("literature:item-update", kwargs={"pk": item.pk})
            ).content.decode()
        )
        assert parser.attr_count == 1
        assigned = parser.x_init.split("form.forcedGroups = ", 1)[1].strip()
        assert "physical" in json.loads(assigned), (
            "a populated off-type group must reach the browser as forced-visible"
        )


class TestSurroundingWhitespaceSurvivesACorrection:
    # CharField strips by default and the CSL JSON import does not, so stored edges are
    # reachable and an unchanged save must keep them.

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

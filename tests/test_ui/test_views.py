"""Tests for ``literature/ui/views.py``.

Article XIV: one source module, one test module — the per-view split is
expressed with classes, one per story (``TestItemListView`` for US-1,
``TestItemDetailView`` for US-2, ``TestContributorDetailView`` for US-4).
"""

import json
import re

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

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


def update_page_post_data(client, item, **overrides):
    """Build a POST body from the rendered edit page's own bound form.

    Same technique as ``create_page_post_data`` (T009): every field starts at
    what the bound ``ItemForm`` actually initialises it to from the stored
    instance, and whatever the Save button's own ``name``/``value`` pair is
    (there is none — item_form.html's block carries neither) is carried
    exactly as the page emits it. A hand-typed dict would miss both, and
    would pass a round-trip assertion even against a view that dropped a
    field the rendered page actually posts.
    """
    response = client.get(reverse("literature:item-update", kwargs={"pk": item.pk}))
    form = response.context["form"]
    data = {name: (form[name].value() or "") for name in form.fields}
    content = response.content.decode()
    submit_button = re.search(r'<button[^>]*type="submit"[^>]*name="([^"]+)"[^>]*value="([^"]+)"', content)
    if submit_button:
        data[submit_button.group(1)] = submit_button.group(2)
    data.update(overrides)
    return data


def create_page_post_data(client, **overrides):
    """Build a POST body from the rendered create page's own form.

    Every field starts at what an unbound ``ItemForm`` actually initialises
    it to, and whatever the Save button's own ``name``/``value`` pair is
    (T011 renders one with neither) is carried exactly as the page emits it
    — never assembled from a bare hand-typed dict. A bare dict omits
    ``default_next`` regardless of what the rendered page's button does, so
    it would pass a redirect-target assertion even against a view whose
    ``{% block actions %}`` reverted to the stock button that posts
    ``default_next=list`` (plan.md D-3).
    """
    response = client.get(reverse("literature:item-create"))
    form = response.context["form"]
    data = {name: (form[name].value() or "") for name in form.fields}
    content = response.content.decode()
    submit_button = re.search(r'<button[^>]*type="submit"[^>]*name="([^"]+)"[^>]*value="([^"]+)"', content)
    if submit_button:
        data[submit_button.group(1)] = submit_button.group(2)
    data.update(overrides)
    return data


class TestItemListView:
    """The catalogue list — FR-012 through FR-018."""

    def test_lists_items_most_recently_added_first(self, client, db):
        older = ItemFactory(title="Older Reference")
        newer = ItemFactory(title="Newer Reference")
        response = client.get(reverse("literature:item-list"))
        content = response.content.decode()
        assert content.index("Newer Reference") < content.index("Older Reference")

    def test_page_holds_no_more_than_paginate_by_items_whatever_the_catalogue_size(self, client, db):
        ItemFactory.create_batch(30)
        response = client.get(reverse("literature:item-list"))
        assert len(response.context["object_list"]) == 24

    def test_pagination_states_position_and_offers_navigation(self, client, db):
        ItemFactory.create_batch(30)
        response = client.get(reverse("literature:item-list"))
        content = response.content.decode()
        assert "1-24 of 30" in content
        assert 'href="?page=2"' in content

    def test_page_number_past_the_end_is_a_404(self, client, db):
        ItemFactory()
        response = client.get(reverse("literature:item-list"), {"page": 999})
        assert response.status_code == 404

    def test_empty_catalogue_renders_the_stated_empty_result(self, client, db):
        # Assert this view's own wording, not merely the presence of an empty
        # state — django-mvp's default heading ("There's nothing here yet")
        # would satisfy a looser match and hide an unwired empty state.
        response = client.get(reverse("literature:item-list"))
        assert response.status_code == 200
        content = response.content.decode()
        assert "Nothing in the catalogue yet" in content
        assert "References imported or created will appear here." in content

    def test_each_row_links_to_that_items_page(self, client, db):
        item = ItemFactory(title="A Linked Reference")
        response = client.get(reverse("literature:item-list"))
        content = response.content.decode()
        assert reverse("literature:item-detail", kwargs={"pk": item.pk}) in content

    def test_item_with_no_title_shows_its_citation_key(self, client, db):
        ItemFactory(title="", citation_key="FallbackKey2026")
        response = client.get(reverse("literature:item-list"))
        content = response.content.decode()
        assert "FallbackKey2026" in content

    def test_row_carries_contributors_issued_date_and_citation_key(self, client, db):
        item = ItemFactory(title="With Everything", citation_key="Everything2026")
        item_name = ItemNameFactory(item=item, role=NameRole.AUTHOR)
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        response = client.get(reverse("literature:item-list"))
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
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "2019" in content
        assert "2021" in content

    def test_row_falls_back_to_a_free_text_date(self, client, db):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=None, literal="in press")
        assert "in press" in client.get(reverse("literature:item-list")).content.decode()

    def test_query_count_does_not_grow_with_row_count(self, client, db):
        def add_items(n):
            for _ in range(n):
                item = ItemFactory()
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

    def test_the_add_link_renders_and_points_at_the_create_page(self, client, db):
        # directory = ["create"] alone renders nothing without
        # show_create_action set (plan.md D-6) — this is the entry point
        # US-1's acceptance scenario 1 starts from.
        content = client.get(reverse("literature:item-list")).content.decode()
        assert f'href="{reverse("literature:item-create")}"' in content


class TestCatalogueListReadability:
    """Issue #65 — what the catalogue list and its rows say at a glance.

    Nothing here changes what the page reports, only how readably it reports
    it, so every test asserts on presentation over data the existing
    ``TestItemListView`` cases already prove is present.
    """

    def test_the_page_is_titled_for_what_it_holds_not_for_the_model(self, client, db):
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "Publications" in content
        assert "Items" not in content

    def test_the_position_line_names_the_collection_the_same_way_the_heading_does(self, client, db):
        # django-mvp writes this line from the model's verbose_name_plural, so
        # retitling the page alone left it reading "Showing 1-24 of 28 items"
        # directly under a heading that said Publications.
        ItemFactory.create_batch(30)
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "of 30 publications" in content
        assert "of 30 items" not in content

    def test_the_model_keeps_its_own_name(self, db):
        # The heading is the view's to choose. Renaming the model to reach it
        # would rename it in the admin, in every error message and in the
        # migration state, for a word on one page.
        assert str(Item._meta.verbose_name_plural) == "items"

    def test_the_item_type_badge_carries_the_primary_colour(self, client, db):
        ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        content = client.get(reverse("literature:item-list")).content.decode()
        assert re.search(r'class="badge badge-primary[^"]*">\s*Journal Article\s*<', content)

    def test_contributor_names_link_to_their_page(self, client, db):
        # The reference page has carried this link since FR-022; the row showed
        # the same names as plain text, so a reader could not tell from the
        # catalogue that a contributor had a page at all.
        item_name = ItemNameFactory(role=NameRole.AUTHOR)
        content = client.get(reverse("literature:item-list")).content.decode()
        contributor_url = reverse("literature:contributor-detail", kwargs={"pk": item_name.name.pk})
        assert f'href="{contributor_url}"' in content

    def test_a_contributor_link_underlines_on_hover(self, client, db):
        item_name = ItemNameFactory(role=NameRole.AUTHOR)
        content = client.get(reverse("literature:item-list")).content.decode()
        contributor_url = reverse("literature:contributor-detail", kwargs={"pk": item_name.name.pk})
        assert "link-hover" in anchor_tag(content, contributor_url)

    def test_the_title_link_underlines_on_hover(self, client, db):
        item = ItemFactory(title="A Followable Title")
        content = client.get(reverse("literature:item-list")).content.decode()
        item_url = reverse("literature:item-detail", kwargs={"pk": item.pk})
        assert "link-hover" in anchor_tag(content, item_url)

    def test_a_role_heading_pluralises_with_the_names_under_it(self, client, db):
        item = ItemFactory()
        for _ in range(3):
            ItemNameFactory(item=item, role=NameRole.AUTHOR)
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "Authors:" in content
        assert "Author:" not in content

    def test_a_role_heading_stays_singular_for_one_name(self, client, db):
        ItemNameFactory(role=NameRole.AUTHOR)
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "Author:" in content

    def test_the_citation_key_is_labelled(self, client, db):
        # Given a title, so the row's fallback does not also print the key
        # (the fallback is the row's heading, and is not what this labels).
        ItemFactory(title="A Titled Reference", citation_key="Labelled2026")
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "Cite key" in content
        assert content.index("Cite key") < content.index("Labelled2026")

    def test_a_row_shows_a_snippet_of_the_abstract(self, client, db):
        ItemFactory(abstract="Sediment cores record the drainage history of the basin.")
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "Sediment cores record the drainage history of the basin." in content

    def test_a_long_abstract_is_cut_to_a_snippet(self, client, db):
        ItemFactory(abstract=" ".join(f"word{n}" for n in range(60)))
        content = client.get(reverse("literature:item-list")).content.decode()
        assert "word0" in content
        assert "word59" not in content

    def test_a_row_carrying_no_abstract_leaves_no_empty_paragraph_behind(self, client, db):
        # The snippet is a paragraph; rendered unconditionally it would leave an
        # empty one on every row of a catalogue imported without abstracts,
        # which is most of them.
        item = ItemFactory(abstract="")
        content = client.get(reverse("literature:item-list")).content.decode()
        assert re.search(r"<p[^>]*>\s*</p>", content) is None
        assert item.citation_key in content


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

        # "id" (citation_key) is expected to differ: from_csl_json dedupes
        # against the original, which is still in the store — the guarantee
        # is that every other CSL key round-trips unchanged.
        assert round_tripped_csl == {**original_csl, "id": round_tripped_csl["id"]}

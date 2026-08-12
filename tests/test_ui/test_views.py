"""Tests for ``literature/ui/views.py``.

Article XIV: one source module, one test module — the per-view split is
expressed with classes, one per story (``TestItemListView`` for US-1,
``TestItemDetailView`` for US-2, ``TestContributorDetailView`` for US-4).
"""

import re

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from literature.choices import DateType, ItemType, NameRole
from literature.models import Item
from tests.factories import ItemDateFactory, ItemFactory, ItemIdentifierFactory, ItemNameFactory, NameFactory


def anchor_tag(content, href):
    """The opening ``<a>`` tag addressing ``href``, so a test can assert on the
    classes it carries rather than only on the presence of the URL."""
    match = re.search(rf"<a\b[^>]*href=\"{re.escape(href)}\"[^>]*>", content)
    assert match, f"no anchor addressing {href}"
    return match.group(0)


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

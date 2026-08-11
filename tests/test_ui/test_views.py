"""Tests for ``literature/ui/views.py``.

Article XIV: one source module, one test module — the per-view split is
expressed with classes, one per story (``TestItemListView`` for US-1,
``TestItemDetailView`` for US-2, ``TestContributorDetailView`` for US-4).
"""

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from literature.choices import DateType, NameRole
from tests.factories import ItemDateFactory, ItemFactory, ItemNameFactory


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

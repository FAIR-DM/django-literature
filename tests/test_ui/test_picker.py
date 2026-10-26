"""Tests for ``literature/ui/picker.py``."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from literature.choices import DateType, NameRole
from literature.models import Item
from literature.ui.picker import item_label
from tests.factories import (
    ItemDateFactory,
    ItemFactory,
    ItemNameFactory,
    NameFactory,
)


def prefetched(*items):
    """Return the given items as the picker's own queries load them."""
    return list(
        Item.objects.filter(pk__in=[item.pk for item in items])
        .order_by("pk")
        .prefetch_related("item_dates", "item_names__name")
    )


@pytest.mark.django_db
class TestItemLabel:
    def test_label_shows_title_year_and_first_author(self):
        item = ItemFactory(title="Deep Time")
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        ItemNameFactory(item=item, name=NameFactory(family="Rowe"))

        (loaded,) = prefetched(item)
        label = item_label(loaded)

        assert "Deep Time" in label
        assert "2020" in label
        assert "Rowe" in label

    def test_label_omits_the_year_when_there_is_none(self):
        item = ItemFactory(title="Deep Time")
        ItemNameFactory(item=item, name=NameFactory(family="Rowe"))

        (loaded,) = prefetched(item)
        label = item_label(loaded)

        assert "Deep Time" in label
        assert "Rowe" in label
        assert "None" not in label
        assert "()" not in label

    def test_label_omits_the_author_when_there_are_no_contributors(self):
        item = ItemFactory(title="Deep Time")
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")

        (loaded,) = prefetched(item)

        assert item_label(loaded) == item_label(Item.objects.get(pk=item.pk))
        assert "Deep Time" in item_label(loaded)
        assert not item_label(loaded).rstrip().endswith(",")

    def test_label_falls_back_to_the_citation_key_without_a_title(self):
        item = ItemFactory(title="", citation_key="rowe2020")

        (loaded,) = prefetched(item)

        assert "rowe2020" in item_label(loaded)

    def test_label_shows_an_organisations_literal_name(self):
        item = ItemFactory(title="Annual Report")
        organisation = NameFactory(
            family="", given="", literal="World Health Organization"
        )
        ItemNameFactory(item=item, name=organisation)

        (loaded,) = prefetched(item)

        assert "World Health Organization" in item_label(loaded)

    def test_label_prefers_the_first_author_over_an_editor_credited_first(self):
        item = ItemFactory(title="Collected Essays")
        ItemNameFactory(
            item=item, name=NameFactory(family="Editorson"), role=NameRole.EDITOR
        )
        ItemNameFactory(
            item=item, name=NameFactory(family="Authorson"), role=NameRole.AUTHOR
        )

        (loaded,) = prefetched(item)
        label = item_label(loaded)

        assert "Authorson" in label
        assert "Editorson" not in label

    def test_label_takes_the_lowest_order_among_authors(self):
        item = ItemFactory(title="Collected Essays")
        ItemNameFactory(
            item=item, name=NameFactory(family="First"), role=NameRole.AUTHOR, order=0
        )
        ItemNameFactory(
            item=item, name=NameFactory(family="Second"), role=NameRole.AUTHOR, order=1
        )

        (loaded,) = prefetched(item)

        assert "First" in item_label(loaded)
        assert "Second" not in item_label(loaded)

    def test_label_names_a_non_author_when_nobody_is_an_author(self):
        item = ItemFactory(title="Collected Essays")
        ItemNameFactory(
            item=item, name=NameFactory(family="Editorson"), role=NameRole.EDITOR
        )

        (loaded,) = prefetched(item)

        assert "Editorson" in item_label(loaded)

    def test_labelling_prefetched_items_issues_no_queries(self):
        items = []
        for number in range(3):
            item = ItemFactory(title=f"Title {number}")
            ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
            ItemNameFactory(item=item)
            items.append(item)
        loaded = prefetched(*items)

        with CaptureQueriesContext(connection) as queries:
            labels = [item_label(item) for item in loaded]

        assert len(labels) == 3
        assert len(queries) == 0

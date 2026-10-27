import datetime

import pytest
from django.core.management import CommandError, call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder

from literature.choices import DateType, IdentifierType, NameRole
from literature.models import Item
from tests.factories import CitationFactory, ItemFactory
from tests.fixtures.legacy_schema import LEGACY_MIGRATIONS, LEGACY_TABLES
from tests.host.models import Citation, ReadingListEntry

PAPER = {
    "id": "pollack1993",
    "type": "article-journal",
    "title": "Heat flow from the Earth's interior",
    "container-title": "Reviews of Geophysics",
    "author": [
        {"family": "Pollack", "given": "Henry N."},
        {"family": "Hurter", "given": "Suzanne J."},
    ],
    "issued": {"date-parts": [[1993, 8]]},
    "DOI": "10.1029/93RG01249",
}


def table_names():
    return set(connection.introspection.table_names())


class TestUpgradeLiterature:
    def test_converts_each_reference_keeping_its_primary_key(self, legacy_item):
        deleted = legacy_item("deleted", type="book", title="Gone")
        legacy_item("first", type="book", title="First")
        old = legacy_item(**PAPER)
        deleted.delete()

        call_command("upgrade_literature")

        item = Item.objects.get(pk=old.pk)
        assert item.citation_key == "pollack1993"
        assert item.title == PAPER["title"]
        assert item.container_title == PAPER["container-title"]
        assert [
            (name.name.family, name.order)
            for name in item.item_names.filter(role=NameRole.AUTHOR).order_by("order")
        ] == [("Pollack", 0), ("Hurter", 1)]
        assert item.item_dates.get(date_type=DateType.ISSUED).begin.date.month == 8
        assert item.item_identifiers.get(type=IdentifierType.DOI).value == PAPER["DOI"]
        assert Item.objects.count() == 2

    def test_keeps_the_rows_citation_key_over_the_jsons(self, legacy_item):
        old = legacy_item("row-key", **{**PAPER, "citation-key": "json-key"})

        call_command("upgrade_literature")

        assert Item.objects.get(pk=old.pk).citation_key == "row-key"

    def test_carries_tags_into_keywords(self, legacy_item, legacy_tag):
        old = legacy_item(**PAPER, keyword="heat flow, geothermics")
        old.keyword.add(legacy_tag("geothermics"), legacy_tag("crust"))

        call_command("upgrade_literature")

        assert Item.objects.get(pk=old.pk).keyword == "heat flow, geothermics, crust"

    def test_keeps_when_each_reference_was_created_and_modified(
        self, legacy_database, legacy_item
    ):
        LiteratureItem = legacy_database.get_model("literature", "LiteratureItem")
        created = datetime.datetime(2024, 3, 1, 9, 30, tzinfo=datetime.UTC)
        modified = datetime.datetime(2025, 6, 2, 14, 0, tzinfo=datetime.UTC)
        old = legacy_item(**PAPER)
        LiteratureItem.objects.filter(pk=old.pk).update(
            created=created, modified=modified
        )

        call_command("upgrade_literature")

        item = Item.objects.get(pk=old.pk)
        assert (item.created, item.modified) == (created, modified)

    def test_leaves_a_host_record_citing_the_same_reference(
        self, legacy_item, legacy_citation
    ):
        old = legacy_item(**PAPER)
        cited = legacy_citation(old.pk)

        call_command("upgrade_literature")

        assert Citation.objects.get(pk=cited.pk).reference.citation_key == "pollack1993"

    def test_points_a_host_foreign_key_at_the_current_table(self, legacy_item):
        legacy_item(**PAPER)

        call_command("upgrade_literature")

        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, Citation._meta.db_table
            )
        assert [
            constraint["foreign_key"]
            for constraint in constraints.values()
            if constraint["columns"] == ["reference_id"] and constraint["foreign_key"]
        ] == [("literature_item", "id")]

    def test_points_a_host_foreign_key_with_a_shortened_name_at_the_current_table(
        self, legacy_item
    ):
        legacy_item(**PAPER)

        call_command("upgrade_literature")

        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, ReadingListEntry._meta.db_table
            )
        assert [
            constraint["foreign_key"]
            for constraint in constraints.values()
            if constraint["columns"] == ["reference_id"] and constraint["foreign_key"]
        ] == [("literature_item", "id")]

    def test_lets_a_host_record_cite_a_reference_added_afterwards(self, legacy_item):
        old = legacy_item(**PAPER)

        call_command("upgrade_literature")
        added = ItemFactory(citation_key="added", type="book")
        CitationFactory(reference=added)

        assert added.pk > old.pk
        assert Citation.objects.get(reference=added).reference_id == added.pk

    def test_records_the_current_migrations_and_drops_the_old_tables(self, legacy_item):
        legacy_item(**PAPER)

        call_command("upgrade_literature")

        applied = MigrationRecorder(connection).applied_migrations()
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes("literature")
        assert executor.migration_plan(leaves) == []
        assert ("literature", LEGACY_MIGRATIONS[-1]) not in applied
        assert table_names().isdisjoint(LEGACY_TABLES)

    def test_changes_nothing_on_a_current_database(self, db):
        ItemFactory(citation_key="current", type="book")

        call_command("upgrade_literature")

        assert list(Item.objects.values_list("citation_key", flat=True)) == ["current"]

    @pytest.mark.parametrize("leftover", ["collection", "supplementary", "file"])
    def test_stops_before_discarding_what_has_no_place(
        self, legacy_item, legacy_collection, leftover
    ):
        old = legacy_item(**PAPER)
        if leftover == "collection":
            old.collections.add(legacy_collection("Reviews"))
        elif leftover == "supplementary":
            old.supplementary.create(file="supplementary/table.csv")
        else:
            old.file = "literature/paper.pdf"
            old.save()

        with pytest.raises(CommandError, match="pollack1993"):
            call_command("upgrade_literature")

        assert "literature_literatureitem" in table_names()
        assert ("literature", LEGACY_MIGRATIONS[-1]) in (
            MigrationRecorder(connection).applied_migrations()
        )

    def test_discards_what_has_no_place_when_told_to(
        self, legacy_item, legacy_collection
    ):
        old = legacy_item(**PAPER)
        old.collections.add(legacy_collection("Reviews"))
        old.supplementary.create(file="supplementary/table.csv")

        call_command("upgrade_literature", discard_unconverted=True)

        assert Item.objects.filter(pk=old.pk).exists()

    def test_changes_nothing_when_a_reference_cannot_be_converted(self, legacy_item):
        legacy_item(**PAPER)
        legacy_item("bad-issn", **{**PAPER, "ISSN": "0000-0001"})

        with pytest.raises(CommandError, match="bad-issn"):
            call_command("upgrade_literature")

        assert "literature_literatureitem" in table_names()
        assert "literature_item" not in table_names()

    def test_reports_a_reference_whose_json_is_malformed(self, legacy_item):
        legacy_item("odd-date", **{**PAPER, "issued": "1993"})

        with pytest.raises(CommandError, match="odd-date"):
            call_command("upgrade_literature")

"""Tests for ``literature/migrations/0004_processor_variables_into_custom.py``."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

BEFORE = [("literature", "0003_alter_item_citation_key")]
AFTER = [("literature", "0004_processor_variables_into_custom")]


def migrate(targets):
    """Migrate the test database to ``targets`` and return the project state there."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.mark.django_db(transaction=True)
class TestProcessorVariablesIntoCustom:
    @pytest.fixture(autouse=True)
    def latest_schema_afterwards(self):
        yield
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes("literature"))

    def test_moves_each_stored_value_into_custom_under_its_csl_name(self):
        Item = migrate(BEFORE).get_model("literature", "Item")
        item = Item.objects.create(
            citation_key="Moved2021",
            type="book",
            citation_label="MD21",
            citation_number="3",
            first_reference_note_number="12",
            locator="45-47",
            year_suffix="a",
            custom={"shelf": "B4"},
        )

        Item = migrate(AFTER).get_model("literature", "Item")

        assert Item.objects.get(pk=item.pk).custom == {
            "shelf": "B4",
            "citation-label": "MD21",
            "citation-number": "3",
            "first-reference-note-number": "12",
            "locator": "45-47",
            "year-suffix": "a",
        }

    def test_leaves_an_item_with_none_of_them_as_it_was(self):
        Item = migrate(BEFORE).get_model("literature", "Item")
        empty = Item.objects.create(citation_key="Empty2021", type="book")
        held = Item.objects.create(
            citation_key="Held2021", type="book", custom={"shelf": "B4"}
        )

        Item = migrate(AFTER).get_model("literature", "Item")

        assert Item.objects.get(pk=empty.pk).custom is None
        assert Item.objects.get(pk=held.pk).custom == {"shelf": "B4"}

    def test_refuses_to_migrate_a_value_whose_custom_is_not_an_object(self):
        Item = migrate(BEFORE).get_model("literature", "Item")
        listed = Item.objects.create(
            citation_key="Listed2021", type="book", locator="4", custom=["x"]
        )

        with pytest.raises(ValueError, match="Listed2021"):
            migrate(AFTER)

        # The refused row would block the fixture's migration back to the latest schema.
        listed.delete()

    def test_reversing_puts_the_values_back_in_their_columns(self):
        Item = migrate(BEFORE).get_model("literature", "Item")
        item = Item.objects.create(
            citation_key="Reversed2021", type="book", year_suffix="a"
        )
        migrate(AFTER)

        Item = migrate(BEFORE).get_model("literature", "Item")

        reversed_item = Item.objects.get(pk=item.pk)
        assert (reversed_item.year_suffix, reversed_item.custom) == ("a", None)

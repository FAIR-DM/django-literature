"""Tests for ``literature/ui/fields.py`` — D-6."""

import pytest

from literature.choices import ItemType
from literature.models import Item
from literature.ui.fields import scalar_fields
from tests.factories import ItemFactory


@pytest.mark.django_db
class TestScalarFields:
    """FR-020, FR-021: every non-empty scalar field the item carries, and nothing else."""

    def test_yields_non_empty_concrete_fields_under_their_verbose_name(self):
        item = ItemFactory(title="A Title", volume="12")
        pairs = {str(label): value for label, value in scalar_fields(item)}
        assert pairs[str(item._meta.get_field("title").verbose_name)] == "A Title"
        assert pairs[str(item._meta.get_field("volume").verbose_name)] == "12"

    def test_omits_blank_fields_entirely(self):
        item = ItemFactory(title="", volume="")
        labels = {str(label) for label, _ in scalar_fields(item)}
        assert str(item._meta.get_field("title").verbose_name) not in labels
        assert str(item._meta.get_field("volume").verbose_name) not in labels

    def test_a_choice_field_yields_its_label_not_its_stored_value(self):
        item = ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        pairs = {str(label): value for label, value in scalar_fields(item)}
        assert pairs[str(item._meta.get_field("type").verbose_name)] == "Journal Article"

    def test_a_stored_value_matching_no_label_is_yielded_unchanged(self):
        # get_FOO_display() falls back to the raw value, so a slug the
        # enumeration has since dropped still renders rather than vanishing.
        item = ItemFactory()
        Item.objects.filter(pk=item.pk).update(type="not-a-csl-type")
        item.refresh_from_db()
        pairs = {str(label): value for label, value in scalar_fields(item)}
        assert pairs[str(item._meta.get_field("type").verbose_name)] == "not-a-csl-type"

    def test_omits_relations(self):
        item = ItemFactory()
        names = {name for name, _ in scalar_fields(item)}
        assert not any(value == item.item_names for _, value in scalar_fields(item))
        assert "item_names" not in names
        assert "item_dates" not in names
        assert "item_identifiers" not in names

    def test_omits_the_primary_key(self):
        item = ItemFactory()
        labels = {str(label) for label, _ in scalar_fields(item)}
        assert str(item._meta.get_field("id").verbose_name) not in labels

    def test_default_skip_set_excludes_audit_and_json_fields(self):
        item = ItemFactory(categories=["x"], custom={"a": 1})
        labels = {str(label) for label, _ in scalar_fields(item)}
        assert str(item._meta.get_field("created").verbose_name) not in labels
        assert str(item._meta.get_field("modified").verbose_name) not in labels
        assert str(item._meta.get_field("categories").verbose_name) not in labels
        assert str(item._meta.get_field("custom").verbose_name) not in labels

    def test_caller_supplied_skip_overrides_the_default(self):
        item = ItemFactory(title="A Title")
        pairs = {str(label): value for label, value in scalar_fields(item, skip={"title"})}
        assert str(item._meta.get_field("title").verbose_name) not in pairs
        # The default skip set no longer applies — created is now carried.
        assert str(item._meta.get_field("created").verbose_name) in pairs

    def test_citation_key_and_type_are_scalar_fields_too(self):
        item = ItemFactory()
        labels = {str(label) for label, _ in scalar_fields(item)}
        assert str(item._meta.get_field("citation_key").verbose_name) in labels
        assert str(item._meta.get_field("type").verbose_name) in labels

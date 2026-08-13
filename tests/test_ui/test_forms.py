"""Tests for ``literature/ui/forms.py`` — the one write form every flow shares (plan.md D-3, D-4).

``ItemForm`` declares every scalar field so scoping stays visibility-only:
the template hides groups a type does not use, but nothing the form
declares is ever narrowed by type, and a hidden field still posts the value
it already held (D-3).
"""

import pytest

from literature.choices import ItemType
from literature.models import Item
from literature.ui.forms import ItemForm
from tests.factories import ItemFactory

#: The four fields ``ItemForm`` never declares (D-4) — ``categories`` and
#: ``custom`` because they are not on the form at all, ``created`` and
#: ``modified`` because they are auto-managed timestamps.
EXCLUDED_FROM_FORM = frozenset({"categories", "custom", "created", "modified"})


def _scalar_field_names():
    return {field.name for field in Item._meta.get_fields() if hasattr(field, "attname") and not field.primary_key}


class TestItemFormFields:
    def test_declares_every_scalar_field_of_item(self):
        assert set(ItemForm().fields) == _scalar_field_names() - EXCLUDED_FROM_FORM

    def test_declares_neither_categories_nor_custom_nor_the_auto_timestamps(self):
        fields = ItemForm().fields
        assert EXCLUDED_FROM_FORM.isdisjoint(fields)


@pytest.mark.django_db
class TestItemFormValidation:
    def test_a_form_with_only_type_and_citation_key_is_valid(self):
        form = ItemForm(data={"type": ItemType.ARTICLE_JOURNAL, "citation_key": "Doe2024"})
        assert form.is_valid(), form.errors

    def test_a_form_missing_type_is_invalid_and_names_the_field(self):
        form = ItemForm(data={"citation_key": "Doe2024"})
        assert not form.is_valid()
        assert "type" in form.errors

    def test_a_form_missing_citation_key_is_invalid_and_names_the_field(self):
        form = ItemForm(data={"type": ItemType.ARTICLE_JOURNAL})
        assert not form.is_valid()
        assert "citation_key" in form.errors

    def test_a_citation_key_duplicating_a_stored_items_key_is_valid(self):
        # FR-007 — citation_key is indexed but not globally unique; a
        # colliding key is a fact the store holds, never a validation error.
        existing = ItemFactory(citation_key="Doe2024")
        form = ItemForm(data={"type": ItemType.ARTICLE_JOURNAL, "citation_key": "Doe2024"})
        assert form.is_valid(), form.errors
        saved = form.save()
        assert saved.pk != existing.pk

    def test_a_duplicate_citation_key_is_stored_unchanged(self):
        ItemFactory(citation_key="Doe2024")
        form = ItemForm(data={"type": ItemType.ARTICLE_JOURNAL, "citation_key": "Doe2024"})
        assert form.is_valid(), form.errors
        saved = form.save()
        assert saved.citation_key == "Doe2024"

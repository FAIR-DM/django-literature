"""Tests for ``literature/ui/forms.py`` — the one write form every flow shares (plan.md D-3, D-4).

``ItemForm`` declares every scalar field so scoping stays visibility-only:
the template hides groups a type does not use, but nothing the form
declares is ever narrowed by type, and a hidden field still posts the value
it already held (D-3).
"""

import pytest
from django.test import override_settings

from literature.choices import ItemType
from literature.importers import available_formats
from literature.ui.forms import ImportForm, ItemForm
from tests.factories import ItemFactory
from tests.test_ui.conftest import EXCLUDED_FROM_FORM, scalar_field_names


class TestItemFormFields:
    def test_declares_every_scalar_field_of_item(self):
        assert set(ItemForm().fields) == scalar_field_names() - EXCLUDED_FROM_FORM

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


class TestImportForm:
    """``ImportForm`` — choose a format and a file to import (US-1, FR-005, FR-006, FR-010)."""

    def test_offers_exactly_the_configured_formats(self):
        # FR-005 — not a hard-coded pair: whatever LITERATURE["BIB_FORMATS"]
        # resolves to, and nothing else.
        choices = dict(ImportForm().fields["format"].choices)
        expected = {name: format_class.label for name, format_class in available_formats().items()}
        assert choices == expected

    def test_the_choices_are_built_when_the_form_is_instantiated(self):
        # FR-005 — a format configured after import time still appears: the
        # choices must be read from available_formats() in __init__, not
        # frozen on the class at import time.
        with override_settings(LITERATURE={"BIB_FORMATS": ["literature.importers.bibtex.BibTeXFormat"]}):
            choices = dict(ImportForm().fields["format"].choices)
        assert list(choices) == ["bibtex"]

    def test_both_fields_are_required(self):
        assert ImportForm().fields["format"].required
        assert ImportForm().fields["file"].required

    def test_a_form_submitted_with_neither_is_invalid_with_a_reason_on_each(self):
        form = ImportForm(data={}, files={})
        assert not form.is_valid()
        assert "format" in form.errors
        assert "file" in form.errors

    def test_the_form_is_multipart(self):
        # The file control cannot post without it (T111's own guard reads
        # this off the rendered page).
        assert ImportForm().is_multipart()

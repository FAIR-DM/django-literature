"""Tests for ``literature/ui/forms.py`` — the one write form every flow shares (plan.md D-3, D-4).

``ItemForm`` declares every scalar field so scoping stays visibility-only:
the template hides groups a type does not use, but nothing the form
declares is ever narrowed by type, and a hidden field still posts the value
it already held (D-3).
"""

import pytest
from django import forms
from django.test import override_settings

from literature.choices import ItemType, NameRole
from literature.importers import available_formats
from literature.models import Name
from literature.ui.forms import ConfirmImportForm, ImportForm, ItemForm, NameForm
from tests.factories import ItemFactory, ItemNameFactory, NameFactory
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

    def test_carries_a_skip_preview_control_unticked_by_default_and_not_required(self):
        # FR-040 — previewing is the default path; ticking this is the only
        # way to skip it, and a blank form is not itself invalid for lacking
        # a tick (a checkbox left unticked, not one left unanswered).
        field = ImportForm().fields["skip_preview"]
        assert field.required is False
        assert field.initial is False


class TestConfirmImportForm:
    """Carries out a previewed import — US-4 (FR-042).

    Nothing on this page may name the staged file. The token and the format
    it was staged as both live in the reader's own session (decisions.md
    D16), and a field carrying either would be exactly the design this
    feature declines to copy — a request that confirms whatever it was
    handed the name of.

    It does carry which preview the page was showing (decisions.md D28).
    That is a different thing: it names nothing on disk, and the view
    imports only where it matches the confirming session's own value, so on
    its own it reaches nothing at all.
    """

    def test_carries_no_file_field(self):
        assert "file" not in ConfirmImportForm().fields

    def test_carries_no_token_field(self):
        assert "token" not in ConfirmImportForm().fields

    def test_names_nothing_the_staged_file_can_be_found_by(self):
        # The blanket "no fields at all" this replaced was a proxy for the
        # rule, and stopped tracking it once a field that reaches nothing
        # was added. This asserts the rule.
        forbidden = {"file", "token", "name", "filename", "path", "format", "resource"}
        assert forbidden.isdisjoint(ConfirmImportForm().fields)

    def test_carries_only_which_preview_was_shown(self):
        assert set(ConfirmImportForm().fields) == {"preview"}

    def test_the_preview_field_is_hidden_and_not_required(self):
        # Not required: a confirmation arriving without it is refused by the
        # view as naming no preview, which is the same answer as naming the
        # wrong one — never a field error on a page with nothing to correct.
        field = ConfirmImportForm().fields["preview"]
        assert isinstance(field.widget, forms.HiddenInput)
        assert not field.required


@pytest.mark.django_db
class TestNameForm:
    """``NameForm`` — the contributor row form over ``ItemName`` (plan.md D-3,
    T006). Family and given are the row's own columns; the particles, the
    suffix and the unparsed organizational form are reachable rather than
    laid out (FR-009, FR-008). The three citation-processor flags are never
    declared, so ``ModelForm`` cannot write them (FR-010).
    """

    def test_declares_neither_the_name_fk_nor_order(self):
        # ``name`` is written in save(), not posted; ``order`` is
        # ``editable=False`` and excluded from any generated form (D-4).
        fields = NameForm().fields
        assert "name" not in fields
        assert "order" not in fields

    def test_never_declares_the_citation_processor_flags(self):
        fields = NameForm().fields
        assert "comma_suffix" not in fields
        assert "static_ordering" not in fields
        assert "parse_names" not in fields

    def test_declares_family_and_given_and_the_disclosure_fields(self):
        fields = NameForm().fields
        for name in ("family", "given", "dropping_particle", "non_dropping_particle", "suffix", "literal"):
            assert name in fields

    def test_a_contributor_with_only_an_unparsed_name_saves(self, item):
        form = NameForm(data={"role": NameRole.AUTHOR, "literal": "United Nations"})
        assert form.is_valid(), form.errors
        item_name = form.save(commit=False)
        item_name.item = item
        item_name.save()
        assert item_name.name.literal == "United Nations"
        assert item_name.name.family == ""

    def test_a_contributor_with_neither_family_nor_unparsed_name_is_rejected(self):
        form = NameForm(data={"role": NameRole.AUTHOR, "given": "Jane"})
        assert not form.is_valid()
        assert not Name.objects.exists()

    def test_the_rejection_names_no_specific_field_but_carries_a_message(self):
        # FR-011 — "returns the form saying so" rather than storing anything;
        # neither family nor literal is individually required at the field
        # level, so the message belongs to the form as a whole.
        form = NameForm(data={"role": NameRole.AUTHOR})
        assert not form.is_valid()
        assert form.non_field_errors()

    def test_a_valid_contributor_with_family_and_given_saves(self, item):
        form = NameForm(data={"role": NameRole.AUTHOR, "family": "Doe", "given": "Jane"})
        assert form.is_valid(), form.errors
        item_name = form.save(commit=False)
        item_name.item = item
        item_name.save()
        assert item_name.name.family == "Doe"
        assert item_name.name.given == "Jane"

    def test_editing_an_existing_row_seeds_initial_values_from_its_linked_name(self):
        item_name = ItemNameFactory(name=NameFactory(family="Aardvark", given="Zoe"))
        form = NameForm(instance=item_name)
        assert form.initial["family"] == "Aardvark"
        assert form.initial["given"] == "Zoe"

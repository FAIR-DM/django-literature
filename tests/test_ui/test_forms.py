"""Tests for ``literature/ui/forms.py``."""

import pytest
from django import forms
from django.test import override_settings

from literature.choices import DateType, IdentifierType, ItemType, NameRole
from literature.importers import available_formats
from literature.models import ItemDate, Name
from literature.ui.forms import (
    ConfirmImportForm,
    ImportForm,
    ItemDateForm,
    ItemForm,
    ItemIdentifierForm,
    NameForm,
)
from tests.factories import ItemDateFactory, ItemFactory, ItemNameFactory, NameFactory
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
        form = ItemForm(
            data={"type": ItemType.ARTICLE_JOURNAL, "citation_key": "Doe2024"}
        )
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
        # citation_key is indexed but not globally unique; a
        # colliding key is a fact the store holds, never a validation error.
        existing = ItemFactory(citation_key="Doe2024")
        form = ItemForm(
            data={"type": ItemType.ARTICLE_JOURNAL, "citation_key": "Doe2024"}
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        assert saved.pk != existing.pk

    def test_a_duplicate_citation_key_is_stored_unchanged(self):
        ItemFactory(citation_key="Doe2024")
        form = ItemForm(
            data={"type": ItemType.ARTICLE_JOURNAL, "citation_key": "Doe2024"}
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        assert saved.citation_key == "Doe2024"


class TestImportForm:
    def test_offers_exactly_the_configured_formats(self):
        # Not a hard-coded pair: whatever LITERATURE["BIB_FORMATS"]
        # resolves to, and nothing else.
        choices = dict(ImportForm().fields["format"].choices)
        expected = {
            name: format_class.label
            for name, format_class in available_formats().items()
        }
        assert choices == expected

    def test_the_choices_are_built_when_the_form_is_instantiated(self):
        # A format configured after import time still appears: the
        # choices must be read from available_formats() in __init__, not
        # frozen on the class at import time.
        with override_settings(
            LITERATURE={"BIB_FORMATS": ["literature.importers.bibtex.BibTeXFormat"]}
        ):
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
        # The file control cannot post without it.
        assert ImportForm().is_multipart()

    def test_carries_a_skip_preview_control_unticked_by_default_and_not_required(self):
        # Previewing is the default path; ticking this is the only
        # way to skip it, and a blank form is not itself invalid for lacking
        # a tick (a checkbox left unticked, not one left unanswered).
        field = ImportForm().fields["skip_preview"]
        assert field.required is False
        assert field.initial is False


class TestConfirmImportForm:
    # Nothing on the page may name the staged file: its token and format live in the
    # reader's session, and the preview id reaches nothing unless it matches.

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
    def test_declares_neither_the_name_fk_nor_order(self):
        # ``name`` is written in save(), not posted; ``order`` is
        # ``editable=False`` and excluded from any generated form.
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
        for name in (
            "family",
            "given",
            "dropping_particle",
            "non_dropping_particle",
            "suffix",
            "literal",
        ):
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
        # Neither family nor literal is individually required at the field
        # level, so the message belongs to the form as a whole.
        form = NameForm(data={"role": NameRole.AUTHOR})
        assert not form.is_valid()
        assert form.non_field_errors()

    def test_a_valid_contributor_with_family_and_given_saves(self, item):
        form = NameForm(
            data={"role": NameRole.AUTHOR, "family": "Doe", "given": "Jane"}
        )
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


class TestItemDateFormFields:
    def test_declares_exactly_date_type_begin_and_end(self):
        assert set(ItemDateForm().fields) == {"date_type", "begin", "end"}

    def test_declares_neither_season_circa_literal_raw_nor_raw_date_parts(self):
        fields = ItemDateForm().fields
        for name in ("season", "circa", "literal", "raw", "raw_date_parts", "item"):
            assert name not in fields


@pytest.mark.django_db
class TestItemDateFormRejectsAnUndeclaredSlot:
    def test_a_row_posted_with_no_slot_is_rejected_rather_than_stored(self):
        form = ItemDateForm(data={"date_type": "", "begin": "2020", "end": ""})
        assert not form.is_valid()
        assert "date_type" in form.errors
        assert not ItemDate.objects.exists()


@pytest.mark.django_db
class TestItemDateFormPrecision:
    @pytest.mark.parametrize("value", ["2019", "2019-03", "2019-03-14"])
    def test_each_precision_round_trips(self, value, item):
        form = ItemDateForm(
            data={"date_type": DateType.ISSUED, "begin": value, "end": ""}
        )
        assert form.is_valid(), form.errors
        instance = form.save(commit=False)
        instance.item = item
        instance.save()
        instance.refresh_from_db()
        # The stored value renders back as the string that re-parses to it
        # at the same precision.
        assert str(instance.begin) == value


@pytest.mark.django_db
class TestItemDateFormSpan:
    def test_a_year_to_year_span_is_valid(self):
        form = ItemDateForm(
            data={"date_type": DateType.EVENT_DATE, "begin": "2019", "end": "2021"}
        )
        assert form.is_valid(), form.errors

    def test_a_mixed_precision_span_is_valid(self):
        form = ItemDateForm(
            data={
                "date_type": DateType.EVENT_DATE,
                "begin": "2019",
                "end": "2021-06-15",
            }
        )
        assert form.is_valid(), form.errors

    def test_an_end_with_no_begin_is_rejected_as_a_form_error_not_an_exception(self):
        form = ItemDateForm(
            data={"date_type": DateType.EVENT_DATE, "begin": "", "end": "2021"}
        )
        assert not form.is_valid()
        assert form.non_field_errors()

    def test_an_end_before_its_begin_is_rejected_as_a_form_error_not_an_exception(self):
        form = ItemDateForm(
            data={"date_type": DateType.EVENT_DATE, "begin": "2021", "end": "2019"}
        )
        assert not form.is_valid()
        assert form.non_field_errors()


@pytest.mark.django_db
class TestItemDateFormSettledSlot:
    def test_an_unsettled_row_offers_every_slot_by_default(self):
        # A required ChoiceField with no model default still carries
        # Django's own blank placeholder choice alongside the six named
        # slots (Field.formfield()'s own include_blank rule) — this
        # asserts every real slot is among them, not that the blank choice
        # is absent.
        form = ItemDateForm()
        choices = {choice[0] for choice in form.fields["date_type"].choices}
        assert set(DateType.values) <= choices
        assert form.fields["date_type"].disabled is False

    def test_an_unsettled_row_excludes_the_occupied_slots(self):
        form = ItemDateForm(occupied_slots={DateType.ISSUED, DateType.ACCESSED})
        choices = {choice[0] for choice in form.fields["date_type"].choices}
        assert choices.isdisjoint({DateType.ISSUED, DateType.ACCESSED})
        assert set(DateType.values) - {DateType.ISSUED, DateType.ACCESSED} <= choices

    def test_a_row_over_a_stored_instance_is_disabled(self, item):
        instance = ItemDateFactory(item=item, date_type=DateType.ISSUED)
        form = ItemDateForm(instance=instance)
        assert form.fields["date_type"].disabled is True

    def test_a_pre_filled_extra_row_is_disabled(self):
        form = ItemDateForm(initial={"date_type": DateType.ISSUED})
        assert form.fields["date_type"].disabled is True

    def test_a_disabled_rows_slot_ignores_a_different_posted_value(self, item):
        instance = ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        form = ItemDateForm(
            data={"date_type": DateType.ACCESSED, "begin": "2021", "end": ""},
            instance=instance,
        )
        assert form.is_valid(), form.errors
        assert form.cleaned_data["date_type"] == DateType.ISSUED


@pytest.mark.django_db
class TestItemDateFormUnparsedRepair:
    def test_a_date_with_only_a_literal_value_shows_it(self, item):
        instance = ItemDateFactory(
            item=item, date_type=DateType.ISSUED, literal="circa 1922"
        )
        form = ItemDateForm(instance=instance)
        assert form.fields["begin"].widget.attrs.get("placeholder") == "circa 1922"

    def test_a_date_with_only_a_raw_value_shows_it(self, item):
        instance = ItemDateFactory(item=item, date_type=DateType.ISSUED, raw="1922?")
        form = ItemDateForm(instance=instance)
        assert form.fields["begin"].widget.attrs.get("placeholder") == "1922?"

    def test_a_date_already_carrying_begin_shows_no_placeholder(self, item):
        instance = ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin="1922", literal="circa 1922"
        )
        form = ItemDateForm(instance=instance)
        assert "placeholder" not in form.fields["begin"].widget.attrs

    def test_replacing_the_unparsed_value_stores_the_readable_date_and_leaves_literal_alone(
        self, item
    ):
        instance = ItemDateFactory(
            item=item, date_type=DateType.ISSUED, literal="circa 1922"
        )
        form = ItemDateForm(
            data={"date_type": DateType.ISSUED, "begin": "1922", "end": ""},
            instance=instance,
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        saved.refresh_from_db()
        assert str(saved.begin) == "1922"
        assert saved.literal == "circa 1922"


class TestItemIdentifierFormFields:
    def test_declares_exactly_type_and_value(self):
        assert set(ItemIdentifierForm().fields) == {"type", "value"}

    def test_the_type_field_offers_the_six_known_kinds_as_completions(self):
        # Offered without restricting to them: the six known
        # kinds render as <option>s of a <datalist> the type input
        # references through list=, so another kind stays typeable.
        rendered = str(ItemIdentifierForm()["type"])
        assert "<datalist" in rendered
        for kind in IdentifierType.values:
            assert f'value="{kind}"' in rendered


@pytest.mark.django_db
class TestItemIdentifierFormNormalization:
    def test_isbn_typed_lowercase_is_normalized_and_checked_as_isbn(self):
        form = ItemIdentifierForm(data={"type": "isbn", "value": "978-0-306-40615-7"})
        assert form.is_valid(), form.errors
        assert form.cleaned_data["type"] == IdentifierType.ISBN

    def test_isbn_typed_lowercase_with_a_malformed_value_is_rejected(self):
        # ItemIdentifier.clean() (literature/models.py) raises a plain
        # ValidationError, the same shape ItemDateForm's span rejections
        # take — _post_clean surfaces it as a non-field error rather
        # than attaching it to "value".
        form = ItemIdentifierForm(data={"type": "isbn", "value": "not-an-isbn"})
        assert not form.is_valid()
        assert form.non_field_errors()

    def test_a_genuinely_unknown_kind_is_stored_exactly_as_given_and_unchecked(
        self, item
    ):
        form = ItemIdentifierForm(
            data={"type": "arxiv", "value": "anything at all, unchecked"}
        )
        assert form.is_valid(), form.errors
        instance = form.save(commit=False)
        instance.item = item
        instance.save()
        instance.refresh_from_db()
        assert instance.type == "arxiv"
        assert instance.value == "anything at all, unchecked"

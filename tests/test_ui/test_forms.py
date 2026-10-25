"""Tests for ``literature/ui/forms.py``."""

import pytest
from django import forms
from django.test import override_settings

from literature.choices import DateType, IdentifierType, ItemType, NameRole
from literature.importers import available_formats
from literature.models import Name
from literature.ui.forms import (
    ConfirmImportForm,
    ImportForm,
    ItemForm,
    ItemIdentifierForm,
    NameForm,
)
from tests.factories import (
    ItemDateFactory,
    ItemFactory,
    ItemIdentifierFactory,
    ItemNameFactory,
    NameFactory,
)
from tests.test_ui.conftest import EXCLUDED_FROM_FORM, scalar_field_names

#: One start and one end field per CSL date slot.
DATE_FIELDS = {
    f"date_{slot.replace('-', '_')}{end}"
    for slot in DateType.values
    for end in ("", "_end")
}


def item_form_data(**fields):
    """A valid write form submission, with ``fields`` posted on top."""
    return {"type": ItemType.BOOK, "citation_key": "Form2024", **fields}


@pytest.mark.django_db
class TestItemFormFields:
    def test_declares_every_scalar_field_and_a_field_per_date_slot(self):
        scalars = scalar_field_names() - EXCLUDED_FROM_FORM
        assert set(ItemForm().fields) == scalars | DATE_FIELDS

    def test_declares_neither_categories_nor_custom_nor_the_auto_timestamps(self):
        fields = ItemForm().fields
        assert EXCLUDED_FROM_FORM.isdisjoint(fields)


@pytest.mark.django_db
class TestItemFormKeywords:
    def test_tags_are_stored_as_one_comma_separated_string(self):
        form = ItemForm(data=item_form_data(keyword=["entropy", "information theory"]))
        assert form.is_valid(), form.errors
        assert form.save().keyword == "entropy, information theory"

    def test_a_keyword_the_catalogue_has_never_used_is_accepted(self):
        ItemFactory(keyword="archives")
        form = ItemForm(data=item_form_data(keyword=["never used before"]))
        assert form.is_valid(), form.errors

    def test_stored_keywords_are_offered_as_tags_in_their_stored_order(self):
        item = ItemFactory(keyword="zebra; apple")
        assert ItemForm(instance=item)["keyword"].value() == ["zebra", "apple"]

    def test_unchanged_tags_keep_the_stored_string_exactly(self):
        item = ItemFactory(keyword="zebra; apple")
        form = ItemForm(
            data=item_form_data(
                type=item.type,
                citation_key=item.citation_key,
                keyword=["zebra", "apple"],
            ),
            instance=item,
        )
        assert form.is_valid(), form.errors
        assert form.save().keyword == "zebra; apple"


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
    def test_declares_no_role_since_the_set_a_row_sits_in_is_its_role(self):
        assert "role" not in NameForm(role=NameRole.EDITOR).fields

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
        form = NameForm(data={"literal": "United Nations"}, role=NameRole.AUTHOR)
        assert form.is_valid(), form.errors
        item_name = form.save(commit=False)
        item_name.item = item
        item_name.save()
        assert item_name.name.literal == "United Nations"
        assert item_name.name.family == ""

    def test_a_contributor_with_neither_family_nor_unparsed_name_is_rejected(self):
        form = NameForm(data={"given": "Jane"}, role=NameRole.AUTHOR)
        assert not form.is_valid()
        assert not Name.objects.exists()

    def test_the_rejection_names_no_specific_field_but_carries_a_message(self):
        # Neither family nor literal is individually required at the field
        # level, so the message belongs to the form as a whole.
        form = NameForm(data={}, role=NameRole.AUTHOR)
        assert not form.is_valid()
        assert form.non_field_errors()

    def test_a_valid_contributor_with_family_and_given_saves(self, item):
        form = NameForm(data={"family": "Doe", "given": "Jane"}, role=NameRole.AUTHOR)
        assert form.is_valid(), form.errors
        item_name = form.save(commit=False)
        item_name.item = item
        item_name.save()
        assert item_name.role == NameRole.AUTHOR
        assert item_name.name.family == "Doe"
        assert item_name.name.given == "Jane"

    def test_editing_an_existing_row_seeds_initial_values_from_its_linked_name(self):
        item_name = ItemNameFactory(name=NameFactory(family="Aardvark", given="Zoe"))
        form = NameForm(instance=item_name)
        assert form.initial["family"] == "Aardvark"
        assert form.initial["given"] == "Zoe"


@pytest.mark.django_db
class TestItemFormDates:
    @pytest.mark.parametrize(
        ("parts", "stored"),
        [
            ({"year": "2019"}, "2019"),
            ({"year": "2019", "month": "03"}, "2019-03"),
            ({"year": "2019", "month": "03", "day": "14"}, "2019-03-14"),
        ],
    )
    def test_each_precision_is_stored_in_its_slot(self, parts, stored):
        data = item_form_data(**{f"date_issued_{k}": v for k, v in parts.items()})
        form = ItemForm(data=data)
        assert form.is_valid(), form.errors
        item = form.save()
        assert str(item.item_dates.get(date_type=DateType.ISSUED).begin) == stored

    def test_a_range_is_stored_on_one_slot(self):
        form = ItemForm(
            data=item_form_data(
                date_event_date_year="2019", date_event_date_end_year="2021"
            )
        )
        assert form.is_valid(), form.errors
        date = form.save().item_dates.get(date_type=DateType.EVENT_DATE)
        assert (str(date.begin), str(date.end)) == ("2019", "2021")

    def test_an_end_with_no_start_is_rejected_on_the_slots_end(self):
        form = ItemForm(data=item_form_data(date_event_date_end_year="2021"))
        assert not form.is_valid()
        assert "date_event_date_end" in form.errors

    def test_an_end_before_its_start_is_rejected_on_the_slots_end(self):
        form = ItemForm(
            data=item_form_data(
                date_event_date_year="2021", date_event_date_end_year="2019"
            )
        )
        assert not form.is_valid()
        assert "date_event_date_end" in form.errors

    def test_a_slot_left_empty_stores_nothing(self):
        form = ItemForm(data=item_form_data(date_issued_year="2020"))
        assert form.is_valid(), form.errors
        assert list(form.save().item_dates.values_list("date_type", flat=True)) == [
            DateType.ISSUED
        ]

    def test_clearing_a_slot_removes_its_date_and_no_other(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2021")
        form = ItemForm(
            data=item_form_data(
                type=item.type, citation_key=item.citation_key, date_issued_year="2020"
            ),
            instance=item,
        )
        assert form.is_valid(), form.errors
        form.save()
        assert list(item.item_dates.values_list("date_type", flat=True)) == [
            DateType.ISSUED
        ]

    def test_a_stored_date_shows_in_its_slot(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2021-05")
        assert str(ItemForm(instance=item)["date_accessed"].value()) == "2021-05"

    def test_a_date_with_only_unparsed_text_shows_it_on_the_slot(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, literal="circa 1922")
        year = ItemForm(instance=item).fields["date_issued"].widget.widgets[0]
        assert year.attrs.get("placeholder") == "circa 1922"

    def test_clearing_a_slot_holding_unparsed_text_keeps_the_text(self):
        item = ItemFactory()
        ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin="1922", literal="circa 1922"
        )
        form = ItemForm(
            data=item_form_data(type=item.type, citation_key=item.citation_key),
            instance=item,
        )
        assert form.is_valid(), form.errors
        form.save()
        date = item.item_dates.get(date_type=DateType.ISSUED)
        assert (date.begin, date.literal) == (None, "circa 1922")

    def test_replacing_unparsed_text_stores_the_date_and_leaves_the_text(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, literal="circa 1922")
        form = ItemForm(
            data=item_form_data(
                type=item.type, citation_key=item.citation_key, date_issued_year="1922"
            ),
            instance=item,
        )
        assert form.is_valid(), form.errors
        form.save()
        date = item.item_dates.get(date_type=DateType.ISSUED)
        assert (str(date.begin), date.literal) == ("1922", "circa 1922")


class TestItemIdentifierFormFields:
    def test_declares_exactly_type_and_value(self):
        assert set(ItemIdentifierForm().fields) == {"type", "value"}

    def test_the_type_field_offers_the_six_known_types_as_choices(self):
        choices = {
            value for value, _label in ItemIdentifierForm().fields["type"].choices
        }
        assert set(IdentifierType.values) <= choices

    @pytest.mark.django_db
    def test_a_stored_type_outside_the_six_is_offered_back(self, item):
        instance = ItemIdentifierFactory(item=item, type="arXiv", value="2101.00001")
        choices = ItemIdentifierForm(instance=instance).fields["type"].choices
        assert ("arXiv", "arXiv") in choices


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

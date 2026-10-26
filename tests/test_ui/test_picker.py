"""Tests for ``literature/ui/picker.py``."""

from html.parser import HTMLParser

import pytest
from django import forms
from django.contrib.staticfiles import finders
from django.db import connection, models
from django.forms import formset_factory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from literature.choices import DateType, NameRole
from literature.models import Item, ItemName
from literature.ui.picker import ItemChoiceField, ItemSearchSelect, item_label
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


class Selects(HTMLParser):
    """Collect each rendered ``<select>``: its attributes and its options."""

    def __init__(self, markup):
        super().__init__()
        self.selects = []
        self._option = None
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "select":
            self.selects.append({"attrs": dict(attrs), "options": []})
        elif tag == "option":
            self._option = {"value": dict(attrs).get("value"), "text": ""}
            self.selects[-1]["options"].append(self._option)

    def handle_endtag(self, tag):
        if tag == "option":
            self._option = None

    def handle_data(self, data):
        if self._option is not None:
            self._option["text"] += data


class ReferenceForm(forms.Form):
    reference = ItemChoiceField()


class OptionalReferenceForm(forms.Form):
    reference = ItemChoiceField(required=False)


class ItemNameForm(forms.ModelForm):
    class Meta:
        model = ItemName
        fields = ["item"]
        field_classes = {"item": ItemChoiceField}


def select_of(form, name="reference"):
    (select,) = Selects(str(form[name])).selects
    return select


@pytest.mark.django_db
class TestItemChoiceField:
    def test_the_select_holds_only_the_chosen_option_labelled_by_item_label(self):
        chosen = ItemFactory(title="Chosen & Quoted")
        ItemNameFactory(item=chosen, name=NameFactory(family="Rowe"))
        ItemFactory(title="Left out")

        select = select_of(ReferenceForm(initial={"reference": chosen}))

        (option,) = select["options"]
        assert option["value"] == str(chosen.pk)
        assert option["text"] == item_label(Item.objects.get(pk=chosen.pk))
        assert "Chosen & Quoted" in option["text"]

    def test_an_empty_field_draws_no_options(self):
        ItemFactory()

        assert select_of(ReferenceForm())["options"] == []

    def test_the_select_carries_the_search_route_and_the_tom_select_marker(self):
        select = select_of(ReferenceForm())

        assert select["attrs"]["data-search-url"] == reverse("literature:item-search")
        assert "data-tom-select" in select["attrs"]

    def test_the_field_is_drawn_with_the_picker_widget(self):
        assert isinstance(ReferenceForm().fields["reference"].widget, ItemSearchSelect)

    def test_a_valid_pk_cleans_to_the_item(self):
        item = ItemFactory()
        form = ReferenceForm(data={"reference": str(item.pk)})

        assert form.is_valid()
        assert form.cleaned_data["reference"] == item

    def test_a_vanished_pk_is_refused_with_invalid_choice(self):
        item = ItemFactory()
        pk = item.pk
        item.delete()
        form = ReferenceForm(data={"reference": str(pk)})

        assert not form.is_valid()
        assert form.has_error("reference", code="invalid_choice")

    def test_a_submitted_non_number_redraws_with_the_error(self):
        ItemFactory()
        form = ReferenceForm(data={"reference": "abc"})

        assert not form.is_valid()
        assert form.has_error("reference", code="invalid_choice")
        assert select_of(form)["options"] == []

    def test_an_empty_submission_is_refused_when_required(self):
        form = ReferenceForm(data={"reference": ""})

        assert form.has_error("reference", code="required")

    def test_an_empty_submission_is_accepted_when_not_required(self):
        form = OptionalReferenceForm(data={"reference": ""})

        assert form.is_valid()
        assert form.cleaned_data["reference"] is None

    def test_a_bound_form_redraws_the_submitted_choice(self):
        item = ItemFactory(title="Redrawn")
        form = ReferenceForm(data={"reference": str(item.pk)})

        (option,) = select_of(form)["options"]

        assert option["value"] == str(item.pk)

    def test_drawing_never_runs_the_catalogue_queryset(self):
        chosen = ItemFactory(title="Chosen")
        ItemNameFactory(item=chosen)

        def queries_drawing():
            form = ReferenceForm(initial={"reference": chosen})
            with CaptureQueriesContext(connection) as queries:
                str(form["reference"])
            return len(queries)

        few = queries_drawing()
        for _ in range(8):
            ItemNameFactory(item=ItemFactory())

        # The chosen item, its dates, its name links and their names: nothing
        # that scales with, or lists, the catalogue.
        assert few == 4
        assert queries_drawing() == few

    def test_drawing_an_empty_field_issues_no_queries(self, django_assert_num_queries):
        ItemFactory()
        form = ReferenceForm()

        with django_assert_num_queries(0):
            str(form["reference"])


@pytest.mark.django_db
class TestItemChoiceFieldOnAModelForm:
    def test_field_classes_builds_the_picker_from_the_model_field(self):
        field = ItemNameForm().fields["item"]

        assert isinstance(field, ItemChoiceField)
        assert isinstance(field.widget, ItemSearchSelect)

    def test_required_follows_a_model_field_that_is_not_blank(self):
        assert ItemNameForm().fields["item"].required is True

    def test_required_follows_a_model_field_that_is_blank(self):
        foreign_key = models.ForeignKey(Item, on_delete=models.CASCADE, blank=True)

        field = foreign_key.formfield(form_class=ItemChoiceField)

        assert isinstance(field, ItemChoiceField)
        assert field.required is False

    def test_an_existing_instance_renders_its_choice(self):
        link = ItemNameFactory(item=ItemFactory(title="Linked"))

        (option,) = select_of(ItemNameForm(instance=link), "item")["options"]

        assert option["value"] == str(link.item.pk)

    def test_the_form_cleans_to_the_item(self):
        item = ItemFactory()
        form = ItemNameForm(data={"item": str(item.pk)})

        assert form.is_valid()
        assert form.cleaned_data["item"] == item


@pytest.mark.django_db
class TestItemChoiceFieldInAFormset:
    def test_each_row_carries_its_own_name_and_search_url(self):
        formset = formset_factory(ReferenceForm, extra=3)()

        selects = [select_of(form) for form in formset]

        assert [select["attrs"]["name"] for select in selects] == [
            "form-0-reference",
            "form-1-reference",
            "form-2-reference",
        ]
        assert {select["attrs"]["data-search-url"] for select in selects} == {
            reverse("literature:item-search")
        }


class TestItemSearchSelectMedia:
    def test_the_picker_script_follows_the_starting_script(self):
        media = str(ItemSearchSelect().media)

        assert "mvp_forms/tomselect.js" in media
        assert "literature/picker.js" in media
        assert media.index("mvp_forms/tomselect.js") < media.index(
            "literature/picker.js"
        )

    def test_the_picker_script_is_served_as_a_static_file(self):
        assert finders.find("literature/picker.js") is not None

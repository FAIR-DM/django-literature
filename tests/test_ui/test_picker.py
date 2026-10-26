"""Tests for ``literature/ui/picker.py``."""

import pytest
from django import forms
from django.contrib.auth.models import AnonymousUser
from django.db import connection, models
from django.http import HttpResponse
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_tomselect.app_settings import Const, TomSelectConfig
from django_tomselect.middleware import TomSelectMiddleware

from literature.choices import DateType, NameRole
from literature.models import Item, ItemName
from literature.ui.picker import ReferenceField, ReferenceMultipleField, item_label
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


def drawn(form, name="reference"):
    """Return the field drawn on a page, as django-tomselect draws it for a request."""
    request = RequestFactory().get("/form/")
    request.user = AnonymousUser()
    drawing = {}

    def respond(request):
        drawing["html"] = str(form[name])
        return HttpResponse()

    TomSelectMiddleware(respond)(request)
    return drawing["html"]


class ReferenceForm(forms.Form):
    reference = ReferenceField()


class OptionalReferenceForm(forms.Form):
    reference = ReferenceField(required=False)


class ItemNameForm(forms.ModelForm):
    class Meta:
        model = ItemName
        fields = ["item"]
        field_classes = {"item": ReferenceField}


def restricted(field_class=ReferenceField, **config):
    class RestrictedForm(forms.Form):
        reference = field_class(config=TomSelectConfig(**config))

    return RestrictedForm


@pytest.mark.django_db
class TestReferenceField:
    def test_the_control_points_at_the_search_route_by_name(self):
        html = drawn(ReferenceForm())

        assert reverse("literature:item-search") in html

    @pytest.mark.urls("tests.urls_refs")
    def test_the_control_follows_where_the_front_end_is_mounted(self):
        html = drawn(ReferenceForm())

        assert "/refs/search/" in html
        assert "/catalogue/search/" not in html

    def test_a_chosen_reference_is_drawn_labelled_by_item_label(self):
        chosen = ItemFactory(title="Chosen Title")
        ItemNameFactory(item=chosen, name=NameFactory(family="Rowe"))
        ItemFactory(title="Left out")

        html = drawn(ReferenceForm(initial={"reference": chosen}))

        assert item_label(Item.objects.get(pk=chosen.pk)) in html
        assert "Left out" not in html

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

    def test_an_empty_submission_is_refused_when_required(self):
        form = ReferenceForm(data={"reference": ""})

        assert form.has_error("reference", code="required")

    def test_an_empty_submission_is_accepted_when_not_required(self):
        form = OptionalReferenceForm(data={"reference": ""})

        assert form.is_valid()
        assert form.cleaned_data["reference"] is None

    def test_a_developers_config_merges_over_the_default(self):
        field = restricted(placeholder="Find a source", max_items=3)().fields[
            "reference"
        ]

        assert field.config.placeholder == "Find a source"
        assert field.config.max_items == 3
        assert field.config.url == "literature:item-search"
        assert field.config.label_field == "label"

    def test_a_config_given_as_a_dict_merges_over_the_default(self):
        field = ReferenceField(config={"placeholder": "Find a source"})

        assert field.config.placeholder == "Find a source"
        assert field.config.url == "literature:item-search"

    def test_a_config_can_name_another_search_route(self):
        field = ReferenceField(config=TomSelectConfig(url="literature:item-list"))

        assert field.config.url == "literature:item-list"

    def test_a_constant_filter_refuses_an_item_outside_it_on_submit(self):
        book = ItemFactory(type="book")
        article = ItemFactory(type="article")
        form_class = restricted(filter_by=Const("book", "type"))

        assert form_class(data={"reference": str(book.pk)}).is_valid()
        outside = form_class(data={"reference": str(article.pk)})
        assert not outside.is_valid()
        assert outside.has_error("reference", code="invalid_choice")

    def test_a_constant_exclude_refuses_an_excluded_item_on_submit(self):
        book = ItemFactory(type="book")
        article = ItemFactory(type="article")
        form_class = restricted(exclude_by=Const("article", "type"))

        assert form_class(data={"reference": str(book.pk)}).is_valid()
        excluded = form_class(data={"reference": str(article.pk)})
        assert not excluded.is_valid()
        assert excluded.has_error("reference", code="invalid_choice")

    def test_a_list_lookup_constant_filter_is_applied(self):
        book = ItemFactory(type="book")
        article = ItemFactory(type="article")
        report = ItemFactory(type="report")
        form_class = restricted(filter_by=Const(["book", "article"], "type__in"))

        assert form_class(data={"reference": str(book.pk)}).is_valid()
        assert form_class(data={"reference": str(article.pk)}).is_valid()
        assert not form_class(data={"reference": str(report.pk)}).is_valid()


@pytest.mark.django_db
class TestReferenceFieldOnAModelForm:
    def test_field_classes_builds_the_picker_from_the_model_field(self):
        assert isinstance(ItemNameForm().fields["item"], ReferenceField)

    def test_required_follows_a_model_field_that_is_not_blank(self):
        assert ItemNameForm().fields["item"].required is True

    def test_required_follows_a_model_field_that_is_blank(self):
        foreign_key = models.ForeignKey(Item, on_delete=models.CASCADE, blank=True)

        field = foreign_key.formfield(form_class=ReferenceField)

        assert isinstance(field, ReferenceField)
        assert field.required is False

    def test_an_existing_instance_renders_its_choice(self):
        link = ItemNameFactory(item=ItemFactory(title="Linked"))

        html = drawn(ItemNameForm(instance=link), "item")

        assert item_label(link.item) in html

    def test_the_form_cleans_to_the_item(self):
        item = ItemFactory()
        form = ItemNameForm(data={"item": str(item.pk)})

        assert form.is_valid()
        assert form.cleaned_data["item"] == item


@pytest.mark.django_db
class TestReferenceMultipleField:
    def test_the_control_points_at_the_search_route_by_name(self):
        class Form(forms.Form):
            references = ReferenceMultipleField()

        assert reverse("literature:item-search") in drawn(Form(), "references")

    def test_several_pks_clean_to_the_items(self):
        class Form(forms.Form):
            references = ReferenceMultipleField()

        first, second = ItemFactory(), ItemFactory()
        form = Form(data={"references": [str(first.pk), str(second.pk)]})

        assert form.is_valid()
        assert set(form.cleaned_data["references"]) == {first, second}

    def test_a_vanished_pk_is_refused_with_invalid_choice(self):
        class Form(forms.Form):
            references = ReferenceMultipleField()

        kept, gone = ItemFactory(), ItemFactory()
        pk = gone.pk
        gone.delete()
        form = Form(data={"references": [str(kept.pk), str(pk)]})

        assert form.has_error("references", code="invalid_choice")

    def test_an_empty_submission_follows_required(self):
        class Required(forms.Form):
            references = ReferenceMultipleField()

        class Optional(forms.Form):
            references = ReferenceMultipleField(required=False)

        assert Required(data={"references": []}).has_error(
            "references", code="required"
        )
        assert Optional(data={"references": []}).is_valid()

    def test_one_item_outside_a_constant_filter_refuses_the_submission(self):
        book = ItemFactory(type="book")
        article = ItemFactory(type="article")

        class Form(forms.Form):
            references = ReferenceMultipleField(
                config=TomSelectConfig(filter_by=Const("book", "type"))
            )

        assert Form(data={"references": [str(book.pk)]}).is_valid()
        outside = Form(data={"references": [str(book.pk), str(article.pk)]})
        assert not outside.is_valid()
        assert outside.has_error("references", code="invalid_choice")

    def test_a_blank_many_to_many_makes_the_field_optional(self):
        many_to_many = models.ManyToManyField(Item, blank=True)

        field = many_to_many.formfield(form_class=ReferenceMultipleField)

        assert isinstance(field, ReferenceMultipleField)
        assert field.required is False

    def test_a_many_to_many_that_is_not_blank_makes_the_field_required(self):
        field = models.ManyToManyField(Item).formfield(
            form_class=ReferenceMultipleField
        )

        assert field.required is True

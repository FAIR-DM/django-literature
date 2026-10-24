"""Tests for ``literature/ui/inlines.py``: the reference form's related-row sets."""

import pytest
from django.test import RequestFactory
from mvp.views.inline import InlinesMixin

from literature.choices import IdentifierType, NameRole
from literature.models import Item, ItemIdentifier, ItemName
from literature.ui.forms import ItemIdentifierForm, NameForm
from literature.ui.inlines import CONTRIBUTOR_INLINES, IdentifierInline
from tests.factories import ItemIdentifierFactory, ItemNameFactory, NameFactory


def _build_formset(declaration_cls, item):
    """Construct the formset a declaration produces, outside of any view."""
    request = RequestFactory().get("/")
    declaration = declaration_cls(Item, request, item, view=None)
    return declaration.construct_formset()


def contributor_inline(role):
    """The contributor set declaration for ``role``."""
    (declaration,) = [inline for inline in CONTRIBUTOR_INLINES if inline.role == role]
    return declaration


@pytest.mark.django_db
class TestInlineDeclarations:
    def test_there_is_one_contributor_set_per_role_each_over_item_name(self, item):
        assert {inline.role for inline in CONTRIBUTOR_INLINES} == set(NameRole.values)
        for inline in CONTRIBUTOR_INLINES:
            assert _build_formset(inline, item).model is ItemName

    def test_identifier_inline_targets_item_identifier(self, item):
        assert _build_formset(IdentifierInline, item).model is ItemIdentifier

    def test_every_set_can_delete_a_row(self, item):
        for declaration_cls in (*CONTRIBUTOR_INLINES, IdentifierInline):
            assert _build_formset(declaration_cls, item).can_delete is True

    def test_the_contributor_sets_use_nameform_for_their_rows(self, item):
        formset = _build_formset(contributor_inline(NameRole.EDITOR), item)
        assert issubclass(formset.empty_form.__class__, NameForm)

    def test_the_identifier_set_uses_itemidentifierform_for_its_rows(self, item):
        formset = _build_formset(IdentifierInline, item)
        assert issubclass(formset.empty_form.__class__, ItemIdentifierForm)


@pytest.mark.django_db
class TestContributorSets:
    def test_a_set_holds_only_its_own_roles_rows_in_credited_order(self, item):
        ItemNameFactory(item=item, role=NameRole.EDITOR, name=NameFactory(family="E"))
        ItemNameFactory(item=item, role=NameRole.AUTHOR, name=NameFactory(family="A"))
        ItemNameFactory(item=item, role=NameRole.AUTHOR, name=NameFactory(family="B"))
        authors = _build_formset(contributor_inline(NameRole.AUTHOR), item)
        editors = _build_formset(contributor_inline(NameRole.EDITOR), item)
        assert [row["family"].value() for row in authors.forms] == ["A", "B"]
        assert [row["family"].value() for row in editors.forms] == ["E"]

    def test_a_row_added_to_a_set_is_credited_in_the_sets_role(self, item):
        data = {
            "contributors-translator-TOTAL_FORMS": "1",
            "contributors-translator-INITIAL_FORMS": "0",
            "contributors-translator-0-family": "Weaver",
        }
        declaration = contributor_inline(NameRole.TRANSLATOR)(
            Item, RequestFactory().post("/", data), item, view=None
        )
        formset = declaration.construct_formset()
        assert formset.is_valid(), formset.errors
        formset.save()
        assert item.item_names.get().role == NameRole.TRANSLATOR

    def test_only_the_author_set_offers_a_blank_row_and_only_when_it_is_empty(
        self, item
    ):
        assert len(_build_formset(contributor_inline(NameRole.AUTHOR), item).forms) == 1
        assert _build_formset(contributor_inline(NameRole.EDITOR), item).forms == []
        ItemNameFactory(item=item, role=NameRole.AUTHOR)
        authors = _build_formset(contributor_inline(NameRole.AUTHOR), item)
        assert [row.instance.pk is not None for row in authors.forms] == [True]

    def test_two_new_rows_with_colliding_order_save_with_a_coherent_sequence(
        self, item
    ):
        # can_order does not itself reject a collision; renumbering turns
        # "1, 1" into a coherent sequence rather than either silently winning.
        data = {
            "contributors-author-TOTAL_FORMS": "2",
            "contributors-author-INITIAL_FORMS": "0",
            "contributors-author-0-family": "First",
            "contributors-author-0-ORDER": "1",
            "contributors-author-1-family": "Second",
            "contributors-author-1-ORDER": "1",
        }
        formset = contributor_inline(NameRole.AUTHOR)(
            Item, RequestFactory().post("/", data), item, view=None
        ).construct_formset()
        assert formset.is_valid(), formset.errors
        formset.save()
        assert sorted(item.item_names.values_list("order", flat=True)) == [0, 1]


@pytest.mark.django_db
class TestDistinctPrefixes:
    def test_declared_together_on_one_view_they_all_construct(self, item):
        # Composes InlinesMixin directly, so its own duplicate-prefix check
        # runs against every set at once.
        request = RequestFactory().get("/")

        class EverySet(InlinesMixin):
            inlines = [*CONTRIBUTOR_INLINES, IdentifierInline]
            fields = None

            def get_parent_model(self):
                return Item

        view = EverySet()
        view.object = item
        view.request = request
        formsets = view.construct_inlines()
        assert len({formset.prefix for formset in formsets}) == len(NameRole.values) + 1


@pytest.mark.django_db
class TestItemIdentifierFormSetUniqueness:
    def test_two_new_rows_claiming_the_same_kind_are_refused(self, item):
        declaration = IdentifierInline(
            Item, RequestFactory().post("/"), item, view=None
        )
        formset_class = declaration.get_formset_class()
        data = {
            "item_identifiers-TOTAL_FORMS": "2",
            "item_identifiers-INITIAL_FORMS": "0",
            "item_identifiers-MIN_NUM_FORMS": "0",
            "item_identifiers-MAX_NUM_FORMS": "1000",
            "item_identifiers-0-type": IdentifierType.DOI,
            "item_identifiers-0-value": "10.1234/first",
            "item_identifiers-1-type": IdentifierType.DOI,
            "item_identifiers-1-value": "10.1234/second",
        }
        formset = formset_class(data=data, instance=item)
        assert not formset.is_valid()
        assert formset.forms[1].errors["type"]
        assert not formset.forms[0].errors
        # The message names the limit.
        assert "DOI" in str(formset.forms[1].errors["type"])

    def test_a_deleted_rows_kind_is_excluded_from_the_collision_check(self, item):
        # Removing one identifier and adding a corrected one of the same
        # kind in the same submission is a replacement, not a collision.
        stored = ItemIdentifierFactory(
            item=item, type=IdentifierType.ISBN, value="0-306-40615-2"
        )
        declaration = IdentifierInline(
            Item, RequestFactory().post("/"), item, view=None
        )
        formset_class = declaration.get_formset_class()
        data = {
            "item_identifiers-TOTAL_FORMS": "2",
            "item_identifiers-INITIAL_FORMS": "1",
            "item_identifiers-MIN_NUM_FORMS": "0",
            "item_identifiers-MAX_NUM_FORMS": "1000",
            "item_identifiers-0-id": str(stored.pk),
            "item_identifiers-0-type": stored.type,
            "item_identifiers-0-value": stored.value,
            "item_identifiers-0-DELETE": "on",
            "item_identifiers-1-type": IdentifierType.ISBN,
            "item_identifiers-1-value": "978-0-306-40615-7",
        }
        formset = formset_class(data=data, instance=item)
        assert formset.is_valid(), formset.errors


@pytest.mark.django_db
class TestIdentifierSetAddAndRemove:
    def test_adding_an_identifier_through_the_set_stores_it(self, item):
        declaration = IdentifierInline(
            Item, RequestFactory().post("/"), item, view=None
        )
        formset_class = declaration.get_formset_class()
        data = {
            "item_identifiers-TOTAL_FORMS": "1",
            "item_identifiers-INITIAL_FORMS": "0",
            "item_identifiers-MIN_NUM_FORMS": "0",
            "item_identifiers-MAX_NUM_FORMS": "1000",
            "item_identifiers-0-type": IdentifierType.DOI,
            "item_identifiers-0-value": "10.1234/added",
        }
        formset = formset_class(data=data, instance=item)
        assert formset.is_valid(), formset.errors
        formset.save()
        assert item.item_identifiers.get().value == "10.1234/added"

    def test_removing_an_identifier_through_the_set_deletes_the_link(self, item):
        stored = ItemIdentifierFactory(
            item=item, type=IdentifierType.DOI, value="10.1234/gone"
        )
        declaration = IdentifierInline(
            Item, RequestFactory().post("/"), item, view=None
        )
        formset_class = declaration.get_formset_class()
        data = {
            "item_identifiers-TOTAL_FORMS": "1",
            "item_identifiers-INITIAL_FORMS": "1",
            "item_identifiers-MIN_NUM_FORMS": "0",
            "item_identifiers-MAX_NUM_FORMS": "1000",
            "item_identifiers-0-id": str(stored.pk),
            "item_identifiers-0-type": stored.type,
            "item_identifiers-0-value": stored.value,
            "item_identifiers-0-DELETE": "on",
        }
        formset = formset_class(data=data, instance=item)
        assert formset.is_valid(), formset.errors
        formset.save()
        assert not item.item_identifiers.exists()

    def test_a_rejected_identifiers_message_reaches_the_person_on_the_form(self, item):
        declaration = IdentifierInline(
            Item, RequestFactory().post("/"), item, view=None
        )
        formset_class = declaration.get_formset_class()
        data = {
            "item_identifiers-TOTAL_FORMS": "1",
            "item_identifiers-INITIAL_FORMS": "0",
            "item_identifiers-MIN_NUM_FORMS": "0",
            "item_identifiers-MAX_NUM_FORMS": "1000",
            "item_identifiers-0-type": IdentifierType.ISBN,
            "item_identifiers-0-value": "not-an-isbn",
        }
        formset = formset_class(data=data, instance=item)
        assert not formset.is_valid()
        assert formset.forms[0].non_field_errors()
        assert not item.item_identifiers.exists()

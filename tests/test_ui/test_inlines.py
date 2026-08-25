"""Tests for ``literature/ui/inlines.py`` — the three related-row set
declarations the reference form composes (plan.md D-2).

Declarations only at this stage: ``model``, ``fields``, ``extra``,
``can_delete``. The forms behind each row arrive in their own stories
(T006, T013, T022).
"""

import pytest
from django.test import RequestFactory
from mvp.views.inline import InlinesMixin

from literature.models import Item, ItemDate, ItemIdentifier, ItemName
from literature.ui.forms import NameForm
from literature.ui.inlines import ContributorInline, DateInline, IdentifierInline


def _build_formset(declaration_cls, item):
    """Construct the formset a declaration produces, outside of any view."""
    request = RequestFactory().get("/")
    declaration = declaration_cls(Item, request, item, view=None)
    return declaration.construct_formset()


@pytest.mark.django_db
class TestInlineDeclarations:
    """Each declaration targets one relation on ``Item`` (D-2)."""

    def test_contributor_inline_targets_item_name(self, item):
        formset = _build_formset(ContributorInline, item)
        assert formset.model is ItemName

    def test_date_inline_targets_item_date(self, item):
        formset = _build_formset(DateInline, item)
        assert formset.model is ItemDate

    def test_identifier_inline_targets_item_identifier(self, item):
        formset = _build_formset(IdentifierInline, item)
        assert formset.model is ItemIdentifier

    def test_all_three_can_delete_a_row(self, item):
        # FR-003, FR-022: a contributor/date/identifier is removable.
        for declaration_cls in (ContributorInline, DateInline, IdentifierInline):
            formset = _build_formset(declaration_cls, item)
            assert formset.can_delete is True

    def test_the_contributor_set_uses_nameform_for_its_rows(self, item):
        # T006 — replaces the fields=("role",) placeholder's bare generated
        # form with the one that also writes the linked Name.
        formset = _build_formset(ContributorInline, item)
        assert issubclass(formset.empty_form.__class__, NameForm)


@pytest.mark.django_db
class TestOrderingSpike:
    """T009's spike: prove ``can_order`` composes with a row form declaring
    unbound, non-model fields, cloned through the library's ``__prefix__``
    mechanism, before building the position column on top of it. Research
    found no working precedent for this combination.
    """

    def test_can_order_adds_an_order_field_alongside_the_unbound_name_fields(self, item):
        formset = _build_formset(ContributorInline, item)
        empty_form = formset.empty_form
        assert "ORDER" in empty_form.fields
        assert "family" in empty_form.fields
        assert "given" in empty_form.fields

    def test_the_prefix_reaches_every_field_the_same_way_custom_and_generated_alike(self, item):
        # The __prefix__ token the browser substitutes on "Add row"
        # (mvp/static/js/formset.js) is this same prefix, index-substituted.
        # If a custom declared field resolved its name/id differently from a
        # model-derived one, the clone would silently post the wrong key for
        # half the row.
        formset = _build_formset(ContributorInline, item)
        empty_form = formset.empty_form
        for field_name in ("role", "family", "given", "ORDER"):
            bound = empty_form[field_name]
            assert bound.html_name == f"item_names-__prefix__-{field_name}"
            assert bound.auto_id == f"id_item_names-__prefix__-{field_name}"

    def test_the_empty_form_renders_with_no_error(self, item):
        # Composes construction with rendering — the row template
        # (cotton/form/formset/row.html) reads every visible field off the
        # form, ORDER included, and a type mismatch or missing attribute
        # would raise here rather than merely fail an assertion.
        formset = _build_formset(ContributorInline, item)
        rendered = str(formset.empty_form)
        assert "__prefix__-family" in rendered
        assert "__prefix__-ORDER" in rendered

    def test_two_new_rows_in_one_role_with_colliding_order_save_with_a_coherent_sequence(self, item):
        # The real proof: two rows posted as if cloned via __prefix__ (index
        # 0 and 1, matching TOTAL_FORMS), both claiming position "1" — the
        # library's own can_order does not itself reject a collision, and
        # renumbering (T009's own job, not yet built at spike time) is what
        # turns "1, 1" into a coherent sequence rather than either silently
        # winning.
        formset_class = ContributorInline(Item, RequestFactory().post("/"), item, view=None).get_formset_class()
        data = {
            "item_names-TOTAL_FORMS": "2",
            "item_names-INITIAL_FORMS": "0",
            "item_names-MIN_NUM_FORMS": "0",
            "item_names-MAX_NUM_FORMS": "1000",
            "item_names-0-role": "author",
            "item_names-0-family": "First",
            "item_names-0-ORDER": "1",
            "item_names-1-role": "author",
            "item_names-1-family": "Second",
            "item_names-1-ORDER": "1",
        }
        formset = formset_class(data=data, instance=item)
        assert formset.is_valid(), formset.errors
        formset.save()
        assert set(item.item_names.values_list("name__family", flat=True)) == {"First", "Second"}


@pytest.mark.django_db
class TestDistinctPrefixes:
    """FR-005 (mvp): two declarations resolving to the same prefix raise
    ``ImproperlyConfigured``. Each of the three here targets a different
    relation on ``Item`` (D-2), so the guard must not fire.
    """

    def test_the_three_resolve_to_distinct_prefixes(self, item):
        prefixes = {
            _build_formset(ContributorInline, item).prefix,
            _build_formset(DateInline, item).prefix,
            _build_formset(IdentifierInline, item).prefix,
        }
        assert len(prefixes) == 3

    def test_declared_together_on_one_view_they_all_construct(self, item):
        # Reproduces InlinesMixin.construct_inlines()'s own duplicate-prefix
        # check (mvp/views/inline.py) against all three at once — the view
        # itself arrives in T005, so this composes InlinesMixin directly
        # rather than routing through a URL.
        request = RequestFactory().get("/")

        class ThreeInlineSets(InlinesMixin):
            inlines = [ContributorInline, DateInline, IdentifierInline]
            fields = None

            def get_parent_model(self):
                return Item

        view = ThreeInlineSets()
        view.object = item
        view.request = request
        formsets = view.construct_inlines()
        assert len(formsets) == 3
        assert {formset.model for formset in formsets} == {ItemName, ItemDate, ItemIdentifier}

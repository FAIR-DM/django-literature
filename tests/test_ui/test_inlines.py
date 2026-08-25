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

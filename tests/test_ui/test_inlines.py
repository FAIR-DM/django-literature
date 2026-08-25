"""Tests for ``literature/ui/inlines.py`` — the three related-row set
declarations the reference form composes (plan.md D-2).

Declarations only at this stage: ``model``, ``fields``, ``extra``,
``can_delete``. The forms behind each row arrive in their own stories
(T006, T013, T022).
"""

import pytest
from django.test import RequestFactory
from mvp.views.inline import InlinesMixin

from literature.choices import DateType, IdentifierType, ItemType
from literature.models import Item, ItemDate, ItemIdentifier, ItemName
from literature.ui.forms import ItemDateForm, ItemIdentifierForm, NameForm
from literature.ui.inlines import ContributorInline, DateInline, IdentifierInline
from tests.factories import ItemDateFactory, ItemIdentifierFactory


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

    def test_the_date_set_uses_itemdateform_for_its_rows(self, item):
        # T013 — replaces the fields=("date_type", "begin", "end")
        # placeholder's bare generated form with the one that declares
        # date_type itself (so it validates) and settles/narrows its choices.
        formset = _build_formset(DateInline, item)
        assert issubclass(formset.empty_form.__class__, ItemDateForm)

    def test_the_identifier_set_uses_itemidentifierform_for_its_rows(self, item):
        # T022 — replaces the fields=("type", "value") placeholder's bare
        # generated form with the one that normalizes a typed kind's casing.
        formset = _build_formset(IdentifierInline, item)
        assert issubclass(formset.empty_form.__class__, ItemIdentifierForm)


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


@pytest.mark.django_db
class TestDateInlineSlots:
    """T015 — which slots the set renders: those ``TYPE_DATE_SLOTS`` leads
    with for the reference's type, plus every slot the reference already
    holds a value in, whatever the mapping says (FR-012, FR-018, D-6).
    """

    def test_a_brand_new_item_leads_with_only_issued(self):
        # self.instance is None before a create page's type is chosen —
        # there is no type yet for TYPE_DATE_SLOTS to key on.
        declaration = DateInline(Item, RequestFactory().get("/"), None, view=None)
        assert declaration.leading_slots() == {DateType.ISSUED}

    def test_an_existing_items_leading_slots_follow_its_own_type(self, item):
        item.type = ItemType.ARTICLE_JOURNAL  # leads with available-date (research R6)
        item.save()
        declaration = DateInline(Item, RequestFactory().get("/"), item, view=None)
        assert declaration.leading_slots() == {DateType.ISSUED, DateType.AVAILABLE_DATE}

    def test_stored_slots_reads_every_date_type_the_item_actually_holds(self, item):
        ItemDateFactory(item=item, date_type=DateType.ACCESSED)
        declaration = DateInline(Item, RequestFactory().get("/"), item, view=None)
        assert declaration.stored_slots() == {DateType.ACCESSED}

    def test_a_brand_new_item_has_no_stored_slots(self):
        declaration = DateInline(Item, RequestFactory().get("/"), None, view=None)
        assert declaration.stored_slots() == frozenset()

    def test_extra_slots_are_leading_slots_with_no_stored_row_yet(self, item):
        item.type = ItemType.ARTICLE_JOURNAL
        item.save()
        ItemDateFactory(item=item, date_type=DateType.ISSUED)
        declaration = DateInline(Item, RequestFactory().get("/"), item, view=None)
        assert declaration.extra_slots == [DateType.AVAILABLE_DATE]

    def test_a_slot_outside_the_types_own_set_but_holding_a_value_still_renders(self, item):
        # FR-018 — ARTICLE leads with no extra slots of its own (DC6); a
        # stored accessed date must still appear as one of the set's forms.
        item.type = ItemType.ARTICLE
        item.save()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2020")
        formset = _build_formset(DateInline, item)
        rendered_slots = {form.instance.date_type for form in formset.forms if form.instance.pk}
        assert DateType.ACCESSED in rendered_slots

    def test_changing_item_type_never_drops_a_stored_date(self, item):
        # FR-018, D-6 — the queryset behind the set's initial forms is every
        # stored ItemDate, never filtered by the type mapping, so a slot the
        # new type does not lead with still renders.
        item.type = ItemType.ARTICLE_JOURNAL
        item.save()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2020")
        item.type = ItemType.MAP  # MAP leads with no date slots either (DC6)
        item.save()
        formset = _build_formset(DateInline, item)
        rendered_slots = {form.instance.date_type for form in formset.forms if form.instance.pk}
        assert DateType.ACCESSED in rendered_slots


@pytest.mark.django_db
class TestDateInlineCap:
    """The set stops offering rows no slot can hold: there are exactly
    ``len(DateType.choices)`` CSL date slots, and ``ItemDate``'s own
    ``unique_date_type_per_item`` constraint admits at most one row per
    slot, so the set's ``max_num`` follows the enum rather than Django's
    default of 1000.
    """

    def test_max_num_matches_the_number_of_date_slots(self, item):
        # Derived from the enum, not pinned to today's count of slots.
        formset = _build_formset(DateInline, item)
        assert formset.max_num == len(DateType.choices)

    def test_a_submission_with_more_rows_than_slots_is_refused(self, item):
        too_many = len(DateType.choices) + 1
        declaration = DateInline(Item, RequestFactory().post("/"), item, view=None)
        formset_class = declaration.get_formset_class()
        data = {
            "item_dates-TOTAL_FORMS": str(too_many),
            "item_dates-INITIAL_FORMS": "0",
            "item_dates-MIN_NUM_FORMS": "0",
            "item_dates-MAX_NUM_FORMS": "1000",
        }
        for i in range(too_many):
            data[f"item_dates-{i}-date_type"] = DateType.ISSUED
            data[f"item_dates-{i}-begin"] = "2020"
            data[f"item_dates-{i}-end"] = ""
        formset = formset_class(data=data, instance=item)
        assert not formset.is_valid()
        assert formset.non_form_errors()
        assert not item.item_dates.exists()


@pytest.mark.django_db
class TestDateInlineAddRow:
    """T015a — every remaining slot is reached by adding a row and naming
    its slot; the slot field on that added row (the set's own
    ``__prefix__`` template) offers the six CSL slots less those already on
    the page.
    """

    def test_a_type_leading_only_with_issued_offers_the_other_five_on_the_added_row(self, item):
        item.type = ItemType.MAP  # DC6 — no extra leading slots
        item.save()
        formset = _build_formset(DateInline, item)
        empty_choices = {choice[0] for choice in formset.empty_form.fields["date_type"].choices}
        assert DateType.ACCESSED in empty_choices
        assert DateType.ISSUED not in empty_choices

    def test_slots_already_on_the_page_are_not_offered_a_second_time(self, item):
        item.type = ItemType.ARTICLE_JOURNAL  # leads with issued + available-date
        item.save()
        ItemDateFactory(item=item, date_type=DateType.SUBMITTED)
        formset = _build_formset(DateInline, item)
        empty_choices = {choice[0] for choice in formset.empty_form.fields["date_type"].choices}
        assert empty_choices.isdisjoint({DateType.ISSUED, DateType.AVAILABLE_DATE, DateType.SUBMITTED})
        assert DateType.ACCESSED in empty_choices
        assert DateType.EVENT_DATE in empty_choices
        assert DateType.ORIGINAL_DATE in empty_choices

    def test_the_added_rows_slot_field_survives_prefix_cloning(self, item):
        # T015a — the added row is cloned from the set's __prefix__ template
        # in the browser: the same check T009's spike ran for the ordering
        # column applies here for the slot field.
        formset = _build_formset(DateInline, item)
        bound = formset.empty_form["date_type"]
        assert bound.html_name == "item_dates-__prefix__-date_type"
        assert bound.auto_id == "id_item_dates-__prefix__-date_type"


@pytest.mark.django_db
class TestDateSetDeletion:
    """T017 — clearing a date removes the reference's date in that slot,
    through the formset's explicit deletion rather than by the row's
    absence (FR-019, D-6).
    """

    def test_deleting_a_stored_rows_slot_removes_only_that_row(self, item):
        kept = ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        removed = ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2021")
        declaration = DateInline(Item, RequestFactory().post("/"), item, view=None)
        formset_class = declaration.get_formset_class()
        data = {
            "item_dates-TOTAL_FORMS": "2",
            "item_dates-INITIAL_FORMS": "2",
            "item_dates-MIN_NUM_FORMS": "0",
            "item_dates-MAX_NUM_FORMS": "1000",
            "item_dates-0-id": str(kept.pk),
            "item_dates-0-date_type": kept.date_type,
            "item_dates-0-begin": "2020",
            "item_dates-0-end": "",
            "item_dates-1-id": str(removed.pk),
            "item_dates-1-date_type": removed.date_type,
            "item_dates-1-begin": "2021",
            "item_dates-1-end": "",
            "item_dates-1-DELETE": "on",
        }
        formset = formset_class(data=data, instance=item)
        assert formset.is_valid(), formset.errors
        formset.save()
        assert set(item.item_dates.values_list("date_type", flat=True)) == {DateType.ISSUED}
        assert str(item.item_dates.get().begin) == "2020"


@pytest.mark.django_db
class TestItemDateFormSetUniqueness:
    """T018 — the date set validates ``(item, date_type)`` across its own
    rows in ``clean()`` and reports a collision against the offending row,
    before the database constraint can fire inside the transaction (D-8).
    """

    def test_two_new_rows_claiming_the_same_slot_are_refused(self, item):
        declaration = DateInline(Item, RequestFactory().post("/"), item, view=None)
        formset_class = declaration.get_formset_class()
        data = {
            "item_dates-TOTAL_FORMS": "2",
            "item_dates-INITIAL_FORMS": "0",
            "item_dates-MIN_NUM_FORMS": "0",
            "item_dates-MAX_NUM_FORMS": "1000",
            "item_dates-0-date_type": DateType.ACCESSED,
            "item_dates-0-begin": "2020",
            "item_dates-0-end": "",
            "item_dates-1-date_type": DateType.ACCESSED,
            "item_dates-1-begin": "2021",
            "item_dates-1-end": "",
        }
        formset = formset_class(data=data, instance=item)
        assert not formset.is_valid()
        assert formset.forms[1].errors["date_type"]
        assert not formset.forms[0].errors
        # The message names the slot (D-8).
        assert "Accessed" in str(formset.forms[1].errors["date_type"])

    def test_a_deleted_rows_slot_is_excluded_from_the_collision_check(self, item):
        # Clearing one slot's date and adding another naming the same slot
        # in the same submission is a replacement, not a collision.
        stored = ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2019")
        declaration = DateInline(Item, RequestFactory().post("/"), item, view=None)
        formset_class = declaration.get_formset_class()
        data = {
            "item_dates-TOTAL_FORMS": "2",
            "item_dates-INITIAL_FORMS": "1",
            "item_dates-MIN_NUM_FORMS": "0",
            "item_dates-MAX_NUM_FORMS": "1000",
            "item_dates-0-id": str(stored.pk),
            "item_dates-0-date_type": stored.date_type,
            "item_dates-0-begin": "2019",
            "item_dates-0-end": "",
            "item_dates-0-DELETE": "on",
            "item_dates-1-date_type": DateType.ACCESSED,
            "item_dates-1-begin": "2022",
            "item_dates-1-end": "",
        }
        formset = formset_class(data=data, instance=item)
        assert formset.is_valid(), formset.errors


@pytest.mark.django_db
class TestIdentifierKindCompletionList:
    """T022 — ``IdentifierKindWidget`` renders its completion list per row rather than once per
    page, which is safe only if each row's ``<datalist>`` carries an id of its own and the
    input beside it points at that id (the widget's own docstring asserts as much).
    """

    def test_each_rows_completion_list_carries_its_own_id(self, item):
        formset = _build_formset(IdentifierInline, item)
        first = formset.forms[0]["type"].as_widget()
        assert 'id="id_item_identifiers-0-type-kinds"' in first
        assert 'list="id_item_identifiers-0-type-kinds"' in first

    def test_the_added_rows_completion_list_survives_prefix_cloning(self, item):
        # The added row is cloned from the set's __prefix__ template in the
        # browser, which rewrites every __prefix__ in the markup at once. The
        # datalist's id and the input's list= must both carry it, or a cloned
        # row points at the template's own list instead of its own.
        rendered = _build_formset(IdentifierInline, item).empty_form["type"].as_widget()
        assert 'id="id_item_identifiers-__prefix__-type-kinds"' in rendered
        assert 'list="id_item_identifiers-__prefix__-type-kinds"' in rendered


@pytest.mark.django_db
class TestItemIdentifierFormSetUniqueness:
    """T023 — the identifier set validates a repeated kind across its own rows in ``clean()``
    and reports it against the offending row with a message naming the limit, before the
    database's own ``unique_identifier_type_per_item`` constraint can fire (D-8, FR-030).
    """

    def test_two_new_rows_claiming_the_same_kind_are_refused(self, item):
        declaration = IdentifierInline(Item, RequestFactory().post("/"), item, view=None)
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
        # The message names the limit (D-8, FR-030).
        assert "DOI" in str(formset.forms[1].errors["type"])

    def test_a_deleted_rows_kind_is_excluded_from_the_collision_check(self, item):
        # Removing one identifier and adding a corrected one of the same
        # kind in the same submission is a replacement, not a collision.
        stored = ItemIdentifierFactory(item=item, type=IdentifierType.ISBN, value="0-306-40615-2")
        declaration = IdentifierInline(Item, RequestFactory().post("/"), item, view=None)
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
    """T024 — adding and removing identifiers through the set (FR-021, FR-022), and a rejected
    identifier's message reaches the person on the form (FR-026).
    """

    def test_adding_an_identifier_through_the_set_stores_it(self, item):
        declaration = IdentifierInline(Item, RequestFactory().post("/"), item, view=None)
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
        stored = ItemIdentifierFactory(item=item, type=IdentifierType.DOI, value="10.1234/gone")
        declaration = IdentifierInline(Item, RequestFactory().post("/"), item, view=None)
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
        declaration = IdentifierInline(Item, RequestFactory().post("/"), item, view=None)
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

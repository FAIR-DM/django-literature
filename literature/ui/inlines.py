"""The three related-row set declarations the reference form composes (plan.md D-2).

Each targets a different relation on ``Item`` — ``ItemName``, ``ItemDate`` and
``ItemIdentifier`` — so the default per-relation prefixes
``mvp.views.inline.InlinesMixin.construct_inlines()`` resolves are distinct and
its duplicate-prefix guard never fires.

Declarations only at this stage: ``model``, ``fields``, ``extra`` and
``can_delete``. The custom forms behind each row — ``NameForm`` and the
position column (contributors story), ``ItemDateForm`` (dates story) and
``ItemIdentifierForm`` (identifiers story) — replace the bare field lists
below with their own ``form=`` in their own stories.
"""

from collections import defaultdict
from functools import cached_property

from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from mvp.views.inline import InlineFormSet

from literature.choices import DateType
from literature.models import ItemDate, ItemIdentifier, ItemName
from literature.ui.fieldgroups import TYPE_DATE_SLOTS
from literature.ui.forms import ItemDateForm, NameForm


class ContributorFormSet(BaseInlineFormSet):
    """Renumbers ``ItemName.order`` to a coherent ``(item, role)`` sequence
    on save (plan.md D-4, T009).

    ``can_order=True`` (below) adds an ``ORDER`` field to every row, reached
    at ``cleaned_data["ORDER"]``; ``ItemName.order`` is ``editable=False``,
    so no ``ModelForm`` ever writes it — this is the one place that does,
    after every row is otherwise saved, so a submission of 1, 1, 3 within
    one role becomes a coherent 0, 1, 2 rather than being rejected (FR-004).
    """

    def add_fields(self, form, index):
        super().add_fields(form, index)
        # Seeds the position control from the row's own current order, not
        # BaseFormSet's own default — a row's position in the *whole*
        # rendered set, which disagrees with its role-scoped order the
        # moment a page holds more than one role.
        if form.instance.pk:
            form.initial.setdefault("ORDER", form.instance.order)

    def save(self, commit=True):
        saved = super().save(commit=commit)
        self.renumber()
        return saved

    def renumber(self):
        """Group every surviving row by role and renumber each group's
        positions to a coherent 0-based sequence, in the order the
        submitted ``ORDER`` values place them.

        "Surviving" excludes a row flagged for deletion and one that was
        never filled in (an extra row with no saved instance) — neither
        holds a position to renumber.
        """
        by_role = defaultdict(list)
        for form in self.forms:
            instance = form.instance
            if not instance.pk or form in self.deleted_forms:
                continue
            by_role[instance.role].append((form.cleaned_data.get("ORDER") or 0, instance))

        for entries in by_role.values():
            entries.sort(key=lambda pair: pair[0])
            for position, entry in enumerate(entries):
                instance = entry[1]
                if instance.order != position:
                    instance.order = position
                    instance.save(update_fields=["order"])


class ContributorInline(InlineFormSet):
    """A reference's contributors, one row per ``ItemName`` link (FR-001)."""

    model = ItemName
    form = NameForm
    formset = ContributorFormSet
    fields = ("role",)
    extra = 1
    can_delete = True
    title = _("Contributors")

    # Django's own escape hatch (D-4, D-13, research R3) — django-mvp has no
    # reordering support of its own and deliberately dropped its Alpine sort
    # plugin, so a drag affordance would mean a custom component this
    # feature is not allowed to write. can_order adds an ORDER field to
    # every row (an ordinary number input, one more column heading under
    # the tabular layout); ItemName.order itself stays editable=False and
    # is never in the form's own Meta.fields.
    factory_kwargs = {"can_order": True}

    def sort_forms(self, forms):
        """Bring a role's rows adjacent for display (D-4, D-13, T009).

        Display only, per the base class's own contract — it must never
        reach save(), since reordering that would change which submitted
        row maps to which record. A contributor row spans one of 26 roles,
        and this set holds every role's rows on one page; an ungrouped list
        shows positions running 0, 0, 1, 2, 0 and reads as broken.
        """
        return sorted(forms, key=lambda form: (form.instance.role or "", form.instance.pk or 0))


class ItemDateFormSet(BaseInlineFormSet):
    """Refuses two rows of one set claiming the same CSL date slot, before
    the database's own ``unique_date_type_per_item`` constraint can fire
    inside the save transaction (D-8, T018).

    A row flagged for deletion is excluded from the check: clearing one
    slot's date and adding another in the same submission is a
    replacement, not a collision.

    Does not call ``super().clean()``: ``BaseModelFormSet.clean()``'s own
    ``validate_unique()`` already catches this exact collision (against
    ``ItemDate``'s ``unique_date_type_per_item`` constraint) before this
    method would even run, reporting it as a bare "Please correct the
    duplicate values below" on the row's ``__all__`` and deleting
    ``date_type`` from its ``cleaned_data`` in the process — which is both
    the wrong message (D-8 asks for one naming the slot) and would leave
    nothing here to detect a second time. This replaces that check
    entirely rather than running alongside it.
    """

    def clean(self):
        if any(self.errors):
            # A row with a field error of its own has nothing reliable in
            # cleaned_data to compare — the same guard BaseModelFormSet's
            # own uniqueness check uses.
            return
        slot_labels = dict(DateType.choices)
        seen_by_slot = {}
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue
            date_type = form.cleaned_data.get("date_type")
            if not date_type:
                continue
            if date_type in seen_by_slot:
                form.add_error(
                    "date_type",
                    ValidationError(
                        _("This reference already has a %(slot)s date."),
                        code="duplicate_date_type",
                        params={"slot": slot_labels.get(date_type, date_type)},
                    ),
                )
            else:
                seen_by_slot[date_type] = form


class DateInline(InlineFormSet):
    """A reference's dates, one row per ``ItemDate`` slot (FR-012, T015).

    The set does not fix ``extra`` at the class level — how many blank rows
    it pre-renders, and for which slots, depends on the reference's own
    type and what it already has stored, so both are computed per instance
    below and threaded through the two-phase construction
    (``get_factory_kwargs``/``get_formset_kwargs``) ``InlineFormSet``
    itself documents.
    """

    model = ItemDate
    form = ItemDateForm
    formset = ItemDateFormSet
    can_delete = True
    title = _("Dates")

    def leading_slots(self):
        """The slots a blank row is pre-rendered for: ``issued`` always,
        plus whatever ``TYPE_DATE_SLOTS`` leads with for the reference's
        own type (T015, D-6).

        ``self.instance`` is ``None`` on a create page's first GET, before
        any type is chosen — ``TYPE_DATE_SLOTS.get(None, ...)`` then falls
        through to the empty set the same way
        ``FieldGroups.groups_for`` already tolerates an unrecognised type,
        so only ``issued`` renders until the reference exists to have a
        type of its own.
        """
        item_type = getattr(self.instance, "type", None)
        return frozenset({DateType.ISSUED}) | TYPE_DATE_SLOTS.get(item_type, frozenset())

    def stored_slots(self):
        """The slots the reference already holds a row for, whatever the
        type mapping says (T015, FR-018)."""
        if self.instance is None or self.instance.pk is None:
            return frozenset()
        return frozenset(self.instance.item_dates.values_list("date_type", flat=True))

    @cached_property
    def extra_slots(self):
        """Leading slots with no stored row yet — the blank rows this set
        pre-renders beyond its queryset (T015). Sorted so the factory's
        ``extra`` count and the formset's own ``initial`` list line up by
        index every time the two are built from this same instance.
        """
        return sorted(self.leading_slots() - self.stored_slots())

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs["extra"] = len(self.extra_slots)
        return kwargs

    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        kwargs["initial"] = [{"date_type": slot} for slot in self.extra_slots]
        return kwargs

    def get_form_kwargs(self, index):
        """Thread the slots already on the page through to every row form,
        so an unsettled (add-row) ``ItemDateForm`` narrows its own choices
        to what T015a asks for (T015a)."""
        kwargs = super().get_form_kwargs(index)
        kwargs["occupied_slots"] = self.stored_slots() | self.leading_slots()
        return kwargs


class IdentifierInline(InlineFormSet):
    """A reference's identifiers, one row per ``ItemIdentifier`` (FR-021)."""

    model = ItemIdentifier
    fields = ("type", "value")
    extra = 1
    can_delete = True
    title = _("Identifiers")

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

from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from mvp.views.inline import InlineFormSet

from literature.models import ItemDate, ItemIdentifier, ItemName
from literature.ui.forms import NameForm


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


class DateInline(InlineFormSet):
    """A reference's dates, one row per ``ItemDate`` slot (FR-012)."""

    model = ItemDate
    fields = ("date_type", "begin", "end")
    extra = 1
    can_delete = True
    title = _("Dates")


class IdentifierInline(InlineFormSet):
    """A reference's identifiers, one row per ``ItemIdentifier`` (FR-021)."""

    model = ItemIdentifier
    fields = ("type", "value")
    extra = 1
    can_delete = True
    title = _("Identifiers")

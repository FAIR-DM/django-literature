"""The related-row set declarations the reference form composes.

One contributor set per role (``CONTRIBUTOR_INLINES``), each over ``ItemName``
with a prefix of its own, ``contributors-<role>``, and one identifier set over
``ItemIdentifier``. Dates are not a set: each date slot is a field of
``ItemForm`` (docs/adr/0034-a-date-slot-is-a-field-of-the-form.md).

Each row's own form does the work particular to its relation: ``NameForm`` and
the position column for contributors, ``ItemIdentifierForm`` for identifiers.
"""

from collections import defaultdict

from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from mvp.views.inline import InlineFormSet

from literature.choices import NameRole
from literature.models import ItemIdentifier, ItemName
from literature.ui.contributors import ContributorGroups
from literature.ui.fieldgroups import ROLE_ORDER
from literature.ui.forms import ItemIdentifierForm, NameForm


class ContributorFormSet(BaseInlineFormSet):
    """Renumbers ``ItemName.order`` to a coherent ``(item, role)`` sequence on save.

    ``can_order=True`` (below) adds an ``ORDER`` field to every row, reached
    at ``cleaned_data["ORDER"]``; ``ItemName.order`` is ``editable=False``,
    so no ``ModelForm`` ever writes it — this is the one place that does,
    after every row is otherwise saved, so a submission of 1, 1, 3 within
    one role becomes a coherent 0, 1, 2 rather than being rejected.
    """

    def add_fields(self, form, index):
        """Seed the position control from the row's own role-scoped order."""
        super().add_fields(form, index)
        # Not BaseFormSet's own default — a row's position in the *whole*
        # rendered set, which disagrees with its role-scoped order the
        # moment a page holds more than one role.
        if form.instance.pk:
            form.initial.setdefault("ORDER", form.instance.order)

    def save(self, commit=True):
        """Save every row, then renumber each role's positions to a coherent sequence."""
        saved = super().save(commit=commit)
        self.renumber()
        return saved

    def renumber(self):
        """Group every surviving row by role and renumber each group's positions to a coherent 0-based sequence.

        Positions follow the order the submitted ``ORDER`` values place them in.

        "Surviving" excludes a row flagged for deletion and one that was
        never filled in (an extra row with no saved instance) — neither
        holds a position to renumber.
        """
        by_role = defaultdict(list)
        for form in self.forms:
            instance = form.instance
            if not instance.pk or form in self.deleted_forms:
                continue
            by_role[instance.role].append(
                (form.cleaned_data.get("ORDER") or 0, instance)
            )

        for entries in by_role.values():
            entries.sort(key=lambda pair: pair[0])
            for position, entry in enumerate(entries):
                instance = entry[1]
                if instance.order != position:
                    instance.order = position
                    instance.save(update_fields=["order"])


class ContributorInline(InlineFormSet):
    """A reference's contributors in one role, one row per ``ItemName`` link.

    One set per role (``CONTRIBUTOR_INLINES`` below), so a row's role is the
    set it sits in, and its position is its place in that set.
    """

    model = ItemName
    form = NameForm
    formset = ContributorFormSet
    fields = ()
    extra = 0
    can_delete = True

    #: The role every row of this set holds. Set by each subclass.
    role = ""

    # Django's own escape hatch: can_order adds an ORDER field to every row,
    # which the page writes from the row's place on screen. ItemName.order
    # itself stays editable=False and is never in the form's own Meta.fields.
    factory_kwargs = {"can_order": True}

    def get_title(self):
        """Name the set by its role, in the plural."""
        return ContributorGroups.role_label(self.role, 2)

    def get_formset_kwargs(self):
        """Hold only this role's rows."""
        kwargs = super().get_formset_kwargs()
        kwargs["queryset"] = ItemName.objects.filter(role=self.role).select_related(
            "name"
        )
        return kwargs

    def get_form_kwargs(self, index):
        """Give every row, the blank template included, this set's role."""
        return {**super().get_form_kwargs(index), "role": self.role}

    def get_factory_kwargs(self):
        """Offer one blank author row to a reference with no authors yet."""
        kwargs = super().get_factory_kwargs()
        if self.role == NameRole.AUTHOR and not (
            self.instance is not None
            and self.instance.pk
            and self.instance.item_names.filter(role=self.role).exists()
        ):
            kwargs["extra"] = 1
        return kwargs

    def sort_forms(self, forms):
        """Show rows in their credited order, new rows last. Display only."""
        return sorted(
            forms,
            key=lambda form: (
                form.instance.pk is None,
                form.instance.order if form.instance.pk else 0,
            ),
        )


CONTRIBUTOR_INLINES = [
    type(
        f"ContributorInline_{role.replace('-', '_')}",
        (ContributorInline,),
        {"role": role, "prefix": f"contributors-{role}"},
    )
    for role in ROLE_ORDER
]


class ItemIdentifierFormSet(BaseInlineFormSet):
    """Refuses two rows of one set claiming the same identifier kind, before the database's own ``unique_identifier_type_per_item`` constraint can fire inside the save transaction.

    A row flagged for deletion is excluded from the check: removing one identifier and adding
    a corrected one of the same kind in the same submission is a replacement, not a collision.

    Does not call ``super().clean()``, for the same reason :class:`ItemDateFormSet` does not
    (see its own docstring): ``BaseModelFormSet.clean()``'s own ``validate_unique()`` already
    catches this exact collision against ``ItemIdentifier``'s ``unique_identifier_type_per_item``
    constraint before this method would even run, reporting it as a bare "Please correct the
    duplicate values below" on the row's ``__all__`` and deleting ``type`` from its
    ``cleaned_data`` in the process — both the wrong message (this feature wants one naming the
    limit) and something that would leave nothing here to detect a second time. This replaces
    that check entirely rather than running alongside it.
    """

    def clean(self):
        """Report a row naming an identifier kind another surviving row already claims."""
        if any(self.errors):
            # A row with a field error of its own has nothing reliable in
            # cleaned_data to compare — the same guard BaseModelFormSet's
            # own uniqueness check uses.
            return
        seen_by_kind = {}
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue
            kind = form.cleaned_data.get("type")
            if not kind:
                continue
            if kind in seen_by_kind:
                form.add_error(
                    "type",
                    ValidationError(
                        _("This reference already has a %(kind)s identifier."),
                        code="duplicate_identifier_type",
                        params={"kind": kind},
                    ),
                )
            else:
                seen_by_kind[kind] = form


class IdentifierInline(InlineFormSet):
    """A reference's identifiers, one row per ``ItemIdentifier`` (FS-012, #117)."""

    model = ItemIdentifier
    form = ItemIdentifierForm
    formset = ItemIdentifierFormSet
    extra = 1
    can_delete = True
    title = _("Identifiers")

    def get_factory_kwargs(self):
        """Offer a blank row only to a reference with no identifiers yet."""
        kwargs = super().get_factory_kwargs()
        if (
            self.instance is not None
            and self.instance.pk
            and self.instance.item_identifiers.exists()
        ):
            kwargs["extra"] = 0
        return kwargs

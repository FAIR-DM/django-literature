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

from django.utils.translation import gettext_lazy as _
from mvp.views.inline import InlineFormSet

from literature.models import ItemDate, ItemIdentifier, ItemName


class ContributorInline(InlineFormSet):
    """A reference's contributors, one row per ``ItemName`` link (FR-001)."""

    model = ItemName
    fields = ("role",)
    extra = 1
    can_delete = True
    title = _("Contributors")


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

"""The one write form every create/update flow shares (plan.md D-3, D-4).

Scoping by item type is the template's job, never the form's: ``ItemForm``
declares every scalar field, always, so a group the current type does not use
still renders (hidden by Alpine's ``x-show``, which leaves the element in the
DOM) and still posts the value it already held. Building the form's field
list from the type instead would make ``ModelForm.construct_instance()``
write every omitted field as empty rather than leaving it alone — the
opposite of the no-loss guarantee this feature exists for (D-3).
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from literature.choices import IdentifierType
from literature.importers import available_formats
from literature.models import Item, ItemDate, ItemIdentifier, ItemName, Name
from literature.ui.fieldgroups import GROUPS

#: Every field ``ItemForm`` declares: every scalar field of ``Item`` except
#: ``categories``, ``custom``, ``created`` and ``modified`` (D-4). Built from
#: the field-group mapping's own partition rather than restated by hand, so
#: the two artefacts cannot drift apart — ``fieldgroups.py`` already proves
#: this set is exactly ``Item``'s form fields
#: (``tests/test_ui/test_fieldgroups.py::TestFieldPartition``).
FORM_FIELDS = tuple(sorted(name for fields in GROUPS.values() for name in fields))


class ItemForm(forms.ModelForm):
    """Every scalar field of ``Item``, always.

    Labels and help text are not restated here: every field already carries
    a translated ``verbose_name`` and ``help_text`` on the model (Article
    VIII), and ``ModelForm`` reads both by default.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django's CharField strips surrounding whitespace by default, which
        # quietly rewrites a stored value on a save that changed nothing —
        # an abstract ending in a newline loses it, a title stored with
        # padding comes back trimmed. SC-003 promises a save with no changes
        # leaves the record byte-identical, and the CSL JSON import path does
        # not strip, so such values do reach the store. Turning it off here
        # is what makes the promise true of every value rather than of the
        # ones that happen not to have edges.
        for field in self.fields.values():
            if isinstance(field, forms.CharField):
                field.strip = False

    class Meta:
        model = Item
        fields = FORM_FIELDS
        widgets = {
            "type": forms.Select(
                attrs={
                    "x-model": "form.itemType",
                    # cotton/form/index.html opens x-data="{form: {}}" on the
                    # <form> element with an empty object, and this form is
                    # rendered inside it — there is no seam that seeds the
                    # scope from self.object.type. Without x-init, x-model
                    # writes its own undefined state onto the select at
                    # initialisation: the edit page would render with no
                    # type selected, and saving would then fail validation
                    # because type is required (plan.md D-3, research.md §2).
                    "x-init": "form.itemType = $el.value",
                }
            ),
        }


#: The id shared between the family-name input's ``list=`` attribute and the
#: page-level ``<datalist>`` it references (plan.md D-1, D-12, T008). Defined
#: here rather than in ``views.py`` so the form and the context that supplies
#: the datalist's own options cannot name two different ids.
CONTRIBUTOR_NAMES_DATALIST_ID = "contributor-names-datalist"


class NameForm(forms.ModelForm):
    """A contributor row: an ``ItemName`` link whose form also carries the
    ``Name`` it points at (plan.md D-3, T006).

    ``ItemName`` carries ``item``, ``name``, ``role`` and ``order``; the
    person types into ``Name``. This form is declared over ``ItemName`` —
    ``role`` is its one model field — and declares the name's own parts as
    fields of its own, unbound to ``ItemName`` (D-3). ``save()`` (T007,
    T007a) is what turns them into a stored ``Name``; ``order`` is excluded
    on purpose, since it is ``editable=False`` and no generated form can
    carry it at all (D-4) — the position column arrives through the
    formset's own ``can_order`` escape hatch instead (T009).

    Each name-part field is built from ``Name``'s own field via
    ``formfield()`` rather than restated here, so the label and help text
    stay the model's own translated copy (Article VIII). Family and given
    are the row's own columns (FR-009); the particles, the suffix and the
    unparsed organizational form ship as ordinary columns beside them too —
    the row-level disclosure that would fold them out of sight does not
    exist in the packaged formset component and waits on a django-mvp
    release that carries one (T012a, decisions.md D15). The three
    citation-processor flags — ``comma_suffix``, ``static_ordering``,
    ``parse_names`` — are never declared, so nothing here can write them and
    their stored values are preserved exactly (FR-010).
    """

    class Meta:
        model = ItemName
        fields = ("role",)

    family = Name._meta.get_field("family").formfield(
        widget=forms.TextInput(attrs={"list": CONTRIBUTOR_NAMES_DATALIST_ID})
    )
    given = Name._meta.get_field("given").formfield()
    dropping_particle = Name._meta.get_field("dropping_particle").formfield()
    non_dropping_particle = Name._meta.get_field("non_dropping_particle").formfield()
    suffix = Name._meta.get_field("suffix").formfield()
    literal = Name._meta.get_field("literal").formfield()

    #: The fields that make up a ``Name``, in the order T007/T007a compare
    #: and write them. Declared once so ``save()`` and ``__init__`` cannot
    #: drift onto two different sets.
    NAME_FIELDS = ("family", "given", "dropping_particle", "non_dropping_particle", "suffix", "literal")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Seeding initial from the linked Name is what makes an unedited row
        # round-trip unchanged (FR-034): without it, every field would start
        # from ModelForm's own blank default and a save that touched nothing
        # would read as a submission clearing every name part.
        if self.instance.pk and self.instance.name_id:
            name = self.instance.name
            for field_name in self.NAME_FIELDS:
                self.initial.setdefault(field_name, getattr(name, field_name))

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("DELETE"):
            # A row marked for removal carries whatever it last held; nothing
            # about a name it is dropping needs to satisfy this rule.
            return cleaned_data
        family = cleaned_data.get("family", "")
        literal = cleaned_data.get("literal", "")
        if not family and not literal:
            raise forms.ValidationError(
                _("A contributor needs a family name or an unparsed name."),
                code="name_required",
            )
        return cleaned_data

    def save(self, commit=True):
        """Write ``role`` onto the link and the name parts onto a ``Name``
        (T007, T007a, D-3).

        A new link (no stored ``ItemName`` yet) always creates a new
        ``Name`` — entry never reuses a stored record, whether or not an
        identical one already exists (FR-006, FR-007). Editing an existing
        link carries a narrower rule: a submission that leaves the name
        parts unchanged writes nothing (this method is not even reached in
        that case — ``has_changed()`` keeps the formset from calling it).
        A submission that does change them updates the linked ``Name`` in
        place only when nothing else credits it; when something else does,
        rewriting it in place would silently rename that contributor on
        every other reference holding it, so a new ``Name`` is created and
        the link is repointed instead, leaving the original untouched
        (T007a, SC-002).
        """
        item_name = super().save(commit=False)
        submitted = {field: self.cleaned_data.get(field, "") for field in self.NAME_FIELDS}

        if item_name.name_id is None:
            item_name.name = self.create_name(submitted)
        else:
            linked_name = item_name.name
            stored = {field: getattr(linked_name, field) for field in self.NAME_FIELDS}
            if submitted != stored:
                shared_elsewhere = linked_name.item_names.exclude(pk=item_name.pk).exists()
                if shared_elsewhere:
                    item_name.name = self.create_name(submitted)
                else:
                    for field, value in submitted.items():
                        setattr(linked_name, field, value)
                    linked_name.full_clean()
                    linked_name.save()

        if commit:
            item_name.save()
        return item_name

    @staticmethod
    def create_name(values):
        name = Name(**values)
        name.full_clean()
        name.save()
        return name


class SetPolicedConstraintMixin:
    """Leaves one named model constraint to the row's own formset, which is
    the only party that can judge it correctly (D-8, D19).

    A row form validates its instance against the model's constraints on its
    own, one row at a time, and against the database as it stands right now.
    That is the wrong vantage point for a constraint the set polices across
    all of its rows. Clearing one slot's value and adding another row naming
    the same slot in the same submission is a replacement rather than a
    collision, but the row doing the adding cannot see that the row holding
    that slot is flagged for removal — the removal has not happened yet, so
    the stored row is still there to be found, and the addition is refused
    for colliding with a row that is on its way out.

    Django's own cross-row check has the same shape and the same escape: it
    skips forms flagged for deletion. Only the set can do that, so the set is
    where this belongs. ``clean()`` on each formset below performs the check
    over the rows actually being kept, reports it against the offending row
    with a message naming what collided, and the database constraint stays as
    the final backstop.

    Named ``constraint_field`` rather than the constraint itself because
    excluding any one of a constraint's fields skips that constraint and
    leaves every other one on the model still validated, so a check
    constraint added later is unaffected by this.
    """

    #: A field of the constraint the set polices. Excluding it skips exactly
    #: that constraint.
    constraint_field: str

    def validate_constraints(self):
        """Mirror ``BaseModelForm.validate_constraints`` with the set-policed
        constraint's own field excluded.

        Only Django 6.0 and later call this: 5.2 validates constraints inside
        ``Model.full_clean()`` during ``_post_clean``, where this row's
        exclusions already covered the constraint. Defining it on 5.2 is
        harmless, since nothing calls it there.
        """
        exclude = self._get_validation_exclusions() | {self.constraint_field}
        try:
            self.instance.validate_constraints(exclude=exclude)
        except ValidationError as e:
            self._update_errors(e)


class ItemDateForm(SetPolicedConstraintMixin, forms.ModelForm):
    """A date-slot row: one ``ItemDate`` reachable through the reference
    form's dates set (plan.md D-6, T013).

    Declares ``date_type`` alongside ``begin`` and ``end`` and nothing
    else, so everything else ``ItemDate`` carries — season, circa,
    literal, raw, raw date parts — is never written by a save through this
    form (FR-017). ``date_type`` earns its place for two reasons rather
    than one: it is what lets an added row name a slot the reference's
    type does not lead with (T015a), and it is what gets the value
    validated at all — ``ModelForm``'s ``_post_clean`` excludes undeclared
    fields from ``full_clean``, so a row cloned from the set's own
    ``__prefix__`` template with an undeclared ``date_type`` would
    otherwise save an empty slot the model's own choices check would have
    refused.

    ``begin``/``end`` are left to ``ModelForm``'s own default field for
    ``PartialDateField`` — a plain ``CharField``/``TextInput``, since the
    field defines no ``formfield()`` of its own (research R5) — which is
    already what accepts a year, a year and month, or a full date with no
    precision declared beforehand (FR-014), and what a stored value
    renders back as (the canonical string that re-parses to the same
    value).

    A row is "settled" — its slot fixed rather than offered as a choice —
    when it edits a stored ``ItemDate`` or was pre-filled for a slot the
    reference's type leads with
    (:meth:`~literature.ui.inlines.DateInline.leading_slots`, T015). In
    both cases ``date_type`` is marked ``disabled`` rather than replaced
    with a hidden input: Django reads a disabled field's value from
    ``initial`` rather than the submission, which carries the same
    guarantee a hidden input would — the slot cannot be changed from the
    page — while keeping the field a *visible* one for
    ``cotton/form/formset/index.html``'s tabular layout, whose column
    headings and grid tracks are read from the row with no slot settled
    (``formset.empty_form``). A literal ``HiddenInput`` renders outside
    that grid entirely (``cotton/form/formset/row.html`` renders hidden
    fields ahead of it, not inside it), which would misalign every settled
    row's ``begin``/``end`` cells by one column — a gap in the packaged
    component this feature works around rather than forks (see this
    story's completion report). Disabling the field is the closest
    supported way to carry the slot's own plain-language label: the option
    text a disabled ``<select>`` still renders.

    An unsettled row — the set's own ``__prefix__`` template, cloned by
    "Add row" (T015a) — instead narrows ``date_type``'s choices to the six
    CSL slots less ``occupied_slots``, the ones already on the page,
    computed by :class:`~literature.ui.inlines.DateInline` and passed in
    through ``get_form_kwargs`` so the cloned template's choices agree
    with what the page actually rendered.
    """

    constraint_field = "date_type"

    class Meta:
        model = ItemDate
        fields = ("date_type", "begin", "end")

    def __init__(self, *args, occupied_slots=frozenset(), **kwargs):
        super().__init__(*args, **kwargs)
        settled_type = self.instance.date_type if self.instance.pk else self.initial.get("date_type")
        if settled_type:
            self.fields["date_type"].disabled = True
        else:
            self.fields["date_type"].choices = [
                choice for choice in self.fields["date_type"].choices if choice[0] not in occupied_slots
            ]
        # T016 (FR-018) — a stored date whose only content is unparsed has
        # nothing in begin/end for the person to see. Showing that content
        # as begin's own placeholder makes it visible — and repairable, by
        # typing over it — without writing it anywhere the form does not
        # already reach on save (FR-017): a placeholder is never submitted,
        # so leaving it untouched stores nothing and literal/raw stay
        # exactly as they were.
        if self.instance.pk and not self.instance.begin and not self.instance.end:
            unparsed = self.instance.literal or self.instance.raw
            if unparsed:
                self.fields["begin"].widget.attrs["placeholder"] = unparsed


class IdentifierKindWidget(forms.TextInput):
    """A text input completing from the package's six known identifier kinds (FR-023, T022).

    The same native ``<datalist>`` shape D-1/D-12 chose for a contributor's name: accepting a
    completion asserts the kind's spelling, and a value not among the six is equally acceptable
    (FR-024) — the model's own ``type`` field carries no ``choices=`` for exactly that reason
    (ADR-0002). Unlike the contributor list (T008), the six kinds are static rather than read
    from the catalogue, so this widget renders its own ``<datalist>`` sibling on every row
    rather than referencing one page-level element built from a view-supplied queryset — each
    row already carries its own unique id from the formset's own numbering
    (``id_item_identifiers-0-type``, ``-1-type``, ...), so a sibling ``<datalist>`` keyed off
    that same id never collides with another row's.
    """

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget_id = context["widget"]["attrs"].get("id") or f"id_{name}"
        context["datalist_id"] = f"{widget_id}-kinds"
        context["widget"]["attrs"]["list"] = context["datalist_id"]
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        input_html = self._render(self.template_name, context, renderer)
        options = format_html_join(
            "",
            '<option value="{}">',
            ((kind,) for kind in IdentifierType.values),
        )
        return format_html('{}<datalist id="{}">{}</datalist>', input_html, context["datalist_id"], options)


class ItemIdentifierForm(SetPolicedConstraintMixin, forms.ModelForm):
    """An identifier row: one ``ItemIdentifier`` reachable through the reference form's
    identifiers set (plan.md D-9, T022).

    Declares ``type`` and ``value``, ``ItemIdentifier``'s only two fields besides the ``item``
    foreign key the identifier set itself supplies (FR-021). ``type`` carries no model-level
    ``choices=`` — an unknown kind is stored and left unchecked by design (ADR-0002, FR-024) —
    so the six known kinds (:class:`~literature.choices.IdentifierType`) are offered through
    :class:`IdentifierKindWidget`'s completion list rather than restricted to them (FR-023).

    Normalization happens here, not in :func:`~literature.validators.validate_identifier`'s
    dispatch dict (D-9): a typed kind matching one of the six known kinds other than by casing
    is cleaned to its canonical acronym before it ever reaches the model, so ``isbn`` is checked
    as ``ISBN`` (FR-025), while a kind matching none of them passes through untouched and
    unchecked, exactly as it does today (FR-029). Changing the dispatch dict instead would also
    normalize the import path's own lookups, which this feature does not touch and FR-029
    protects.

    Format checking itself is not this form's own job: ``ItemIdentifier.clean()``/``save()``
    already call ``validate_identifier(self.type, self.value)`` (``literature/models.py``),
    which ``ModelForm._post_clean()`` runs through ``full_clean()``. That call raises a plain
    ``ValidationError`` rather than one keyed by field, so a rejection surfaces as a non-field
    error — the same shape :class:`ItemDateForm`'s span rejections take — carrying whichever
    message ``literature/validators.py`` raised (FR-026).
    """

    constraint_field = "type"

    class Meta:
        model = ItemIdentifier
        fields = ("type", "value")
        widgets = {"type": IdentifierKindWidget}

    def clean_type(self):
        """Normalize a typed kind matching a known one other than by casing to its canonical
        acronym (FR-025, D-9). A kind matching none of the six passes through exactly as typed
        (FR-024)."""
        value = self.cleaned_data["type"]
        for known in IdentifierType.values:
            if value.casefold() == known.casefold():
                return known
        return value


class ImportForm(forms.Form):
    """Choose a configured format and a file to run it through (US-1, FR-005, FR-006).

    Not a ``ModelForm``: nothing here maps to ``Item``, the format resolves
    the file into entries and the entries into items, never this form
    (FR-010 — the front end has no reading path of its own).
    """

    format = forms.ChoiceField(
        label=_("Format"),
        help_text=_("The bibliographic file syntax to read the upload as."),
    )
    file = forms.FileField(
        label=_("File"),
        help_text=_("The bibliography file to import."),
    )
    skip_preview = forms.BooleanField(
        label=_("Skip the preview and import immediately"),
        help_text=_("Import the file in one step, without a preview to confirm first."),
        required=False,
        initial=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Read at __init__ time, not declared on the class: a ChoiceField
        # built from available_formats() at class-definition time would
        # freeze the set at import time, and a format configured afterwards
        # would never appear (FR-005).
        self.fields["format"].choices = [
            (name, format_class.label) for name, format_class in available_formats().items()
        ]


class ConfirmImportForm(forms.Form):
    """Carry out the import a preview described (US-4, FR-041, FR-042).

    The staged file's token and the format it was staged as both live in the
    reader's own session, never in this form — the whole point of FR-042 is
    that nothing on this page can name someone else's staged upload
    (decisions.md D16).

    The one field it does declare names which preview the page was showing.
    That is not the same thing: on its own it reaches nothing, because the
    view checks it against the confirming session's own value and imports
    only where the two agree. What it prevents is a page still showing an
    earlier preview carrying out a later one (decisions.md D28).
    """

    preview = forms.CharField(widget=forms.HiddenInput, required=False)

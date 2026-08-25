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
from django.utils.translation import gettext_lazy as _

from literature.importers import available_formats
from literature.models import Item, ItemName, Name
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

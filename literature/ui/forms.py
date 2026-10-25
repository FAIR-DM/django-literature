"""The one write form every create/update flow shares (FS-008, #74).

Scoping by item type is the template's job, never the form's: ``ItemForm``
declares every scalar field, always, so a group the current type does not use
still renders (hidden by Alpine's ``x-show``, which leaves the element in the
DOM) and still posts the value it already held. Building the form's field
list from the type instead would make ``ModelForm.construct_instance()``
write every omitted field as empty rather than leaving it alone — the
opposite of the no-loss guarantee this feature exists for.
"""

import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from mvp_forms.fields import PartialDateField
from mvp_forms.widgets import PartialDateInput, TomSelect, TomSelectMultiple
from partial_date import PartialDate

from literature.choices import IdentifierType
from literature.importers import available_formats
from literature.models import Item, ItemDate, ItemIdentifier, ItemName, Name
from literature.ui.fieldgroups import GROUPS
from literature.ui.formlayout import (
    DATE_SLOTS,
    FIELD_HELP,
    FIELD_LABELS,
    TYPE_CHOICE_GROUPS,
    ItemFormLayout,
    date_field_name,
)

#: Every field ``ItemForm`` declares: every scalar field of ``Item`` except
#: ``categories``, ``custom``, ``created`` and ``modified``. Built from
#: the field-group mapping's own partition rather than restated by hand, so
#: the two artefacts cannot drift apart — ``fieldgroups.py`` already proves
#: this set is exactly ``Item``'s form fields
#: (``tests/test_ui/test_fieldgroups.py::TestFieldPartition``).
FORM_FIELDS = tuple(sorted(name for fields in GROUPS.values() for name in fields))


class CreatableSelect(TomSelect):
    """A Tom Select control that also takes a value typed in, beside the choices it offers.

    ``literature/static/literature/creatable.js`` turns Tom Select's ``create``
    setting on for every select marked ``data-create``, since django-mvp-forms'
    widget passes no such setting.
    """

    class Media:
        js = ["literature/creatable.js"]

    def build_attrs(self, base_attrs, extra_attrs=None):
        """Mark the select for the script that lets it take typed values."""
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs["data-create"] = "true"
        return attrs


class CreatableSelectMultiple(CreatableSelect, TomSelectMultiple):
    """A multiple Tom Select control that takes typed values as tags."""


class OpenChoiceField(forms.ChoiceField):
    """A choice field that also accepts a value outside its choices."""

    def valid_value(self, value):
        """Accept any value: the choices are suggestions."""
        return True


class KeywordsField(forms.MultipleChoiceField):
    """Keywords as tags, stored as the one comma-separated string CSL JSON keeps them in."""

    widget = CreatableSelectMultiple(
        remove_button=True, placeholder=_("Type a keyword and press Enter")
    )

    @staticmethod
    def split(value):
        """Return the keywords a stored string holds, in order."""
        if isinstance(value, str):
            # CSL JSON separates keywords with commas, and some sources use
            # semicolons, so either one ends a keyword.
            return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
        return list(value or [])

    def prepare_value(self, value):
        """Show a stored string as one tag per keyword."""
        return self.split(value)

    def valid_value(self, value):
        """Accept any keyword: the choices are the catalogue's own, offered for reuse."""
        return True

    def has_changed(self, initial, data):
        """Compare keyword by keyword, so a stored string unchanged in content is unchanged."""
        return self.split(initial) != self.split(data)


class ItemForm(forms.ModelForm):
    """Every scalar field of ``Item``, always, and one date field per CSL date slot.

    The model's ``help_text`` records each field's CSL JSON name, which is
    the developer's reference and means nothing to the person filling the
    form in, so the form carries its own labels and help where the model's
    would mislead (``FIELD_LABELS``, ``FIELD_HELP``) and none elsewhere.
    The page's arrangement is ``ItemFormLayout``'s, built per instance.

    Each slot is a start and an end, written to that slot's ``ItemDate`` on
    save. A slot left empty that was empty stays absent, and a stored date
    whose only content is unparsed text keeps that text.
    """

    class Media:
        js = ["literature/item-form.js"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.help_text = FIELD_HELP.get(name, "")
            if name in FIELD_LABELS:
                field.label = FIELD_LABELS[name]
        self.fields["type"].choices = [("", ""), *TYPE_CHOICE_GROUPS]
        self.fields["keyword"] = KeywordsField(
            label=_("Keywords"),
            required=False,
            choices=keyword_choices(self.instance.keyword if self.instance.pk else ""),
        )
        self.stored_dates = (
            {row.date_type: row for row in self.instance.item_dates.all()}
            if self.instance.pk
            else {}
        )
        for slot, label in DATE_SLOTS:
            row = self.stored_dates.get(slot)
            begin = StoredPartialDateField(
                label=label, required=False, widget=PartialDateInput
            )
            end = StoredPartialDateField(
                label=_("End date"), required=False, widget=PartialDateInput
            )
            self.fields[date_field_name(slot)] = begin
            self.fields[date_field_name(slot, end=True)] = end
            if row is not None:
                self.initial[date_field_name(slot)] = row.begin
                self.initial[date_field_name(slot, end=True)] = row.end
                unparsed = row.literal or row.raw
                if not row.begin and unparsed:
                    year = begin.widget.widgets[0]
                    year.attrs["placeholder"] = unparsed
                    year.attrs["title"] = unparsed
        # Django's CharField strips surrounding whitespace by default, which
        # quietly rewrites a stored value on a save that changed nothing —
        # an abstract ending in a newline loses it, a title stored with
        # padding comes back trimmed. A save with no changes must leave the
        # record byte-identical, and the CSL JSON import path does not
        # strip, so such values do reach the store. Turning it off here is
        # what makes that true of every value, not only the ones that
        # happen not to have edges.
        for field in self.fields.values():
            if isinstance(field, forms.CharField):
                field.strip = False
        self.helper = ItemFormLayout(self).helper()

    def date_slots_holding_values(self):
        """The slots with a stored date, of any kind, on the reference being edited."""
        return frozenset(self.stored_dates)

    def clean_keyword(self):
        """Join the tags back into one string, or keep the stored string when no keyword changed."""
        words = self.cleaned_data["keyword"]
        stored = self.instance.keyword if self.instance.pk else ""
        if words == KeywordsField.split(stored):
            return stored
        return ", ".join(words)

    def clean(self):
        """Check each date slot's range the way ``ItemDate`` does, and report it on the slot."""
        cleaned_data = super().clean()
        for slot, _label in DATE_SLOTS:
            begin = cleaned_data.get(date_field_name(slot)) or None
            end = cleaned_data.get(date_field_name(slot, end=True)) or None
            try:
                ItemDate(date_type=slot, begin=begin, end=end).clean()
            except ValidationError as error:
                self.add_error(date_field_name(slot, end=True), error)
        return cleaned_data

    def _save_m2m(self):
        """Write the date slots after the reference itself is saved."""
        super()._save_m2m()
        for slot, _label in DATE_SLOTS:
            names = (date_field_name(slot), date_field_name(slot, end=True))
            if not any(name in self.changed_data for name in names):
                continue
            begin = self.cleaned_data[names[0]] or None
            end = self.cleaned_data[names[1]] or None
            row = self.stored_dates.get(slot)
            if begin is None and end is None:
                if row is None:
                    continue
                if row.literal or row.raw or row.raw_date_parts:
                    row.begin = row.end = None
                    row.save()
                else:
                    row.delete()
                continue
            row = row or ItemDate(item=self.instance, date_type=slot)
            row.begin, row.end = begin, end
            row.save()

    class Meta:
        model = Item
        fields = FORM_FIELDS
        widgets = {
            "abstract": forms.Textarea(attrs={"rows": 8}),
            "note": forms.Textarea(attrs={"rows": 3}),
            "annote": forms.Textarea(attrs={"rows": 3}),
            "references": forms.Textarea(attrs={"rows": 3}),
            "type": TomSelect(
                placeholder=_("Choose a type"),
                attrs={
                    "x-model": "form.itemType",
                    # cotton/form/index.html opens x-data="{form: {}}" on the
                    # <form> element with an empty object, and this form is
                    # rendered inside it — there is no seam that seeds the
                    # scope from self.object.type. Without x-init, x-model
                    # writes its own undefined state onto the select at
                    # initialisation: the edit page would render with no
                    # type selected, and saving would then fail validation
                    # because type is required.
                    "x-init": "form.itemType = $el.value",
                },
            ),
        }


def keyword_choices(own):
    """This reference's own keywords in their stored order, then every other keyword the catalogue uses.

    Its own come first because a select sends its chosen options in the order
    they are listed, and an unchanged save has to send them back in the order
    they were stored.
    """
    mine = KeywordsField.split(own)
    others = set()
    for stored in Item.objects.exclude(keyword="").values_list("keyword", flat=True):
        others.update(KeywordsField.split(stored))
    others -= set(mine)
    words = [*mine, *sorted(others, key=str.casefold)]
    return [(word, word) for word in words]


#: The id shared between the family-name input's ``list=`` attribute and the
#: page-level ``<datalist>`` it references (FS-012, #117). Defined here
#: rather than in ``views.py`` so the form and the context that supplies the
#: datalist's own options cannot name two different ids.
CONTRIBUTOR_NAMES_DATALIST_ID = "contributor-names-datalist"


class NameForm(forms.ModelForm):
    """A contributor row: an ``ItemName`` link whose form also carries the ``Name`` it points at (FS-012, #117).

    ``ItemName`` carries ``item``, ``name``, ``role`` and ``order``; the
    person types into ``Name``. This form declares none of ``ItemName``'s own
    fields: the role is the set the row sits in, handed in as ``role`` and
    written onto a new row, and ``order`` arrives through the formset's
    ``can_order`` field. The name's own parts are fields of this form, unbound
    to ``ItemName``, and ``save()`` turns them into a stored ``Name``.

    Each name-part field is built from ``Name``'s own field via
    ``formfield()``. The three citation-processor flags — ``comma_suffix``,
    ``static_ordering``, ``parse_names`` — are never declared, so nothing here
    can write them and their stored values are preserved exactly.
    """

    class Meta:
        model = ItemName
        fields = ()

    family = Name._meta.get_field("family").formfield(
        widget=forms.TextInput(attrs={"list": CONTRIBUTOR_NAMES_DATALIST_ID})
    )
    given = Name._meta.get_field("given").formfield()
    dropping_particle = Name._meta.get_field("dropping_particle").formfield()
    non_dropping_particle = Name._meta.get_field("non_dropping_particle").formfield()
    suffix = Name._meta.get_field("suffix").formfield()
    literal = Name._meta.get_field("literal").formfield()

    #: The fields that make up a ``Name``, in the order ``save()`` compares
    #: and writes them. Declared once so ``save()`` and ``__init__`` cannot
    #: drift onto two different sets.
    NAME_FIELDS = (
        "family",
        "given",
        "dropping_particle",
        "non_dropping_particle",
        "suffix",
        "literal",
    )

    def __init__(self, *args, role=None, **kwargs):
        super().__init__(*args, **kwargs)
        # The role is the set's, never the row's: each role has a set of its
        # own, so a row added to the editors is an editor.
        if not self.instance.pk:
            self.instance.role = role
        # Seeding initial from the linked Name is what makes an unedited row
        # round-trip unchanged: without it, every field would start from
        # ModelForm's own blank default and a save that touched nothing
        # would read as a submission clearing every name part.
        if self.instance.pk and self.instance.name_id:
            name = self.instance.name
            for field_name in self.NAME_FIELDS:
                self.initial.setdefault(field_name, getattr(name, field_name))
        for name, (label, help_text) in self.NAME_COPY.items():
            self.fields[name].label = label
            self.fields[name].help_text = help_text

    #: What each name part is called on the page, with an example where the
    #: CSL name would leave a person guessing.
    NAME_COPY = {
        "family": (_("Family name"), ""),
        "given": (_("Given name"), ""),
        "non_dropping_particle": (
            _("Particle kept with the family name"),
            _("Such as de in Jean de La Fontaine."),
        ),
        "dropping_particle": (
            _("Particle dropped when sorting"),
            _("Such as van in Ludwig van Beethoven."),
        ),
        "suffix": (_("Suffix"), _("Such as Jr. or III.")),
        "literal": (_("Organisation name"), ""),
    }

    def clean(self):
        """Require a family name or an unparsed name, unless the row is being deleted."""
        cleaned_data = super().clean()
        if cleaned_data.get("DELETE"):
            # A row marked for removal carries whatever it last held; nothing
            # about a name it is dropping needs to satisfy this rule.
            return cleaned_data
        family = cleaned_data.get("family", "")
        literal = cleaned_data.get("literal", "")
        if not family and not literal:
            raise forms.ValidationError(
                _("Enter a family name, or an organisation name under name details."),
                code="name_required",
            )
        return cleaned_data

    def save(self, commit=True):
        """Write ``role`` onto the link and the name parts onto a ``Name``."""
        item_name = super().save(commit=False)
        submitted = {
            field: self.cleaned_data.get(field, "") for field in self.NAME_FIELDS
        }

        if item_name.name_id is None:
            # A new link always creates a new Name — entry never reuses a
            # stored record, even one identical to it.
            item_name.name = self.create_name(submitted)
        else:
            linked_name = item_name.name
            stored = {field: getattr(linked_name, field) for field in self.NAME_FIELDS}
            if submitted != stored:
                shared_elsewhere = linked_name.item_names.exclude(
                    pk=item_name.pk
                ).exists()
                if shared_elsewhere:
                    # Rewriting the linked Name in place would silently
                    # rename it on every other reference holding it, so a
                    # new one is created and the link is repointed instead.
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
        """Create and return a new, fully validated ``Name`` from ``values``, one per :attr:`NAME_FIELDS`."""
        name = Name(**values)
        name.full_clean()
        name.save()
        return name


class SetPolicedConstraintMixin:
    """Leaves one named model constraint to the row's own formset, which is the only party that can judge it correctly (FS-012, #117).

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
        """Mirror ``BaseModelForm.validate_constraints`` with the set-policed constraint's own field excluded."""
        # Only Django 6.0+ calls this; 5.2 already excludes the constraint
        # inside Model.full_clean(), so defining it there is harmless.
        exclude = self._get_validation_exclusions() | {self.constraint_field}
        try:
            self.instance.validate_constraints(exclude=exclude)
        except ValidationError as e:
            self._update_errors(e)


class StoredPartialDateField(PartialDateField):
    """A partial date field that shows a stored ``PartialDate`` as the text it saves as.

    The model hands the form a ``PartialDate``, which never compares equal to
    the text sent back, so every stored date would count as changed.
    """

    def prepare_value(self, value):
        """Show a stored partial date as its ISO text."""
        if isinstance(value, PartialDate):
            return str(value)
        return super().prepare_value(value)


class ItemIdentifierForm(SetPolicedConstraintMixin, forms.ModelForm):
    """An identifier row: one ``ItemIdentifier`` reachable through the reference form's identifiers set (FS-012, #117).

    Declares ``type`` and ``value``, ``ItemIdentifier``'s only two fields besides the ``item``
    foreign key the identifier set itself supplies. ``type`` carries no model-level
    ``choices=`` — an unknown kind is stored and left unchecked by design
    (``docs/adr/0002-open-identifier-types.md``) — so the six known kinds
    (:class:`~literature.choices.IdentifierType`) are offered through
    :class:`IdentifierKindWidget`'s completion list rather than restricted to them.

    Normalization happens here, not in :func:`~literature.validators.validate_identifier`'s
    dispatch dict: a typed kind matching one of the six known kinds other than by casing
    is cleaned to its canonical acronym before it ever reaches the model, so ``isbn`` is checked
    as ``ISBN``, while a kind matching none of them passes through untouched and
    unchecked, exactly as it does today. Changing the dispatch dict instead would also
    normalize the import path's own lookups, which this feature does not touch and must not
    affect.

    Format checking itself is not this form's own job: ``ItemIdentifier.clean()``/``save()``
    already call ``validate_identifier(self.type, self.value)`` (``literature/models.py``),
    which ``ModelForm._post_clean()`` runs through ``full_clean()``. That call raises a plain
    ``ValidationError`` rather than one keyed by field, so a rejection surfaces as a non-field
    error — the same shape :class:`ItemDateForm`'s span rejections take — carrying whichever
    message ``literature/validators.py`` raised.
    """

    constraint_field = "type"

    class Meta:
        model = ItemIdentifier
        fields = ("type", "value")
        labels = {"type": _("Identifier type"), "value": _("Identifier")}
        help_texts = {"type": "", "value": ""}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The six known types are the choices. Any other type is typed in and
        # stored as it is (docs/adr/0002-open-identifier-types.md), and a
        # stored one is offered back so the row shows what it holds.
        choices = [("", ""), *((kind, kind) for kind in IdentifierType.values)]
        stored = self.instance.type if self.instance.pk else ""
        if stored and stored not in IdentifierType.values:
            choices.append((stored, stored))
        self.fields["type"] = OpenChoiceField(
            label=_("Identifier type"),
            choices=choices,
            widget=CreatableSelect(placeholder=_("DOI, ISBN, URL…")),
        )

    def clean_type(self):
        """Normalize a typed kind matching a known one, other than by casing, to its canonical acronym.

        A kind matching none of the six passes through exactly as typed.
        """
        value = self.cleaned_data["type"]
        for known in IdentifierType.values:
            if value.casefold() == known.casefold():
                return known
        return value


class ImportForm(forms.Form):
    """Choose a configured format and a file to run it through (FS-011, #103).

    Not a ``ModelForm``: nothing here maps to ``Item``, the format resolves
    the file into entries and the entries into items, never this form — the
    front end has no reading path of its own.
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
        # would never appear.
        self.fields["format"].choices = [
            (name, format_class.label)
            for name, format_class in available_formats().items()
        ]


class ConfirmImportForm(forms.Form):
    """Carry out the import a preview described (FS-011, #103).

    The staged file's token and the format it was staged as both live in the
    reader's own session, never in this form — the whole point is that
    nothing on this page can name someone else's staged upload.

    The one field it does declare names which preview the page was showing.
    That is not the same thing: on its own it reaches nothing, because the
    view checks it against the confirming session's own value and imports
    only where the two agree. What it prevents is a page still showing an
    earlier preview carrying out a later one.
    """

    preview = forms.CharField(widget=forms.HiddenInput, required=False)

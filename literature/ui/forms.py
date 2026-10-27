"""The one write form every create and update flow shares (FS-008, #74)."""

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

#: Every scalar field of ``Item`` except ``categories``, ``custom``, ``created`` and
#: ``modified``, built from the field-group mapping so the two cannot drift apart.
FORM_FIELDS = tuple(sorted(name for fields in GROUPS.values() for name in fields))


class CreatableSelect(TomSelect):
    """A Tom Select control that also takes a value typed in, beside the choices it offers.

    ``literature/ui/static/literature/creatable.js`` turns Tom Select's ``create``
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
        """Return the keywords a stored string holds, in order.

        Args:
            value: A stored string, or a list of keywords.

        Returns:
            The keywords. Either a comma or a semicolon ends one, as sources use both.
        """
        if isinstance(value, str):
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

    Scoping by item type is the template's job: every field is declared, so a
    group the type does not use is hidden by Alpine but still posts the value it
    held. Building the field list from the type would blank every omitted field
    on save.

    The model's ``help_text`` records each field's CSL JSON name, which means
    nothing to the person filling the form in, so the form carries its own labels
    and help where the model's would mislead (``FIELD_LABELS``, ``FIELD_HELP``).
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
        # Stripping would rewrite imported values with edge whitespace on a save that
        # changed nothing, which must leave the record byte-identical.
        for field in self.fields.values():
            if isinstance(field, forms.CharField):
                field.strip = False
        self.helper = ItemFormLayout(self).helper()

    def date_slots_holding_values(self):
        """Return the slots with a stored date, of any kind, on the reference being edited.

        Returns:
            The slot names.
        """
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
                    # The form's x-data starts empty, so without x-init x-model blanks the
                    # stored type and saving fails because type is required.
                    "x-init": "form.itemType = $el.value",
                },
            ),
        }


def keyword_choices(own):
    """List a reference's own keywords in stored order, then every other keyword the catalogue uses.

    Its own come first because a select sends its options in listed order, and an
    unchanged save has to send them back in the order they were stored.

    Args:
        own: The reference's stored keyword string.

    Returns:
        ``(word, word)`` choice pairs.
    """
    mine = KeywordsField.split(own)
    others = set()
    for stored in Item.objects.exclude(keyword="").values_list("keyword", flat=True):
        others.update(KeywordsField.split(stored))
    others -= set(mine)
    words = [*mine, *sorted(others, key=str.casefold)]
    return [(word, word) for word in words]


#: The id shared by the family-name input's ``list=`` attribute and the page-level
#: ``<datalist>`` it references (FS-012, #117), so the two cannot name different ids.
CONTRIBUTOR_NAMES_DATALIST_ID = "contributor-names-datalist"


class NameForm(forms.ModelForm):
    """A contributor row: an ``ItemName`` link whose form also carries its ``Name`` (FS-012, #117).

    The form declares none of ``ItemName``'s own fields: the role is the set the
    row sits in, and ``order`` arrives through the formset's ``can_order`` field.
    The name's parts are unbound fields built from ``Name``'s own via
    ``formfield()``, and ``save()`` turns them into a stored ``Name``. The
    citation-processor flags (``comma_suffix``, ``static_ordering``,
    ``parse_names``) are never declared, so their stored values are preserved.

    Args:
        *args: What ``ModelForm`` takes.
        role: The role of the set the row sits in, written onto a new row.
        **kwargs: What ``ModelForm`` takes.
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

    #: The fields that make up a ``Name``, in the order ``save()`` compares and writes them.
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
        if not self.instance.pk:
            self.instance.role = role
        # Without this, a save that touched nothing would read as clearing every name part.
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
            # Entry never reuses a stored Name, even an identical one.
            item_name.name = self.create_name(submitted)
        else:
            linked_name = item_name.name
            stored = {field: getattr(linked_name, field) for field in self.NAME_FIELDS}
            if submitted != stored:
                shared_elsewhere = linked_name.item_names.exclude(
                    pk=item_name.pk
                ).exists()
                if shared_elsewhere:
                    # Editing in place would rename it on every other reference holding it.
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
        """Create a new, fully validated ``Name``.

        Args:
            values: The name parts, one per :attr:`NAME_FIELDS`.

        Returns:
            The saved ``Name``.
        """
        name = Name(**values)
        name.full_clean()
        name.save()
        return name


class SetPolicedConstraintMixin:
    """Leave one named model constraint to the row's own formset (FS-012, #117).

    A row form validates against the database as it stands, so it cannot see
    that another row holding the same value is flagged for removal in this
    submission. A replacement would be refused as a collision. Only the formset
    can judge the rows being kept, so its ``clean()`` performs the check, and the
    database constraint stays the final backstop.

    ``constraint_field`` names one field of the constraint rather than the
    constraint itself: excluding any one of its fields skips exactly that
    constraint and leaves the others validated.
    """

    #: A field of the constraint the set polices. Excluding it skips exactly
    #: that constraint.
    constraint_field: str

    def validate_constraints(self):
        """Validate model constraints, leaving out the one the formset polices."""
        # Only Django 6.0+ calls this; 5.2 excludes the constraint in Model.full_clean().
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
    """An identifier row: one ``ItemIdentifier`` in the reference form's identifiers set (FS-012, #117).

    ``type`` carries no model-level ``choices``: an unknown kind is stored and
    left unchecked by design (``docs/adr/0002-open-identifier-types.md``), so the
    six known kinds (:class:`~literature.choices.IdentifierType`) are offered
    through :class:`CreatableSelect` rather than enforced.

    A typed kind matching a known one other than by casing is normalized to its
    canonical acronym here, so ``isbn`` is checked as ``ISBN``. Changing the
    validator's dispatch dict instead would also change the import path's lookups.

    Format checking is not this form's job: ``ItemIdentifier.clean()`` calls
    ``validate_identifier``, which raises a plain ``ValidationError``, so a
    rejection surfaces as a non-field error.
    """

    constraint_field = "type"

    class Meta:
        model = ItemIdentifier
        fields = ("type", "value")
        labels = {"type": _("Identifier type"), "value": _("Identifier")}
        help_texts = {"type": "", "value": ""}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A stored type outside the six is offered back so the row shows what it holds.
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
        """Normalize a kind matching a known one, other than by casing, to its canonical acronym."""
        value = self.cleaned_data["type"]
        for known in IdentifierType.values:
            if value.casefold() == known.casefold():
                return known
        return value


class ImportForm(forms.Form):
    """Choose a configured format and a file to run it through (FS-011, #103).

    Not a ``ModelForm``: the format resolves the file into entries and items, as
    the front end has no reading path of its own.
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
        # Read here, not at class definition, so a format configured later appears.
        self.fields["format"].choices = [
            (name, format_class.label)
            for name, format_class in available_formats().items()
        ]


class ConfirmImportForm(forms.Form):
    """Carry out the import a preview described (FS-011, #103).

    The staged file's token and format live in the reader's own session, so
    nothing on the page can name someone else's upload. The one field names which
    preview the page showed; the view imports only where it matches the session's
    value, which stops a stale page from carrying out a later preview.
    """

    preview = forms.CharField(widget=forms.HiddenInput, required=False)

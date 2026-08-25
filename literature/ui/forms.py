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
from literature.models import Item
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

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

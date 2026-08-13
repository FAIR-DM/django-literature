"""Shared fixtures for the opt-in front end's tests.

No story owns this file — T009, T013 and T020 all build on it. The root
``tests/conftest.py`` already gives every test a bare, unrelated ``item``; the
fixture here is the populated case the catalogue list, the reference page and
the contributor page all render against, so no view test wires the four
factories together itself.
"""

import pytest

from literature.models import Item
from tests.factories import ItemDateFactory, ItemFactory, ItemIdentifierFactory, ItemNameFactory


@pytest.fixture
def populated_item(db):
    """A saved :class:`~literature.models.Item` with one contributor, one date
    and one identifier — the shape a catalogue row and a reference page both
    render."""
    item = ItemFactory()
    ItemNameFactory(item=item)
    ItemDateFactory(item=item)
    ItemIdentifierFactory(item=item)
    return item


#: The four fields that are on ``Item`` but never on ``ItemForm`` (D-4), shared
#: by ``test_fieldgroups.py`` (which checks the field-group partition against
#: it) and ``test_forms.py`` (which checks ``ItemForm`` itself against it).
#: ``categories`` and ``custom`` are excluded because the form never carries
#: them; ``created`` and ``modified`` because they are auto-managed
#: timestamps, not CSL variables.
EXCLUDED_FROM_FORM = frozenset({"categories", "custom", "created", "modified"})


def scalar_field_names():
    """Every concrete, non-pk field ``Item`` declares, by name.

    Mirrors the same walk ``literature/ui/fields.py``'s ``scalar_fields``
    uses, so a field added to the model is picked up here the same way it
    would be picked up there.
    """
    return {field.name for field in Item._meta.get_fields() if hasattr(field, "attname") and not field.primary_key}

"""Shared fixtures for the opt-in front end's tests."""

import pytest

from literature.models import Item
from tests.factories import (
    ItemDateFactory,
    ItemFactory,
    ItemIdentifierFactory,
    ItemNameFactory,
)


@pytest.fixture
def populated_item(db):
    item = ItemFactory()
    ItemNameFactory(item=item)
    ItemDateFactory(item=item)
    ItemIdentifierFactory(item=item)
    return item


#: The four fields that are on ``Item`` but never on ``ItemForm``, shared
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
    return {
        field.name
        for field in Item._meta.get_fields()
        if hasattr(field, "attname") and not field.primary_key
    }

"""Shared fixtures for the opt-in front end's tests.

No story owns this file — T009, T013 and T020 all build on it. The root
``tests/conftest.py`` already gives every test a bare, unrelated ``item``; the
fixture here is the populated case the catalogue list, the reference page and
the contributor page all render against, so no view test wires the four
factories together itself.
"""

import pytest

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

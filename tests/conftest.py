"""Shared pytest fixtures for the literature test suite.

Django settings are wired via ``DJANGO_SETTINGS_MODULE`` in ``pyproject.toml``;
pytest-django handles setup and teardown from there.

The object fixtures below are thin wrappers over the model factories in
``tests.factories``. A test uses one when it needs an item, name, or related
record only as a precondition. A test that asserts on specific field values
builds its object inline with the factory instead, since those values are then
the thing under test.
"""

import pytest

from tests.factories import (
    ItemDateFactory,
    ItemFactory,
    ItemIdentifierFactory,
    ItemNameFactory,
    NameFactory,
)


@pytest.fixture
def item(db):
    """A saved :class:`~literature.models.Item` with a generated citation key."""
    return ItemFactory()


@pytest.fixture
def name(db):
    """A saved :class:`~literature.models.Name` with a generated family name."""
    return NameFactory()


@pytest.fixture
def item_name(db):
    """A saved :class:`~literature.models.ItemName`, item and name auto-created."""
    return ItemNameFactory()


@pytest.fixture
def item_date(db):
    """A saved :class:`~literature.models.ItemDate`, item auto-created."""
    return ItemDateFactory()


@pytest.fixture
def item_identifier(db):
    """A saved :class:`~literature.models.ItemIdentifier`, item auto-created."""
    return ItemIdentifierFactory()

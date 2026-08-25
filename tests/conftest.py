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


@pytest.fixture(autouse=True)
def _media_root_under_tmp_path(tmp_path, settings):
    """Every test's ``MEDIA_ROOT`` is a throwaway ``tmp_path`` (US-4).

    ``ItemImportView.dispatch()`` sweeps ``StagedUpload``'s storage
    directory on every request, GET included (T507), so any test reaching
    that view at all touches ``default_storage`` — from ``tests/test_ui/``
    and from ``tests/test_demo/`` alike, which is why this lives at the
    suite root rather than in either package's own ``conftest.py``. Left at
    Django's own default, that resolves to the process's working directory,
    and a test run leaves ``literature-imports/`` behind in the repository
    itself rather than in a directory pytest already cleans up.
    """
    settings.MEDIA_ROOT = str(tmp_path)


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

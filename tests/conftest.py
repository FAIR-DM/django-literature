"""Shared pytest fixtures for the literature test suite.

The object fixtures wrap ``tests.factories`` for tests that need a record only as a
precondition. A test asserting on specific field values builds its record inline.
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
    # ItemImportView sweeps staged uploads in default_storage on every request, from
    # test_ui and test_demo alike; left at the default, a run writes into the repository.
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def item(db):
    return ItemFactory()


@pytest.fixture
def name(db):
    return NameFactory()


@pytest.fixture
def item_name(db):
    return ItemNameFactory()


@pytest.fixture
def item_date(db):
    return ItemDateFactory()


@pytest.fixture
def item_identifier(db):
    return ItemIdentifierFactory()

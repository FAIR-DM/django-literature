"""Shared pytest fixtures for the literature test suite.

The object fixtures wrap ``tests.factories`` for tests that need a record only as a
precondition. A test asserting on specific field values builds its record inline.

``client`` is signed in as an editor holding every permission the catalogue's write
pages ask for, because most tests drive those pages. A test about what someone without
them sees asks for ``anonymous_client`` or ``reader_client`` by name.
"""

import pytest
from django.contrib.auth.models import Permission
from django.test import Client

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


#: The model permissions an editor holds: adding (which covers importing), changing
#: and deleting a reference.
EDITOR_PERMISSIONS = ("add_item", "change_item", "delete_item")


@pytest.fixture
def editor(db, django_user_model):
    user = django_user_model.objects.create_user("editor.user")
    user.user_permissions.set(
        Permission.objects.filter(
            content_type__app_label="literature", codename__in=EDITOR_PERMISSIONS
        )
    )
    return user


@pytest.fixture
def client(client, editor):
    client.force_login(editor)
    return client


@pytest.fixture
def reader_client(db, django_user_model):
    reader = django_user_model.objects.create_user("regular.user")
    reader_client = Client()
    reader_client.force_login(reader)
    return reader_client


@pytest.fixture
def anonymous_client():
    return Client()


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

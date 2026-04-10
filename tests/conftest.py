"""Shared pytest fixtures and factory helpers for the literature test suite.

All fixture factories accept keyword overrides so tests can customise only
what they need (Constitution Principle IV).
"""

import pytest

from literature.choices import DateType, IdentifierType, ItemType, NameRole


@pytest.fixture
def admin_user(db):
    """Create a superuser for HTTP admin tests."""
    from django.contrib.auth.models import User

    return User.objects.create_superuser(
        username="admin",
        password="password",
        email="admin@example.com",
    )


@pytest.fixture
def make_item(db):
    """Factory fixture for creating Item instances.

    Accepts keyword overrides to customise fields.
    """
    from literature.models import Item

    def factory(**kwargs):
        defaults = {
            "citation_key": "TestItem2024",
            "type": ItemType.ARTICLE_JOURNAL,
        }
        defaults.update(kwargs)
        return Item.objects.create(**defaults)

    return factory


@pytest.fixture
def make_name(db):
    """Factory fixture for creating Name instances.

    Accepts keyword overrides to customise fields.
    """
    from literature.models import Name

    def factory(**kwargs):
        defaults = {
            "family": "Smith",
            "given": "John",
        }
        defaults.update(kwargs)
        return Name.objects.create(**defaults)

    return factory


@pytest.fixture
def make_item_name(db, make_item, make_name):
    """Factory fixture for creating ItemName through-model instances.

    Accepts keyword overrides to customise fields.
    """
    from literature.models import ItemName

    def factory(**kwargs):
        item = kwargs.pop("item", None) or make_item()
        name = kwargs.pop("name", None) or make_name()
        defaults = {
            "item": item,
            "name": name,
            "role": NameRole.AUTHOR,
        }
        defaults.update(kwargs)
        return ItemName.objects.create(**defaults)

    return factory


@pytest.fixture
def make_item_date(db, make_item):
    """Factory fixture for creating ItemDate instances.

    Accepts keyword overrides to customise fields.
    """
    from literature.models import ItemDate

    def factory(**kwargs):
        item = kwargs.pop("item", None) or make_item()
        defaults = {
            "item": item,
            "date_type": DateType.ISSUED,
        }
        defaults.update(kwargs)
        return ItemDate.objects.create(**defaults)

    return factory


@pytest.fixture
def make_item_identifier(db, make_item):
    """Factory fixture for creating ItemIdentifier instances.

    Accepts keyword overrides to customise fields.
    """
    from literature.models import ItemIdentifier

    def factory(**kwargs):
        item = kwargs.pop("item", None) or make_item()
        defaults = {
            "item": item,
            "type": IdentifierType.DOI,
            "value": "10.1234/test",
        }
        defaults.update(kwargs)
        return ItemIdentifier.objects.create(**defaults)

    return factory

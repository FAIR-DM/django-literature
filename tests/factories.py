"""factory_boy factories for the literature models, one per model.

``SubFactory`` wires each related row to its owner, so ``ItemNameFactory()`` alone yields a
complete row.
"""

import factory
from django.conf import settings

from literature.choices import DateType, IdentifierType, ItemType, NameRole
from literature.models import Item, ItemDate, ItemIdentifier, ItemName, Name
from tests.host.models import Citation


class ItemFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`Item` with a batch-unique citation key.

    ``type`` defaults to a journal article; every other field keeps its model
    default so ``__str__`` fallbacks and blank-field behaviour stay testable by
    overriding only what a test needs.
    """

    class Meta:
        model = Item

    citation_key = factory.Sequence(lambda n: f"Item{n}")
    type = ItemType.ARTICLE_JOURNAL


class UserFactory(factory.django.DjangoModelFactory):
    """Build a saved user with a batch-unique username and no permissions."""

    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: f"user{n}")


class CitationFactory(factory.django.DjangoModelFactory):
    """Build a saved host-app :class:`Citation`, auto-creating the item it cites."""

    class Meta:
        model = Citation

    reference = factory.SubFactory(ItemFactory)


class NameFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`Name` with a batch-unique family name."""

    class Meta:
        model = Name

    family = factory.Sequence(lambda n: f"Family{n}")
    given = "Given"


class ItemNameFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`ItemName`, auto-creating its item and name."""

    class Meta:
        model = ItemName

    item = factory.SubFactory(ItemFactory)
    name = factory.SubFactory(NameFactory)
    role = NameRole.AUTHOR


class ItemDateFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`ItemDate`, auto-creating its owning item."""

    class Meta:
        model = ItemDate

    item = factory.SubFactory(ItemFactory)
    date_type = DateType.ISSUED


class ItemIdentifierFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`ItemIdentifier`, auto-creating its owning item."""

    class Meta:
        model = ItemIdentifier

    item = factory.SubFactory(ItemFactory)
    type = IdentifierType.DOI
    value = "10.1234/test"

"""factory_boy factories for the literature models.

One factory per model. Tests build their fixtures on these instead of
hand-constructing records. ``citation_key`` is driven by a sequence so repeated
calls never collide on the unique key, and the related models auto-create their
owning objects through ``SubFactory`` so a single ``ItemNameFactory()`` (or
``ItemDateFactory`` / ``ItemIdentifierFactory``) call yields a fully-wired row.
"""

import factory

from literature.choices import DateType, IdentifierType, ItemType, NameRole
from literature.models import Item, ItemDate, ItemIdentifier, ItemName, Name


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

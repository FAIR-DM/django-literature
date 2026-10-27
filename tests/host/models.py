"""A model standing in for a host project's own link to a reference.

The upgrade from the ``LiteratureItem`` schema has to leave a host's foreign
keys to ``Item`` working, so the tests need a host model to check that with.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Citation(models.Model):
    """A host record that cites one reference."""

    reference = models.ForeignKey(
        "literature.Item",
        on_delete=models.CASCADE,
        verbose_name=_("reference"),
        help_text=_("The reference this record cites."),
    )


class ReadingListEntry(models.Model):
    """A host record whose table and column names are long enough to be shortened.

    PostgreSQL cuts a constraint name at 63 characters, so the foreign key to the
    old table and the one to the current table come out with the same name.
    """

    reference = models.ForeignKey(
        "literature.Item",
        on_delete=models.CASCADE,
        verbose_name=_("reference"),
        help_text=_("The reference on the reading list."),
    )

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

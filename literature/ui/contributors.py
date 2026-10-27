"""Contributor grouping for the reference page."""

from itertools import groupby
from operator import attrgetter

from django.utils.translation import ngettext_lazy

from literature.choices import NameRole
from literature.models import Name


class ContributorGroups:
    """One item's contributors, grouped by role and headed by that role's name.

    A subclass overriding :attr:`ROLE_LABELS` or :meth:`role_label` is the
    supported way for a host project to rename a role, for example "Creators".
    This lives in ``literature/ui/`` rather than the core, which stays free of
    helpers only the optional app uses.

    Args:
        item: The item whose contributors to group.
    """

    #: One ngettext message pair per role, keyed by the stored role value, so the
    #: heading agrees in number with the names under it in every language.
    ROLE_LABELS = {
        NameRole.AUTHOR: ngettext_lazy("Author", "Authors", "count"),
        NameRole.CHAIR: ngettext_lazy("Chair", "Chairs", "count"),
        NameRole.COLLECTION_EDITOR: ngettext_lazy(
            "Collection Editor", "Collection Editors", "count"
        ),
        NameRole.COMPILER: ngettext_lazy("Compiler", "Compilers", "count"),
        NameRole.COMPOSER: ngettext_lazy("Composer", "Composers", "count"),
        NameRole.CONTAINER_AUTHOR: ngettext_lazy(
            "Container Author", "Container Authors", "count"
        ),
        NameRole.CONTRIBUTOR: ngettext_lazy("Contributor", "Contributors", "count"),
        NameRole.CURATOR: ngettext_lazy("Curator", "Curators", "count"),
        NameRole.DIRECTOR: ngettext_lazy("Director", "Directors", "count"),
        NameRole.EDITOR: ngettext_lazy("Editor", "Editors", "count"),
        NameRole.EDITORIAL_DIRECTOR: ngettext_lazy(
            "Editorial Director", "Editorial Directors", "count"
        ),
        NameRole.EXECUTIVE_PRODUCER: ngettext_lazy(
            "Executive Producer", "Executive Producers", "count"
        ),
        NameRole.GUEST: ngettext_lazy("Guest", "Guests", "count"),
        NameRole.HOST: ngettext_lazy("Host", "Hosts", "count"),
        NameRole.ILLUSTRATOR: ngettext_lazy("Illustrator", "Illustrators", "count"),
        NameRole.INTERVIEWER: ngettext_lazy("Interviewer", "Interviewers", "count"),
        NameRole.NARRATOR: ngettext_lazy("Narrator", "Narrators", "count"),
        NameRole.ORGANIZER: ngettext_lazy("Organizer", "Organizers", "count"),
        NameRole.ORIGINAL_AUTHOR: ngettext_lazy(
            "Original Author", "Original Authors", "count"
        ),
        NameRole.PERFORMER: ngettext_lazy("Performer", "Performers", "count"),
        NameRole.PRODUCER: ngettext_lazy("Producer", "Producers", "count"),
        NameRole.RECIPIENT: ngettext_lazy("Recipient", "Recipients", "count"),
        NameRole.REVIEWED_AUTHOR: ngettext_lazy(
            "Reviewed Author", "Reviewed Authors", "count"
        ),
        NameRole.SCRIPT_WRITER: ngettext_lazy(
            "Script Writer", "Script Writers", "count"
        ),
        NameRole.SERIES_CREATOR: ngettext_lazy(
            "Series Creator", "Series Creators", "count"
        ),
        NameRole.TRANSLATOR: ngettext_lazy("Translator", "Translators", "count"),
    }

    def __init__(self, item):
        self.item = item

    @classmethod
    def role_label(cls, role, count):
        """Return ``role``'s heading in the plural form ``count`` calls for.

        A role the enumeration does not name is returned as stored, as
        ``ItemName.get_role_display()`` does: the store accepts values outside
        :class:`~literature.choices.NameRole`.

        Args:
            role: The stored role value.
            count: How many names sit under the heading.

        Returns:
            The translated heading.
        """
        label = cls.ROLE_LABELS.get(role)
        if label is None:
            return role
        return label % {"count": count}

    def groups(self):
        """Return one ``{"label", "names"}`` group per role the item carries.

        Groups follow ``ItemName``'s declared ordering — role, then the
        position stored within that role — so both the order and the grouping
        are the store's rather than this class's.

        Reads ``item.item_names`` as given, so an item drawn through
        ``prefetch_related("item_names__name")`` costs no further query.

        Returns:
            A list rather than a generator, so the reference page can split it
            into the byline and the other roles.
        """
        groups = []
        for role, group in groupby(self.item.item_names.all(), key=attrgetter("role")):
            item_names = list(group)
            groups.append(
                {
                    "label": self.role_label(role, len(item_names)),
                    "names": [item_name.name for item_name in item_names],
                }
            )
        return groups


def contributor_groups(item):
    """Return ``ContributorGroups(item).groups()``, the form the reference page calls.

    Args:
        item: The item whose contributors to group.

    Returns:
        One ``{"label", "names"}`` group per role.
    """
    return ContributorGroups(item).groups()


def stored_contributor_names():
    """Return the distinct, non-empty family names the catalogue already holds.

    Offered as ``<datalist>`` suggestions on every contributor row's family-name
    input, a spelling aid only: accepting one links the reference to nothing.
    An unparsed organizational name has no family part, so it is excluded.

    Returns:
        The family names, sorted.
    """
    return list(
        Name.objects.exclude(family="")
        .order_by("family")
        .values_list("family", flat=True)
        .distinct()
    )

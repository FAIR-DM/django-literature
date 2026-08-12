"""Contributor grouping for the catalogue row and the reference page.

Lives beside its callers' views rather than in ``literature/utils/``, on the
same reasoning as :mod:`literature.ui.fields`: the core stays free of a helper
an optional app is the sole consumer of (FR-006), which is also why this is not
a method on ``Item``.

A role heading has to agree with the number of names under it — "Authors" over
three, "Author" over one. The plural is a message of its own per role rather
than a letter appended in the template, because the roles are translatable and
a language may declare more than two plural forms; only ``ngettext`` can pick
between them.
"""

from itertools import groupby
from operator import attrgetter

from django.utils.translation import ngettext_lazy

from literature.choices import NameRole


class ContributorGroups:
    """One item's contributors, grouped by role and headed by that role's name.

    A class rather than a pair of functions per Article XV: the labels are the
    part of this a host project is most likely to want its own version of — a
    repository that calls its authors "Creators", say — and a subclass
    overriding :attr:`ROLE_LABELS` or :meth:`role_label` is a supported way to
    do that, where monkey-patching a module function is not.
    """

    #: One deferred-number message pair per role, keyed by the stored role
    #: value. The third argument names the key :meth:`role_label` supplies the
    #: count under, so the form is chosen at render time under the reader's
    #: active language rather than fixed at import.
    ROLE_LABELS = {
        NameRole.AUTHOR: ngettext_lazy("Author", "Authors", "count"),
        NameRole.CHAIR: ngettext_lazy("Chair", "Chairs", "count"),
        NameRole.COLLECTION_EDITOR: ngettext_lazy("Collection Editor", "Collection Editors", "count"),
        NameRole.COMPILER: ngettext_lazy("Compiler", "Compilers", "count"),
        NameRole.COMPOSER: ngettext_lazy("Composer", "Composers", "count"),
        NameRole.CONTAINER_AUTHOR: ngettext_lazy("Container Author", "Container Authors", "count"),
        NameRole.CONTRIBUTOR: ngettext_lazy("Contributor", "Contributors", "count"),
        NameRole.CURATOR: ngettext_lazy("Curator", "Curators", "count"),
        NameRole.DIRECTOR: ngettext_lazy("Director", "Directors", "count"),
        NameRole.EDITOR: ngettext_lazy("Editor", "Editors", "count"),
        NameRole.EDITORIAL_DIRECTOR: ngettext_lazy("Editorial Director", "Editorial Directors", "count"),
        NameRole.EXECUTIVE_PRODUCER: ngettext_lazy("Executive Producer", "Executive Producers", "count"),
        NameRole.GUEST: ngettext_lazy("Guest", "Guests", "count"),
        NameRole.HOST: ngettext_lazy("Host", "Hosts", "count"),
        NameRole.ILLUSTRATOR: ngettext_lazy("Illustrator", "Illustrators", "count"),
        NameRole.INTERVIEWER: ngettext_lazy("Interviewer", "Interviewers", "count"),
        NameRole.NARRATOR: ngettext_lazy("Narrator", "Narrators", "count"),
        NameRole.ORGANIZER: ngettext_lazy("Organizer", "Organizers", "count"),
        NameRole.ORIGINAL_AUTHOR: ngettext_lazy("Original Author", "Original Authors", "count"),
        NameRole.PERFORMER: ngettext_lazy("Performer", "Performers", "count"),
        NameRole.PRODUCER: ngettext_lazy("Producer", "Producers", "count"),
        NameRole.RECIPIENT: ngettext_lazy("Recipient", "Recipients", "count"),
        NameRole.REVIEWED_AUTHOR: ngettext_lazy("Reviewed Author", "Reviewed Authors", "count"),
        NameRole.SCRIPT_WRITER: ngettext_lazy("Script Writer", "Script Writers", "count"),
        NameRole.SERIES_CREATOR: ngettext_lazy("Series Creator", "Series Creators", "count"),
        NameRole.TRANSLATOR: ngettext_lazy("Translator", "Translators", "count"),
    }

    def __init__(self, item):
        self.item = item

    @classmethod
    def role_label(cls, role, count):
        """Return ``role``'s heading in the plural form ``count`` names call for.

        A role the enumeration does not name is returned as stored, which is
        what ``ItemName.get_role_display()`` does with the same value: the
        store accepts role values outside
        :class:`~literature.choices.NameRole`, and the interface reports what
        it holds rather than refusing to render the row.
        """
        label = cls.ROLE_LABELS.get(role)
        if label is None:
            return role
        return label % {"count": count}

    def groups(self):
        """Return one ``{"label", "names"}`` group per role the item carries.

        Groups follow ``ItemName``'s declared ordering — role, then the
        position stored within that role — so both the order and the grouping
        are the store's rather than this class's (FR-013, FR-022).

        Reads ``item.item_names`` as given, so an item drawn through
        ``prefetch_related("item_names__name")`` costs no further query. A list
        rather than a generator: the catalogue row reads this off an
        annotation, which more than one template may iterate.
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
    """``ContributorGroups(item).groups()`` — the form the two views call."""
    return ContributorGroups(item).groups()

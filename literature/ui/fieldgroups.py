"""The item-type-to-field mapping the write form scopes itself by."""

from django.utils.translation import gettext_lazy as _

from literature.choices import DateType, ItemType, NameRole

#: Field membership, one field in exactly one group. CSL publishes no type-to-field
#: mapping, so this one follows specs/008-add-edit-remove-references/plan.md D-1; it
#: governs presentation, never what can be stored.
GROUPS: dict[str, tuple[str, ...]] = {
    "core": ("type", "citation_key", "title", "abstract"),
    "general": (
        "note",
        "annote",
        "keyword",
        "language",
        "status",
        "source",
        "call_number",
    ),
    "titles": (
        "title_short",
        "original_title",
        "part_title",
        "volume_title",
        "volume_title_short",
    ),
    "container": (
        "container_title",
        "container_title_short",
        "journal_abbreviation",
        "collection_title",
        "collection_number",
    ),
    "publication": (
        "publisher",
        "publisher_place",
        "edition",
        "medium",
        "genre",
        "version",
    ),
    "original": ("original_publisher", "original_publisher_place"),
    "numbering": (
        "volume",
        "issue",
        "page",
        "page_first",
        "number",
        "number_of_pages",
        "number_of_volumes",
        "chapter_number",
        "section",
        "part",
        "supplement",
        "printing",
    ),
    "event": ("event_title", "event_place"),
    "review": ("reviewed_title", "reviewed_genre"),
    "legal": ("authority", "jurisdiction", "division", "references"),
    "archive": ("archive", "archive_collection", "archive_location", "archive_place"),
    "physical": ("dimensions", "scale"),
}

#: User-visible group headings. Not annotated ``dict[str, str]``: ``gettext_lazy``
#: returns a lazy proxy, which mypy rejects as a ``str``.
GROUP_LABELS = {
    "core": _("Core"),
    "general": _("General"),
    "titles": _("Alternate titles"),
    "container": _("Published in"),
    "publication": _("Publication"),
    "original": _("Original publication"),
    "numbering": _("Numbering and pagination"),
    "event": _("Event"),
    "review": _("Reviewed work"),
    "legal": _("Legal"),
    "archive": _("Archive"),
    "physical": _("Physical description"),
}

#: Groups each type shows beyond ``core`` and ``general``; the code beside each entry is
#: the criterion that decided it (specs/008-add-edit-remove-references/plan.md D-1).
#: ``titles`` is assigned to no type, so it is reached only through "Show every field".
TYPE_GROUPS: dict[str, frozenset[str]] = {
    ItemType.ARTICLE: frozenset({"numbering"}),  # C4a
    ItemType.ARTICLE_JOURNAL: frozenset({"container", "numbering"}),  # C2 + C2a + C4a
    ItemType.ARTICLE_MAGAZINE: frozenset({"container", "numbering"}),  # C2a + C4a
    ItemType.ARTICLE_NEWSPAPER: frozenset({"container", "numbering"}),  # C2 + C2a + C4a
    ItemType.BILL: frozenset({"legal", "numbering"}),  # C2 + C4c
    ItemType.BOOK: frozenset(
        {"container", "publication", "original", "numbering"}
    ),  # C1 + C2 + C5
    ItemType.BROADCAST: frozenset({"container", "publication"}),  # C1
    ItemType.CHAPTER: frozenset({"container", "numbering"}),  # C2 + C2a + C4b
    ItemType.CLASSIC: frozenset({"archive", "original"}),  # C3 + C5
    ItemType.COLLECTION: frozenset({"archive"}),  # C3
    ItemType.DATASET: frozenset(),  # C6
    ItemType.DOCUMENT: frozenset(),  # C6
    ItemType.ENTRY: frozenset({"container", "numbering"}),  # C2a + C4b
    ItemType.ENTRY_DICTIONARY: frozenset({"container", "numbering"}),  # C2a + C4b
    ItemType.ENTRY_ENCYCLOPEDIA: frozenset({"container", "numbering"}),  # C2a + C4b
    ItemType.EVENT: frozenset({"event"}),  # C2
    ItemType.FIGURE: frozenset({"archive", "publication"}),  # C3 + C1
    ItemType.GRAPHIC: frozenset({"archive", "publication"}),  # C3 + C1
    ItemType.HEARING: frozenset({"legal", "numbering"}),  # C2 + C4c
    ItemType.INTERVIEW: frozenset(),  # C6
    ItemType.LEGAL_CASE: frozenset({"legal", "numbering"}),  # C2 + C4c
    ItemType.LEGISLATION: frozenset({"legal", "numbering"}),  # C2 + C4c
    ItemType.MANUSCRIPT: frozenset({"archive"}),  # C3
    ItemType.MAP: frozenset({"physical"}),  # C2
    ItemType.MOTION_PICTURE: frozenset({"container"}),  # C1
    ItemType.MUSICAL_SCORE: frozenset(),  # C6
    ItemType.PAMPHLET: frozenset({"archive"}),  # C3
    ItemType.PAPER_CONFERENCE: frozenset(
        {"container", "event", "numbering"}
    ),  # C2 + C2a + C4b
    ItemType.PATENT: frozenset({"legal", "numbering"}),  # C2 + C4c
    ItemType.PERFORMANCE: frozenset({"event"}),  # C2
    ItemType.PERIODICAL: frozenset(),  # C6
    ItemType.PERSONAL_COMMUNICATION: frozenset({"archive"}),  # C3
    ItemType.POST: frozenset(),  # C6
    ItemType.POST_WEBLOG: frozenset(),  # C6
    ItemType.REGULATION: frozenset({"legal", "numbering"}),  # C2 + C4c
    ItemType.REPORT: frozenset({"container", "numbering"}),  # C1 + C4c
    ItemType.REVIEW: frozenset({"container", "review", "numbering"}),  # C2 + C2a + C4b
    ItemType.REVIEW_BOOK: frozenset(
        {"container", "review", "numbering"}
    ),  # C2 + C2a + C4b
    ItemType.SOFTWARE: frozenset({"publication"}),  # C2
    ItemType.SONG: frozenset({"container", "numbering"}),  # C1 + C2
    ItemType.SPEECH: frozenset({"container", "event", "publication"}),  # C2 + C1
    ItemType.STANDARD: frozenset({"numbering"}),  # C4c
    ItemType.THESIS: frozenset({"publication"}),  # C1
    ItemType.TREATY: frozenset({"legal", "numbering"}),  # C2 + C4c
    ItemType.WEBPAGE: frozenset({"container"}),  # C1
}

#: Date slots that lead for each type beyond ``issued``, which is always on; the code
#: beside each entry is the criterion that decided it. Both are defined in
#: specs/012-reference-contributors-dates/plan.md D-5, which also says why this is not in ``GROUPS``.
TYPE_DATE_SLOTS: dict[str, frozenset[str]] = {
    ItemType.ARTICLE: frozenset(),  # DC6
    ItemType.ARTICLE_JOURNAL: frozenset({DateType.AVAILABLE_DATE}),  # DC2
    ItemType.ARTICLE_MAGAZINE: frozenset(),  # DC6
    ItemType.ARTICLE_NEWSPAPER: frozenset(),  # DC6
    ItemType.BILL: frozenset(),  # DC6
    ItemType.BOOK: frozenset({DateType.ORIGINAL_DATE}),  # DC4
    ItemType.BROADCAST: frozenset(),  # DC6
    ItemType.CHAPTER: frozenset(),  # DC6
    ItemType.CLASSIC: frozenset({DateType.ORIGINAL_DATE}),  # DC4
    ItemType.COLLECTION: frozenset(),  # DC6
    ItemType.DATASET: frozenset(),  # DC6
    ItemType.DOCUMENT: frozenset(),  # DC6
    ItemType.ENTRY: frozenset(),  # DC6
    ItemType.ENTRY_DICTIONARY: frozenset(),  # DC6
    ItemType.ENTRY_ENCYCLOPEDIA: frozenset(),  # DC6
    ItemType.EVENT: frozenset({DateType.EVENT_DATE}),  # DC3
    ItemType.FIGURE: frozenset(),  # DC6
    ItemType.GRAPHIC: frozenset(),  # DC6
    ItemType.HEARING: frozenset(),  # DC6
    ItemType.INTERVIEW: frozenset(),  # DC6
    ItemType.LEGAL_CASE: frozenset(),  # DC6
    ItemType.LEGISLATION: frozenset(),  # DC6
    ItemType.MANUSCRIPT: frozenset({DateType.SUBMITTED}),  # DC5
    ItemType.MAP: frozenset(),  # DC6
    ItemType.MOTION_PICTURE: frozenset(),  # DC6
    ItemType.MUSICAL_SCORE: frozenset(),  # DC6
    ItemType.PAMPHLET: frozenset(),  # DC6
    ItemType.PAPER_CONFERENCE: frozenset({DateType.EVENT_DATE}),  # DC3
    ItemType.PATENT: frozenset(),  # DC6
    ItemType.PERFORMANCE: frozenset({DateType.EVENT_DATE}),  # DC3
    ItemType.PERIODICAL: frozenset(),  # DC6
    ItemType.PERSONAL_COMMUNICATION: frozenset(),  # DC6
    ItemType.POST: frozenset({DateType.ACCESSED}),  # DC1
    ItemType.POST_WEBLOG: frozenset(),  # DC6
    ItemType.REGULATION: frozenset(),  # DC6
    ItemType.REPORT: frozenset(),  # DC6
    ItemType.REVIEW: frozenset(),  # DC6
    ItemType.REVIEW_BOOK: frozenset(),  # DC6
    ItemType.SOFTWARE: frozenset(),  # DC6
    ItemType.SONG: frozenset(),  # DC6
    ItemType.SPEECH: frozenset({DateType.EVENT_DATE}),  # DC3
    ItemType.STANDARD: frozenset(),  # DC6
    ItemType.THESIS: frozenset(),  # DC6
    ItemType.TREATY: frozenset({DateType.AVAILABLE_DATE}),  # DC2
    ItemType.WEBPAGE: frozenset({DateType.ACCESSED}),  # DC1
}


class FieldGroups:
    """Lookups over the item-type-to-field mapping above.

    The mapping is data a subclass may extend, the way
    :class:`~literature.ui.contributors.ContributorGroups` is extended, never
    something a project configures at runtime.
    """

    GROUPS = GROUPS
    GROUP_LABELS = GROUP_LABELS
    TYPE_GROUPS = TYPE_GROUPS
    TYPE_DATE_SLOTS = TYPE_DATE_SLOTS

    #: Groups every type carries regardless of its own ``TYPE_GROUPS`` entry.
    ALWAYS_ON = frozenset({"core", "general"})

    @classmethod
    def groups_for(cls, item_type) -> frozenset[str]:
        """Return the group names the form shows by default for ``item_type``.

        Always includes :attr:`ALWAYS_ON`; an unrecognised type resolves to
        just that baseline rather than raising, so a value the store accepts
        but the mapping has no opinion on still renders a form.

        Args:
            item_type: The stored item type value.

        Returns:
            The group names to show.
        """
        return cls.ALWAYS_ON | cls.TYPE_GROUPS.get(item_type, frozenset())

    @classmethod
    def fields_for(cls, group: str) -> tuple[str, ...]:
        """Return the field names belonging to ``group``.

        Args:
            group: A key of :attr:`GROUPS`.

        Returns:
            The field names in the group.
        """
        return cls.GROUPS[group]

    @classmethod
    def groups_holding_values(cls, item) -> frozenset[str]:
        """Return the groups with at least one non-empty field on ``item``.

        This is the forced-visible set FR-010 and FR-014
        (specs/008-add-edit-remove-references/spec.md) ask for: a group the
        current type would not otherwise show still renders when a stored
        value lives in one of its fields. "Non-empty" matches
        :func:`literature.ui.fields.field_sections`.

        Args:
            item: The item to inspect.

        Returns:
            The names of the groups holding a value.
        """
        holding = set()
        for group, field_names in cls.GROUPS.items():
            for field_name in field_names:
                value = getattr(item, field_name, None)
                if value not in (None, "", False):
                    holding.add(group)
                    break
        return frozenset(holding)


#: Roles the contributor tab leads with for each type, beside ``author``. A role holding a
#: contributor shows whatever the type. Unlike the two mappings above this is a judgement
#: of which roles cataloguers most often need, read from CSL's Appendix IV (Name Variables).
TYPE_ROLES: dict[str, frozenset[str]] = {
    ItemType.BOOK: frozenset({NameRole.EDITOR, NameRole.TRANSLATOR}),
    ItemType.CHAPTER: frozenset(
        {NameRole.EDITOR, NameRole.CONTAINER_AUTHOR, NameRole.TRANSLATOR}
    ),
    ItemType.CLASSIC: frozenset({NameRole.EDITOR, NameRole.TRANSLATOR}),
    ItemType.COLLECTION: frozenset({NameRole.EDITOR, NameRole.CURATOR}),
    ItemType.ENTRY: frozenset({NameRole.EDITOR}),
    ItemType.ENTRY_DICTIONARY: frozenset({NameRole.EDITOR}),
    ItemType.ENTRY_ENCYCLOPEDIA: frozenset({NameRole.EDITOR}),
    ItemType.PAPER_CONFERENCE: frozenset({NameRole.EDITOR}),
    ItemType.PERIODICAL: frozenset({NameRole.EDITOR}),
    ItemType.REPORT: frozenset({NameRole.EDITOR}),
    ItemType.EVENT: frozenset({NameRole.ORGANIZER, NameRole.CHAIR}),
    ItemType.SPEECH: frozenset({NameRole.CHAIR}),
    ItemType.PERFORMANCE: frozenset({NameRole.PERFORMER, NameRole.DIRECTOR}),
    ItemType.MOTION_PICTURE: frozenset(
        {NameRole.DIRECTOR, NameRole.PRODUCER, NameRole.SCRIPT_WRITER}
    ),
    ItemType.BROADCAST: frozenset(
        {NameRole.DIRECTOR, NameRole.HOST, NameRole.GUEST, NameRole.PRODUCER}
    ),
    ItemType.INTERVIEW: frozenset({NameRole.INTERVIEWER}),
    ItemType.SONG: frozenset({NameRole.COMPOSER, NameRole.PERFORMER}),
    ItemType.MUSICAL_SCORE: frozenset({NameRole.COMPOSER}),
    ItemType.FIGURE: frozenset({NameRole.ILLUSTRATOR}),
    ItemType.GRAPHIC: frozenset({NameRole.ILLUSTRATOR}),
    ItemType.PERSONAL_COMMUNICATION: frozenset({NameRole.RECIPIENT}),
    ItemType.REVIEW: frozenset({NameRole.REVIEWED_AUTHOR}),
    ItemType.REVIEW_BOOK: frozenset({NameRole.REVIEWED_AUTHOR}),
}

#: The order the role sets take on the page: authors, then editors, then the
#: rest in the order CSL lists them.
ROLE_ORDER = (
    NameRole.AUTHOR,
    NameRole.EDITOR,
    *(
        role
        for role in NameRole.values
        if role not in (NameRole.AUTHOR, NameRole.EDITOR)
    ),
)

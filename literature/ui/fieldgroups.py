"""The item-type-to-field mapping the write form scopes itself by (plan.md D-1, D-2).

CSL JSON publishes no such mapping — the schema validates every property on
every type, and the specification (Appendix III, item types; Appendix IV,
variables) describes the two separately (research.md §1). This module is the
package's own artefact, authored against six stated criteria rather than
inferred, and FR-004 requires the reasoning to be on record: every entry in
``TYPE_GROUPS`` below carries a one-line comment naming the criterion that put
it there.

**``titles`` is never assigned by any type.** None of the six criteria name it
— Appendix III and IV give no type-scoped evidence for the alternate-title
fields the way they do for, say, the legal or archival variables — so under a
criteria-only mapping it stays reachable only through the form's "Show every
field" toggle, for every type, rather than being guessed into a default view.

Sits in ``literature/ui/`` and not the core: ``tests/test_ui/test_architecture.py``
forbids the core importing anything the front end needs, and this mapping
governs presentation, never what can be stored (D-1).
"""

from django.utils.translation import gettext_lazy as _

from literature.choices import ItemType

#: Field membership, one field in exactly one group (tests/test_ui/test_fieldgroups.py
#: TestFieldPartition). Grouped as ``models.py`` already organises ``Item``,
#: which is itself CSL's own grouping (plan.md D-1).
GROUPS: dict[str, tuple[str, ...]] = {
    "core": ("type", "citation_key", "title", "abstract"),
    "general": ("note", "annote", "keyword", "language", "status", "source", "call_number"),
    "titles": ("title_short", "original_title", "part_title", "volume_title", "volume_title_short"),
    "container": (
        "container_title",
        "container_title_short",
        "journal_abbreviation",
        "collection_title",
        "collection_number",
    ),
    "publication": ("publisher", "publisher_place", "edition", "medium", "genre", "version"),
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
    "processor": (
        "citation_label",
        "citation_number",
        "first_reference_note_number",
        "locator",
        "year_suffix",
    ),
}

#: User-visible group headings (Article VIII).
GROUP_LABELS: dict[str, str] = {
    "core": _("Core"),
    "general": _("General"),
    "titles": _("Alternate titles"),
    "container": _("Container"),
    "publication": _("Publication"),
    "original": _("Original publication"),
    "numbering": _("Numbering and pagination"),
    "event": _("Event"),
    "review": _("Reviewed work"),
    "legal": _("Legal"),
    "archive": _("Archive"),
    "physical": _("Physical description"),
    "processor": _("Processor-generated"),
}

# --- Per-type assignment ---------------------------------------------------
#
# D-1's six criteria, applied in this order to every type below:
#
#   C1  A group Appendix III names for that type.
#   C2  A group whose fields Appendix IV defines in terms of that type.
#   C3  `archive` for types whose subject is a held object.
#   C4  `numbering` where the type is or sits inside a numbered sequence.
#   C5  `original` where republication or translation is ordinary.
#   C6  Otherwise: not used. Absence is the default.
#
# C4 and C5 name no worked examples in plan.md — applying them is this task's
# own judgement call, so each C4/C5 line below states the sub-case reasoned
# from, not just the criterion number:
#
#   C4a  periodical article, published with a volume/issue/page of its own
#   C4b  embedded in a paginated host (a chapter, an entry, a paper, a review)
#   C4c  a document identified by an official/report number
#
# Thirteen of the 45 types are outside Zotero's 32-type coverage entirely
# (research.md §1) and rest on the criteria alone, with no plausibility check
# available: classic, collection, entry, event, figure, musical_score,
# pamphlet, performance, periodical, regulation, review, review-book, treaty.
# Every other type's resolved field count (core + general + its extra groups,
# 11 baseline) is checked against Zotero's covered-type band (16-35, median
# 24); nine sit genuinely below it, each with a stated reason rather than a
# forced fit.
TYPE_GROUPS: dict[str, frozenset[str]] = {
    # C4a — periodical article: volume, issue, page. 23 fields, in-band.
    ItemType.ARTICLE: frozenset({"numbering"}),
    ItemType.ARTICLE_JOURNAL: frozenset({"numbering"}),
    ItemType.ARTICLE_MAGAZINE: frozenset({"numbering"}),
    ItemType.ARTICLE_NEWSPAPER: frozenset({"numbering"}),
    # C2 (legal) + C4c (a bill carries a bill number). 27 fields, in-band.
    ItemType.BILL: frozenset({"legal", "numbering"}),
    # C1 ("container-title... interpreted as" book) + C1 (medium statement) +
    # C5 (translated/republished editions are ordinary for a book). 24 fields, in-band.
    ItemType.BOOK: frozenset({"container", "publication", "original"}),
    # C1 (container-title statement) + C1 (genre statement). 22 fields, in-band.
    ItemType.BROADCAST: frozenset({"container", "publication"}),
    # C4b — a chapter is paginated inside its book and numbered within it. 23 fields, in-band.
    ItemType.CHAPTER: frozenset({"numbering"}),
    # C3 (a classic text is a held/canonical object) + C5 (translated and
    # re-edited across centuries by different publishers is ordinary for a
    # classic). Not in Zotero's 32. 17 fields.
    ItemType.CLASSIC: frozenset({"archive", "original"}),
    # C3 (a collection is itself the held object its members belong to). Not
    # in Zotero's 32. 15 fields.
    ItemType.COLLECTION: frozenset({"archive"}),
    # C6 — no Appendix III/IV language names a group for a dataset; its
    # identifying variables (DOI, version) are outside the scalar-field set
    # this mapping scopes. 11 fields, genuinely below Zotero's band: Zotero's
    # own dataset schema folds in fields (format, repository) this package
    # does not model as `Item` columns at all, so there is nothing here for
    # the criteria to find.
    ItemType.DATASET: frozenset(),
    # C6 — CSL's catch-all type, named by neither appendix. 11 fields, below
    # band: "document" has no criterion-evidenced shape of its own, so it
    # stays at the baseline rather than borrowing one.
    ItemType.DOCUMENT: frozenset(),
    # C4b — an entry is paginated inside the reference work that holds it.
    # Not in Zotero's 32. 23 fields.
    ItemType.ENTRY: frozenset({"numbering"}),
    ItemType.ENTRY_DICTIONARY: frozenset({"numbering"}),
    ItemType.ENTRY_ENCYCLOPEDIA: frozenset({"numbering"}),
    # C2 (event fields Appendix IV defines in terms of event). Not in
    # Zotero's 32. 13 fields.
    ItemType.EVENT: frozenset({"event"}),
    # C3 (a figure is a held object) + C1 (medium statement). Not in
    # Zotero's 32. 21 fields.
    ItemType.FIGURE: frozenset({"archive", "publication"}),
    # C3 (a graphic is a held object) + C1 (medium statement). 21 fields, in-band.
    ItemType.GRAPHIC: frozenset({"archive", "publication"}),
    # C2 (legal) + C4c (a hearing carries an official number). 27 fields, in-band.
    ItemType.HEARING: frozenset({"legal", "numbering"}),
    # C6 — an interview's distinguishing detail is who gave it, which is a
    # name-variable (interviewer/interviewee), not a scalar field either
    # appendix ties to this type. 11 fields, below band: nothing in the
    # scalar-field set is interview-specific.
    ItemType.INTERVIEW: frozenset(),
    # C2 (legal) + C4c (a case carries a docket/citation number). 27 fields, in-band.
    ItemType.LEGAL_CASE: frozenset({"legal", "numbering"}),
    # C2 (legal) + C4c (legislation carries an official number). 27 fields, in-band.
    ItemType.LEGISLATION: frozenset({"legal", "numbering"}),
    # C3 (a manuscript is a held object). 15 fields, below band: Zotero's
    # manuscript type folds in a free-text "type" descriptor this schema
    # does not carry as its own group; the criteria give archive and nothing
    # else evidenced.
    ItemType.MANUSCRIPT: frozenset({"archive"}),
    # C2 (Appendix IV's `scale` example is a map). 13 fields, below band:
    # only the physical group is criterion-evidenced for a map — no
    # container or numbering language ties it to an atlas or series, even
    # though that is common in practice.
    ItemType.MAP: frozenset({"physical"}),
    # C1 (container-title statement). 16 fields, in-band (at the floor).
    ItemType.MOTION_PICTURE: frozenset({"container"}),
    # C6 — neither appendix names a group for a musical score. Not in
    # Zotero's 32. 11 fields.
    ItemType.MUSICAL_SCORE: frozenset(),
    # C3 (a pamphlet is a held object). Not in Zotero's 32. 15 fields.
    ItemType.PAMPHLET: frozenset({"archive"}),
    # C2 (event) + C4b (a conference paper is paginated inside its
    # proceedings). 25 fields, in-band.
    ItemType.PAPER_CONFERENCE: frozenset({"event", "numbering"}),
    # C4c (a patent carries an official patent number). 23 fields, in-band.
    ItemType.PATENT: frozenset({"numbering"}),
    # C2 (event). Not in Zotero's 32. 13 fields.
    ItemType.PERFORMANCE: frozenset({"event"}),
    # C6 — a periodical (the publication itself, not an article within it)
    # matches no criterion; its own title fields already sit in `core`. Not
    # in Zotero's 32. 11 fields.
    ItemType.PERIODICAL: frozenset(),
    # C3 (the record of a private communication is the held object). 15
    # fields, below band: no publication or numbering evidence applies to a
    # communication that was never formally issued, which is the correct
    # shape for the type rather than a gap in it.
    ItemType.PERSONAL_COMMUNICATION: frozenset({"archive"}),
    # C6 — no criterion names a group for a post; where it was posted is
    # already reachable through `container_title` in `core`'s neighbours via
    # the toggle. 11 fields, below band.
    ItemType.POST: frozenset(),
    ItemType.POST_WEBLOG: frozenset(),
    # C2 (legal) + C4c (a regulation carries an official number). Not in
    # Zotero's 32. 27 fields.
    ItemType.REGULATION: frozenset({"legal", "numbering"}),
    # C1 (container-title statement) + C4c (a report carries a report
    # number). 28 fields, in-band.
    ItemType.REPORT: frozenset({"container", "numbering"}),
    # C2 (review fields Appendix IV defines in terms of review) + C4b (a
    # review is paginated inside the periodical that carries it). Not in
    # Zotero's 32. 25 fields.
    ItemType.REVIEW: frozenset({"review", "numbering"}),
    ItemType.REVIEW_BOOK: frozenset({"review", "numbering"}),
    # C6 — no criterion names a group for software; its version concept has
    # no Appendix III/IV language tying `publication` specifically to this
    # type the way it does for book/figure/graphic. 11 fields, below band.
    ItemType.SOFTWARE: frozenset(),
    # C1 (container-title statement — a song on an album). 16 fields, in-band (at the floor).
    ItemType.SONG: frozenset({"container"}),
    # C2 (event) + C1 (genre statement). 19 fields, in-band.
    ItemType.SPEECH: frozenset({"event", "publication"}),
    # C4c (a standard carries an official standard number). 23 fields, in-band.
    ItemType.STANDARD: frozenset({"numbering"}),
    # C1 (genre statement). 17 fields, in-band.
    ItemType.THESIS: frozenset({"publication"}),
    # C2 (legal) + C4c (a treaty carries an official number). Not in
    # Zotero's 32. 27 fields.
    ItemType.TREATY: frozenset({"legal", "numbering"}),
    # C1 (container-title statement — a page within a site). 16 fields, in-band (at the floor).
    ItemType.WEBPAGE: frozenset({"container"}),
}


class FieldGroups:
    """Lookups over the mapping above (Article XV — they share one subject).

    A constant and a few functions, not a registry or a settings-overridable
    table (Article III) — the mapping is data a subclass may extend the same
    way :class:`~literature.ui.contributors.ContributorGroups` is extended,
    never data a project configures at runtime.
    """

    GROUPS = GROUPS
    GROUP_LABELS = GROUP_LABELS
    TYPE_GROUPS = TYPE_GROUPS

    #: Groups every type carries regardless of its own ``TYPE_GROUPS`` entry.
    #: ``processor`` is deliberately absent from this set and from every
    #: entry above — a CSL processor assigns those values, not a person
    #: filling in a form (plan.md D-1).
    ALWAYS_ON = frozenset({"core", "general"})

    @classmethod
    def groups_for(cls, item_type) -> frozenset[str]:
        """Return the group names the form shows by default for ``item_type``.

        Always includes :attr:`ALWAYS_ON`; an unrecognised type resolves to
        just that baseline rather than raising, so a value the store accepts
        but the mapping has no opinion on still renders a form.
        """
        return cls.ALWAYS_ON | cls.TYPE_GROUPS.get(item_type, frozenset())

    @classmethod
    def fields_for(cls, group: str) -> tuple[str, ...]:
        """Return the field names belonging to ``group``."""
        return cls.GROUPS[group]

    @classmethod
    def groups_holding_values(cls, item) -> frozenset[str]:
        """Return the groups with at least one non-empty field on ``item``.

        This is the forced-visible set FR-010 and FR-014 ask for: a group the
        current type would not otherwise show still renders when a stored
        value already lives in one of its fields. "Non-empty" matches
        :func:`literature.ui.fields.scalar_fields`'s own test — ``None``, an
        empty string and ``False`` all count as not carried.
        """
        holding = set()
        for group, field_names in cls.GROUPS.items():
            for field_name in field_names:
                value = getattr(item, field_name, None)
                if value not in (None, "", False):
                    holding.add(group)
                    break
        return frozenset(holding)

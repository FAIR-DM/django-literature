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

from literature.choices import DateType, ItemType

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

#: User-visible group headings (Article VIII). Left for mypy to infer as
#: ``dict[str, _StrPromise]``: ``gettext_lazy`` returns a lazy proxy, not a
#: plain ``str``, and annotating this ``dict[str, str]`` is a type error even
#: though every value renders as one wherever Django consumes it.
GROUP_LABELS = {
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
# D-1's criteria, applied in this order to every type below:
#
#   C1   A group Appendix III names for that type.
#   C2   A group whose fields Appendix IV defines in terms of that type.
#   C2a  A type that sits inside a container takes `container`, not
#        `numbering` alone. Recording where an item appeared is what the
#        container group is for, and a form offering a page range without
#        the name of the thing the pages are in is not a usable form.
#   C3   `archive` for types whose subject is a held object.
#   C4   `numbering` where the type is or sits inside a numbered sequence.
#   C5   `original` where republication or translation is ordinary.
#   C6   Otherwise: not used. Absence is the default.
#
# C4 and C5 name no worked examples in plan.md — applying them is this task's
# own judgement call, so each C4/C5 line below states the sub-case reasoned
# from, not just the criterion number:
#
#   C4a  periodical article, published with a volume/issue/page of its own
#   C4b  embedded in a paginated host (a chapter, an entry, a paper, a
#        review) — paired with C2a below: the host itself is named via
#        `container`, the position within it via `numbering`.
#   C4c  a document identified by an official/report number
#
# Correction (T030): the first pass applied C2 as though the four clusters
# named in plan.md D-1 point 2's closing sentence (legal/review/event/
# physical) were the whole of it, and never reached C2a or the itemized
# evidence the same paragraph states ahead of that sentence. Re-derived below
# against the full itemized list: `container-title`'s own definition names
# chapter, article-journal, song and speech; `version` names software;
# `chapter-number` names chapter and song; `number-of-volumes` and `ISBN`
# name the book-like types; `authority`/`jurisdiction`/`division` name patent
# in addition to the named legal-types cluster.
#
# Thirteen of the 45 types are outside Zotero's 32-type coverage entirely
# (research.md §1) and rest on the criteria alone, with no plausibility check
# available: classic, collection, entry, event, figure, musical_score,
# pamphlet, performance, periodical, regulation, review, review-book, treaty.
# Every other type's resolved field count (core + general + its extra groups,
# 11 baseline) is checked against Zotero's covered-type band (16-35, median
# 24); nine sit genuinely below it, and book alone sits genuinely above it —
# each with a stated reason rather than a forced fit.
TYPE_GROUPS: dict[str, frozenset[str]] = {
    # C4a — periodical article: volume, issue, page. CSL's bare "article" is
    # the generic/unspecified variant — no host is named for it the way one
    # is for its journal/magazine/newspaper siblings below — so it stays at
    # numbering alone. 23 fields, in-band.
    ItemType.ARTICLE: frozenset({"numbering"}),
    # C2 (`container-title`'s definition names "the journal title for a
    # journal article") + C2a (a journal article is paginated inside the
    # journal that carries it) + C4a. 28 fields, in-band.
    ItemType.ARTICLE_JOURNAL: frozenset({"container", "numbering"}),
    # C2a (paginated inside the magazine that carries it) + C4a. 28 fields, in-band.
    ItemType.ARTICLE_MAGAZINE: frozenset({"container", "numbering"}),
    # C2 (`section` names article-newspaper) + C2a (paginated inside the
    # newspaper that carries it) + C4a. 28 fields, in-band.
    ItemType.ARTICLE_NEWSPAPER: frozenset({"container", "numbering"}),
    # C2 (legal) + C4c (a bill carries a bill number). 27 fields, in-band.
    ItemType.BILL: frozenset({"legal", "numbering"}),
    # C1 ("container-title... interpreted as" book) + C1 (medium statement) +
    # C2 (`number-of-volumes` and `ISBN` name "the book-like types") +
    # C5 (translated/republished editions are ordinary for a book). 36
    # fields, above Zotero's 35-field ceiling: CSL's own text names
    # `number-of-volumes` for book directly, and Zotero's schema — which
    # sets the plausibility ceiling, not a rule — has no field of its own
    # that surfaces it for its book type, so the criterion legitimately
    # produces a set the check cannot bound.
    ItemType.BOOK: frozenset({"container", "publication", "original", "numbering"}),
    # C1 (container-title statement) + C1 (genre statement). 22 fields, in-band.
    ItemType.BROADCAST: frozenset({"container", "publication"}),
    # C2 (`container-title`'s definition names "the book title for a book
    # chapter") + C2a (a chapter is paginated inside its book, so container
    # names the book) + C4b (numbered and paginated within it). 28 fields, in-band.
    ItemType.CHAPTER: frozenset({"container", "numbering"}),
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
    # C2a — an entry is paginated inside the reference work that holds it,
    # so container names that work, paired with C4b's numbering within it.
    # Not in Zotero's 32. 28 fields.
    ItemType.ENTRY: frozenset({"container", "numbering"}),
    ItemType.ENTRY_DICTIONARY: frozenset({"container", "numbering"}),
    ItemType.ENTRY_ENCYCLOPEDIA: frozenset({"container", "numbering"}),
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
    # C2 (event) + C2a (a conference paper is paginated inside its
    # proceedings, so container names them) + C4b (paginated within it). 30
    # fields, in-band.
    ItemType.PAPER_CONFERENCE: frozenset({"container", "event", "numbering"}),
    # C4c (a patent carries an official patent number) + C2 (`authority`,
    # `jurisdiction` and `division` name "patent and the legal types" —
    # patent itself is not in the named legal-types cluster, so this needed
    # the itemized reading rather than the cluster shorthand). 27 fields, in-band.
    ItemType.PATENT: frozenset({"legal", "numbering"}),
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
    # C2 (review fields Appendix IV defines in terms of review) + C2a (a
    # review is paginated inside the periodical that carries it, so
    # container names that periodical) + C4b (paginated within it). Not in
    # Zotero's 32. 30 fields.
    ItemType.REVIEW: frozenset({"container", "review", "numbering"}),
    ItemType.REVIEW_BOOK: frozenset({"container", "review", "numbering"}),
    # C2 (`version` names software, and `version` sits in `publication`).
    # 17 fields, in-band.
    ItemType.SOFTWARE: frozenset({"publication"}),
    # C1 (container-title statement — a song on an album) + C2
    # (`chapter-number` names chapter and song, standing in for a song's
    # track number within its album). 28 fields, in-band.
    ItemType.SONG: frozenset({"container", "numbering"}),
    # C2 (event) + C1 (genre statement) + C2 (`container-title`'s own
    # definition names "the session title for multi-part presentation at a
    # conference"). 24 fields, in-band.
    ItemType.SPEECH: frozenset({"container", "event", "publication"}),
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

# --- Per-type date-slot assignment -----------------------------------------
#
# A sibling mapping to TYPE_GROUPS above (plan.md D-5), never folded into
# `GROUPS`: research.md R6 measured why — `GROUPS` is flattened straight into
# `ItemForm.Meta.fields`, and a name that is not an `Item` column raises
# `FieldError` at class-definition time. CSL's six date slots are rows on
# `ItemDate`, not columns on `Item`, so they get a second structure under the
# same ADR-0020 discipline rather than a widened first one.
#
# `issued` is always-on, the way `core` and `general` are for `TYPE_GROUPS`
# above, and for the same reason: a bibliographic reference with no issue
# date at all is the case this mapping should never hide the field for. It is
# therefore never named in any entry below.
#
# Every other entry names the slots that additionally lead for that type,
# decided against these criteria and CSL's own two appendices alone —
# https://docs.citationstyles.org/en/stable/specification.html, Appendix III
# (Types) and Appendix IV (Variables, Date Variables):
#
#   DC1  `accessed` — Appendix III's own definition of the type uses the
#        word "online" to describe it directly.
#   DC2  `available-date` — Appendix IV's own definition of `available-date`
#        names the type by example ("the online publication date of a
#        journal article before its formal publication date; the date a
#        treaty was made available for signing").
#   DC3  `event-date` — the type already carries `event` in `TYPE_GROUPS`:
#        its own Appendix III definition ties it to a conference, exhibition
#        or presentation.
#   DC4  `original-date` — the type already carries `original` in
#        `TYPE_GROUPS`: republication or translation is ordinary for it.
#   DC5  `submitted` — Appendix IV's own definition of `submitted` names the
#        type by example ("e.g. a manuscript").
#   DC6  Otherwise: `issued` alone.
#
# DC1 is the narrowest of the six. Appendix III's 45 one-paragraph type
# definitions use the word "online" exactly twice: in `webpage`'s own text
# ("intrinsically online") and in `post`'s ("a online forum"). `post-weblog`
# — `post`'s own sibling, and a blog by any other name just as online — does
# not use the word in its one-line definition ("A blog post"), so under a
# criteria-only mapping it stays at the baseline rather than borrowing its
# relative's evidence, the same discipline `TYPE_GROUPS` applies to `titles`.
TYPE_DATE_SLOTS: dict[str, frozenset[str]] = {
    ItemType.ARTICLE: frozenset(),  # DC6
    ItemType.ARTICLE_JOURNAL: frozenset({DateType.AVAILABLE_DATE}),  # DC2 — "a journal article"
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
    ItemType.MANUSCRIPT: frozenset({DateType.SUBMITTED}),  # DC5 — "e.g. a manuscript"
    ItemType.MAP: frozenset(),  # DC6
    ItemType.MOTION_PICTURE: frozenset(),  # DC6
    ItemType.MUSICAL_SCORE: frozenset(),  # DC6
    ItemType.PAMPHLET: frozenset(),  # DC6
    ItemType.PAPER_CONFERENCE: frozenset({DateType.EVENT_DATE}),  # DC3
    ItemType.PATENT: frozenset(),  # DC6
    ItemType.PERFORMANCE: frozenset({DateType.EVENT_DATE}),  # DC3
    ItemType.PERIODICAL: frozenset(),  # DC6
    ItemType.PERSONAL_COMMUNICATION: frozenset(),  # DC6
    ItemType.POST: frozenset({DateType.ACCESSED}),  # DC1 — "a online forum"
    ItemType.POST_WEBLOG: frozenset(),  # DC6 — see note above; post's sibling, but not itself "online"
    ItemType.REGULATION: frozenset(),  # DC6
    ItemType.REPORT: frozenset(),  # DC6
    ItemType.REVIEW: frozenset(),  # DC6
    ItemType.REVIEW_BOOK: frozenset(),  # DC6
    ItemType.SOFTWARE: frozenset(),  # DC6
    ItemType.SONG: frozenset(),  # DC6
    ItemType.SPEECH: frozenset({DateType.EVENT_DATE}),  # DC3
    ItemType.STANDARD: frozenset(),  # DC6
    ItemType.THESIS: frozenset(),  # DC6
    ItemType.TREATY: frozenset({DateType.AVAILABLE_DATE}),  # DC2 — "a treaty was made available for signing"
    ItemType.WEBPAGE: frozenset({DateType.ACCESSED}),  # DC1 — "intrinsically online"
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
    TYPE_DATE_SLOTS = TYPE_DATE_SLOTS

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

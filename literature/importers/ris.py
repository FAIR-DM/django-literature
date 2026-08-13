"""Reading RIS files into the catalogue.

The second concrete format behind the import contract (spec 005), following the shape
:class:`~literature.importers.bibtex.BibTeXFormat` established: it supplies only the two stages
a format owns, :meth:`~RISFormat.parse` and :meth:`~RISFormat.to_csl_json`; the workflow,
atomicity, per-entry reporting and dry runs all come from
:class:`~literature.importers.base.BibFormat` unchanged.

This module is the foundational phase only — :class:`RISParser` and the :class:`RISFormat`
skeleton. There is no RIS-to-CSL mapping yet: that is US-1 (issue #36). Until it lands, only a
file with no entries (an empty file, or one holding nothing but header material) converts
cleanly; a real entry's :meth:`~RISFormat.to_csl_json` raises, and is reported as a failed entry
like any other conversion the contract cannot complete (plan.md "Story boundaries").

One format reads EndNote, Web of Science and Scopus alike, with no producer detection (FR-029):
the parser reads what the primary RIS specification defines, and the tags that only some
producers use are read by the tags themselves rather than by which tool wrote the file.

The parser is hand-rolled rather than built on ``rispy``: see research.md R1 and decisions.md D11
for why, checked empirically rather than assumed.
"""

import dataclasses
import re
from collections.abc import Iterator
from typing import Any, ClassVar, cast

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from literature.importers.base import BibFormat
from literature.importers.exceptions import EntryError, ParseError, SkipEntry
from literature.importers.normalizers import IdentifierNormalizer
from literature.importers.results import EntryResult
from literature.validators import validate_doi, validate_isbn, validate_issn, validate_url


@dataclasses.dataclass(frozen=True)
class RISEntry:
    """One RIS entry recovered from a file: its tags in source order, its position among the
    entries this parser has yielded, and the line its opening ``TY`` tag was found on.

    ``tags`` is an ordered sequence of ``(tag, value)`` pairs rather than a dict, because a
    repeatable tag (``AU``, ``KW``, ...) legitimately appears more than once — see
    :attr:`RISParser.REPEATABLE_TAGS`.
    """

    tags: tuple[tuple[str, str], ...]
    index: int
    start_line: int

    def values(self, tag: str) -> list[str]:
        """Every value this entry carries under ``tag``, in source order."""
        return [value for t, value in self.tags if t == tag]

    def first(self, tag: str) -> str:
        """This entry's first value under ``tag``, stripped, or ``""`` where it carries none.

        A tag present with a blank value reads the same as an absent one here, which is what
        every mapping site wants: a value that is only whitespace is nothing to store. Sites that
        genuinely need the unstripped text, or every value, use :meth:`values` instead.
        """
        values = self.values(tag)
        return values[0].strip() if values else ""


class RISParser:
    """Reads one ``.ris`` file into :class:`RISEntry` objects, one at a time.

    A generator, not a list builder (FR-004): the whole file's entries are never materialised
    before the first is available, which is what lets a caller consume one entry from a
    several-hundred-entry file and leave the rest unread.

    Expects ``file`` opened in **binary** mode. Decoding is this parser's own job — ``utf-8-sig``,
    so a byte-order mark is silently absorbed rather than becoming part of the first tag's value
    (research.md R1) — because naming the attempted encoding and the byte offset on failure
    (FR-034) needs the raw bytes, not whatever a caller's own text-mode decoding already turned
    them into (decisions.md D19).
    """

    #: Tolerant of the single-space and double-space-after-dash variants real producers emit
    #: (plan.md "The parser"; research.md R2 documents the two-space form as the specification's
    #: own, and real exports vary).
    _TAG_RE: ClassVar[re.Pattern[str]] = re.compile(r"^([A-Z][A-Z0-9])\s{0,2}-\s?(.*)$")

    #: RIS is a line-based format defined over CR, LF and CRLF, and nothing else (decisions.md
    #: D41). ``str.splitlines`` additionally breaks on vertical tab, form feed, the file/group/
    #: record separators, NEL and the Unicode line and paragraph separators, so a value carrying
    #: one of those would be split here and rejoined by the continuation-line rule with the
    #: character replaced by a space — a record that lands holding less than the file stated.
    _LINE_BREAK_RE: ClassVar[re.Pattern[str]] = re.compile(r"\r\n|\r|\n")

    #: An untagged line following one of these tags becomes another value; following any other
    #: tag, it is a continuation joined onto the previous value with a single space (FR-007,
    #: amended — see decisions.md D12, D20). Repeatability is RIS syntax, decidable from the tag
    #: alone, and has nothing to do with the CSL mapping, so it lives on the parser rather than on
    #: the (not-yet-built) mapping tables.
    REPEATABLE_TAGS: ClassVar[frozenset[str]] = frozenset({"AU", "A1", "A2", "A3", "A4", "ED", "KW", "UR", "SN", "N1"})

    def parse(self, file) -> Iterator[RISEntry | str]:
        """Yield this file's entries, one at a time, in source order.

        Header material — everything before the first ``TY`` tag — is yielded once, as a plain
        ``str``, immediately before the first entry (plan.md "How the skipped header is
        signalled"); :meth:`RISFormat.to_csl_json` raises
        :class:`~literature.importers.exceptions.SkipEntry` for it, the same pattern
        ``bibtex.py`` uses for a comment or preamble. A file with no header material at all
        yields no such sentinel (decisions.md D17).

        Raises :class:`~literature.importers.exceptions.ParseError` — never lets a decoding or
        framing failure escape raw — when the file cannot be decoded, when it carries RIS tag
        lines but no ``TY`` anywhere, or when it carries no recognisable tag lines at all. An
        empty or whitespace-only file is not an error: it yields nothing (spec Edge Cases).
        """
        raw = file.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ParseError(
                _("Could not decode this file as {encoding}: invalid byte at offset {offset}.").format(
                    encoding=exc.encoding, offset=exc.start
                )
            ) from exc

        if not text.strip():
            return

        lines = self._LINE_BREAK_RE.split(text)
        if lines and lines[-1] == "":
            # A file ending in a newline has no empty final line; ``str.splitlines`` drops it and
            # so must this, or the last value gains an empty continuation.
            lines.pop()

        has_tag_line = False
        has_ty = False
        for line in lines:
            match = self._TAG_RE.match(line)
            if match:
                has_tag_line = True
                if match.group(1) == "TY":
                    has_ty = True
                    break

        if not has_tag_line:
            raise ParseError(_("No RIS tag lines found. Is this an RIS file, or in an unexpected encoding?"))
        if not has_ty:
            raise ParseError(_("This file carries RIS tags but no 'TY' (reference type) tag anywhere."))

        yield from self._entries(lines)

    def _entries(self, lines: list[str]) -> Iterator[RISEntry | str]:
        """The real framing pass: open at ``TY``, close at ``ER`` or the next ``TY`` (FR-006).

        A block of tags with no ``TY`` of its own, seen after the first entry, is yielded as its
        own :class:`RISEntry` (its ``tags`` carrying no ``"TY"`` pair) rather than dropped
        (T021, FR-009 — supersedes decisions.md D18). :meth:`RISFormat.to_csl_json` raises
        :class:`~literature.importers.exceptions.EntryError` for an entry with no ``TY``, which
        reports it as its own failed entry rather than ending the file: raising directly from this
        generator would, per ``import_entries``, stop the whole run at the index it failed on and
        lose every entry after it, which FR-009's "the rest of the file still imports" forbids.
        """
        header: list[str] = []
        pairs: list[list[str]] = []
        stray: list[list[str]] = []
        start_line = 0
        stray_start_line = 0
        header_yielded = False
        index = 0

        for line_no, line in enumerate(lines, start=1):
            match = self._TAG_RE.match(line)

            if match is None:
                if pairs:
                    self._continue_value(pairs, line)
                elif stray:
                    self._continue_value(stray, line)
                elif not header_yielded:
                    header.append(line)
                continue

            tag, value = match.group(1), match.group(2)

            if tag == "TY":
                if pairs:
                    yield RISEntry(tags=tuple((t, v) for t, v in pairs), index=index, start_line=start_line)
                    index += 1
                elif stray:
                    yield RISEntry(tags=tuple((t, v) for t, v in stray), index=index, start_line=stray_start_line)
                    index += 1
                    stray = []
                elif not header_yielded:
                    text = "\n".join(header).strip()
                    if text:
                        yield text
                header_yielded = True
                pairs = [[tag, value]]
                start_line = line_no
                continue

            if tag == "ER":
                if pairs:
                    yield RISEntry(tags=tuple((t, v) for t, v in pairs), index=index, start_line=start_line)
                    index += 1
                    pairs = []
                elif stray:
                    yield RISEntry(tags=tuple((t, v) for t, v in stray), index=index, start_line=stray_start_line)
                    index += 1
                    stray = []
                continue

            if pairs:
                pairs.append([tag, value])
            elif not header_yielded:
                header.append(line)
            else:
                if not stray:
                    stray_start_line = line_no
                stray.append([tag, value])

        if pairs:
            yield RISEntry(tags=tuple((t, v) for t, v in pairs), index=index, start_line=start_line)
        elif stray:
            yield RISEntry(tags=tuple((t, v) for t, v in stray), index=index, start_line=stray_start_line)

    def _continue_value(self, pairs: list[list[str]], line: str) -> None:
        """Resolve one untagged line against the tag it follows (FR-007, amended).

        Only called while an entry is open (``pairs`` non-empty), so the most recently added pair
        always names the tag this line continues.
        """
        last_tag = pairs[-1][0]
        if last_tag in self.REPEATABLE_TAGS:
            pairs.append([last_tag, line.strip()])
        else:
            pairs[-1][1] = f"{pairs[-1][1]} {line.strip()}"


#: RIS reference type -> CSL item type (T010, FR-011). A type not listed here maps to the generic
#: ``document`` type rather than failing the entry, the spec's own fallback for an unrecognised
#: type ("it will be labeled as Generic", research.md R2). Adapted from citation-js's per-type
#: table (MIT, research.md R3), not Zotero's (AGPL) — read as evidence only, never copied.
#: ``GRNT``/``GRANT`` and ``UNPD``/``UNPB`` are the same reference type under the two RIS
#: specification generations' spellings (research.md R2) and are listed side by side so both reach
#: the same CSL type rather than one falling to the fallback and the other not.
REFERENCE_TYPE_TABLE: dict[str, str] = {
    "ABST": "article-journal",
    "ADVS": "motion_picture",
    "AGGR": "dataset",
    "ANCIENT": "classic",
    "ART": "graphic",
    "BILL": "bill",
    "BLOG": "post-weblog",
    "BOOK": "book",
    "CASE": "legal_case",
    "CHAP": "chapter",
    "CHART": "graphic",
    "CLSWK": "classic",
    "COMP": "software",
    "CONF": "paper-conference",
    "CPAPER": "paper-conference",
    "CTLG": "document",
    "DATA": "dataset",
    "DBASE": "dataset",
    "DICT": "entry-dictionary",
    "EBOOK": "book",
    "ECHAP": "chapter",
    "EDBOOK": "book",
    "EJOUR": "article-journal",
    "ELEC": "webpage",
    "ENCYC": "entry-encyclopedia",
    "FIGURE": "figure",
    "GEN": "document",
    "GOVDOC": "legislation",
    "GRANT": "document",
    "GRNT": "document",
    "HEAR": "hearing",
    "ICOMM": "personal_communication",
    "INPR": "article-journal",
    "JFULL": "periodical",
    "JOUR": "article-journal",
    "LEGAL": "legislation",
    "MANSCPT": "manuscript",
    "MAP": "map",
    "MGZN": "article-magazine",
    "MPCT": "motion_picture",
    "MULTI": "webpage",
    "MUSIC": "musical_score",
    "NEWS": "article-newspaper",
    "PAMP": "pamphlet",
    "PAT": "patent",
    "PCOMM": "personal_communication",
    "RPRT": "report",
    "SER": "periodical",
    "SLIDE": "graphic",
    "SOUND": "song",
    "STAND": "standard",
    "STAT": "legislation",
    "THES": "thesis",
    "UNBILL": "bill",
    "UNPB": "manuscript",
    "UNPD": "manuscript",
    "VIDEO": "motion_picture",
}

#: A reference type with no row above becomes ``document`` rather than failing the entry (T010,
#: FR-011, acceptance scenario 3).
_FALLBACK_TYPE = "document"

#: Core RIS tag -> CSL variable (T011, FR-012), for tags whose CSL variable does not depend on the
#: entry's reference type. ``T2`` and ``SP`` are type-conditional and are resolved separately
#: (:func:`_container_or_collection_variable`, :func:`_page_variable`).
FIELD_TABLE: dict[str, str] = {
    "TI": "title",
    "AB": "abstract",
    "ST": "title-short",
    "VL": "volume",
    "IS": "issue",
    "LA": "language",
    "M3": "genre",
    "ET": "edition",
    "PB": "publisher",
    "CY": "publisher-place",
}

#: Reference types that are already their own container — a whole book, a report, a standalone
#: work — so a ``T2`` one of them carries names the series it belongs to rather than a containing
#: work (research.md R4's "book-like" set for ``A2``'s collection-editor resolution, reused here:
#: the same fact about a type — that it has no container of its own — decides both). Everything
#: else has a genuine container (a journal, a book for one of its chapters), so its ``T2`` is a
#: container title.
_BOOK_LIKE_TYPES: frozenset[str] = frozenset(
    {"BOOK", "EDBOOK", "RPRT", "ELEC", "MAP", "CLSWK", "COMP", "MULTI", "UNPB"}
)

#: Reference types where ``SP`` states a page *count* rather than a locator, because the type is a
#: whole work rather than something with a location inside a container (research.md R11).
_PAGE_COUNT_TYPES: frozenset[str] = frozenset({"BOOK", "EBOOK", "EDBOOK", "THES"})


def _container_or_collection_variable(ref_type: str) -> str:
    """The CSL variable ``T2`` maps to for ``ref_type`` (T011, FR-012)."""
    return "collection-title" if ref_type in _BOOK_LIKE_TYPES else "container-title"


def _page_variable(ref_type: str) -> str:
    """The CSL variable ``SP`` maps to for ``ref_type`` (T011, FR-012, research.md R11)."""
    return "number-of-pages" if ref_type in _PAGE_COUNT_TYPES else "page"


# ---------------------------------------------------------------------------
# Contributors (T012, FR-013, FR-014) — role resolved on the reference type, per research.md R4's
# encoding of the 2011 specification's per-type matrix.
# ---------------------------------------------------------------------------

#: Reference types with a genuine container (a chapter's book, a paper's proceedings): ``A2`` names
#: that container's editor. ``JOUR`` is included for Scopus's mistyped book chapters (research.md
#: R9): a genuine Scopus record carries the book's editors in ``A2`` under ``TY - JOUR``, with
#: ``M3 - Book Chapter`` the more reliable type signal Scopus does not act on itself.
_CHAPTER_LIKE_A2_EDITOR_TYPES: frozenset[str] = frozenset(
    {"CHAP", "ECHAP", "CONF", "CPAPER", "ENCYC", "DICT", "SER", "EBOOK", "MUSIC", "ANCIENT", "BLOG", "JOUR"}
)

#: On ``BOOK``, ``A3`` is the editor (research.md R4 — the one type where ``A2``/``A3`` invert).
_A3_EDITOR_TYPES: frozenset[str] = frozenset({"BOOK"})

#: Elsewhere, where ``A3`` has a documented role, it is the collection editor.
_A3_COLLECTION_EDITOR_TYPES: frozenset[str] = frozenset(
    {"CHAP", "CONF", "SER", "EBOOK", "ADVS", "MUSIC", "SLIDE", "SOUND", "VIDEO"}
)

#: On an edited book, the author tag names the editor instead (research.md R4).
_AU_EDITOR_TYPES: frozenset[str] = frozenset({"EDBOOK"})

#: Reference types where ``A4`` has a documented role at all: translator (research.md R4's table).
#: Elsewhere ``A4`` is left unmapped rather than guessed at.
_A4_TRANSLATOR_TYPES: frozenset[str] = frozenset(
    {"BOOK", "CHAP", "ANCIENT", "CLSWK", "CTLG", "DICT", "EDBOOK", "ENCYC", "PAMP"}
)


def _name_to_csl(name: str) -> dict[str, Any]:
    """One RIS name string to a CSL name-variable object.

    The primary specification's own author format is ``Family, Given``. A name with no comma is
    institutional or otherwise unparsed and is stored as a ``literal`` rather than split (FR-014) —
    forcing it into ``family``/``given`` would invent a split the source never stated. Where a
    second comma-separated part follows the given name, it is a suffix (``Family, Given, Jr.``).
    """
    stripped = name.strip()
    if not stripped:
        return {}
    if "," not in stripped:
        return {"literal": stripped}

    family, _sep, rest = stripped.partition(",")
    family = family.strip()
    if not family:
        return {"literal": stripped}

    result: dict[str, Any] = {"family": family}
    given_parts = [part.strip() for part in rest.split(",")]
    if given_parts[0]:
        result["given"] = given_parts[0]
    if len(given_parts) > 1 and given_parts[1]:
        result["suffix"] = given_parts[1]
    return result


def _add_contributors(roles: dict[str, list[dict[str, Any]]], role: str, names: list[str]) -> None:
    """Parse each of ``names`` and append it to ``role``'s list, in order."""
    for name in names:
        parsed = _name_to_csl(name)
        if parsed:
            roles.setdefault(role, []).append(parsed)


#: The contributor tags this module reads, in the order their roles are resolved.
_CONTRIBUTOR_TAGS: tuple[str, ...] = ("AU", "ED", "A2", "A3", "A4")


def _contributor_role(tag: str, ref_type: str) -> str | None:
    """The CSL role ``tag`` names on ``ref_type``, or ``None`` where it names none.

    ``AU`` and ``ED`` always resolve. ``A2``, ``A3`` and ``A4`` resolve only on the reference types
    research.md R4's per-type matrix documents them for, which is most types for ``A2`` and a
    minority for ``A3`` and ``A4``.

    ``None`` does not mean "discard": a contributor tag with no documented role on this entry's
    reference type is an unmapped tag, and reaches the item through the preservation sweep like
    any other (decisions.md D43, FR-024). :func:`_consumed_tags` is what keeps the two in step.
    """
    if tag == "AU":
        return "editor" if ref_type in _AU_EDITOR_TYPES else "author"
    if tag == "ED":
        return "editor"
    if tag == "A2":
        if ref_type in _CHAPTER_LIKE_A2_EDITOR_TYPES:
            return "editor"
        return "collection-editor" if ref_type in _BOOK_LIKE_TYPES else None
    if tag == "A3":
        if ref_type in _A3_EDITOR_TYPES:
            return "editor"
        return "collection-editor" if ref_type in _A3_COLLECTION_EDITOR_TYPES else None
    if tag == "A4":
        return "translator" if ref_type in _A4_TRANSLATOR_TYPES else None
    return None


def _contributors(raw: RISEntry, ref_type: str) -> dict[str, list[dict[str, Any]]]:
    """Every contributor tag this entry carries, resolved to its CSL role in source order.

    ``ED`` is Web of Science's own editor tag, in neither official RIS specification and used in
    place of ``A2`` rather than alongside it (research.md R4: a genuine WoS ``CHAP`` record carries
    three ``ED`` tags and zero ``A2``), so it resolves to ``editor`` unconditionally rather than by
    reference type.
    """
    roles: dict[str, list[dict[str, Any]]] = {}

    for tag in _CONTRIBUTOR_TAGS:
        role = _contributor_role(tag, ref_type)
        if role:
            _add_contributors(roles, role, raw.values(tag))

    return roles


# ---------------------------------------------------------------------------
# Dates (T013, FR-015, FR-016) — ``PY`` anchors, ``DA`` refines precision, ``Y1`` is a fallback
# alias for ``PY``, ``Y2`` is the access date. research.md R5: none of this feature's three
# supported producers emits ``Y1``, but Ovid, CINAHL, RefWorks and others do.
# ---------------------------------------------------------------------------


def _ris_date_parts(value: str) -> tuple[int, ...] | None:
    """The year, or year/month, or year/month/day ``value`` states, at whatever precision it
    carries. RIS date fields (``PY``, ``DA``, ``Y1``, ``Y2``) share one shape: up to three
    slash-separated numeric components, optionally followed by more that this parser does not
    need. ``None`` for a value that states no leading numeric component at all.
    """
    parts: list[int] = []
    for segment in value.strip().split("/"):
        segment = segment.strip()
        if not segment.isdigit():
            break
        parts.append(int(segment))
        if len(parts) == 3:
            break
    return tuple(parts) if parts else None


#: RIS's three-letter month abbreviations, for splicing Web of Science's year-less ``DA`` onto
#: ``PY``'s year (research.md R5, T026).
_MONTH_ABBREVIATIONS: dict[str, int] = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def _splice_year_less_da(value: str, year: int) -> tuple[int, ...] | None:
    """Web of Science's year-less ``DA`` -- a month alone (``DEC``), a month and day (``SEP 22``)
    -- spliced onto ``PY``'s ``year`` (research.md R5, T026). A range naming two months
    (``JUL-DEC``) is ambiguous and cannot refine to one, so it is discarded, as is anything else
    that is not cleanly one recognised month optionally followed by a day number -- ``None`` in
    every such case, distinct from D25's disagreeing-year case, which this value states no year
    to disagree with in the first place.
    """
    parts = value.strip().split()
    if len(parts) not in (1, 2):
        return None
    month = _MONTH_ABBREVIATIONS.get(parts[0].upper())
    if month is None:
        return None
    if len(parts) == 1:
        return (year, month)
    if parts[1].isdigit():
        return (year, month, int(parts[1]))
    return None


def _issued_date(raw: RISEntry) -> dict[str, Any] | None:
    """The entry's ``issued`` date, at the precision the source states (FR-015).

    ``PY`` anchors the year. Where ``DA`` also parses and agrees with ``PY``'s year, its extra
    precision (month, or month and day) is kept and no component the source did not state is
    padded in. A ``DA`` whose year disagrees is not a refinement of this date and is left alone
    (a producer that means something else by it, or a malformed tag, is not evidence for the
    date this entry actually carries — decisions.md D25). Where ``DA`` states no year at all — Web
    of Science's own shape, ``SEP 22`` or ``DEC`` — it is spliced onto ``PY``'s year instead,
    unless it is a month range (``JUL-DEC``), which is discarded rather than guessed at (T026,
    research.md R5). Without ``PY``, ``Y1`` supplies the issued date instead (research.md R5) — at
    whatever precision it states, since there is no anchor to refine.

    Where neither resolves to a structured date but one carries text, that text is kept in the
    ``literal`` fallback ``ItemDate`` already has, rather than discarded (T020, FR-026) — ``PY``'s
    own text wins, since it is the anchor tag and ``Y1`` is only ever consulted in its absence.
    """
    py_value = raw.first("PY")
    if py_value:
        py_parts = _ris_date_parts(py_value)
        if py_parts:
            year = py_parts[0]
            da_value = raw.first("DA")
            if da_value:
                da_parts = _ris_date_parts(da_value)
                if da_parts and da_parts[0] == year:
                    return {"date-parts": [list(da_parts)]}
                if da_parts is None:
                    spliced = _splice_year_less_da(da_value, year)
                    if spliced:
                        return {"date-parts": [list(spliced)]}
            return {"date-parts": [[year]]}

    y1_value = raw.first("Y1")
    if y1_value:
        y1_parts = _ris_date_parts(y1_value)
        if y1_parts:
            return {"date-parts": [list(y1_parts)]}

    if py_value:
        return {"literal": py_value}
    if y1_value:
        return {"literal": y1_value}

    return None


def _accessed_date(raw: RISEntry) -> dict[str, Any] | None:
    """The entry's ``accessed`` date: ``Y2``, and only ``Y2`` (FR-016).

    An unparseable ``Y2`` falls back to ``literal`` rather than being discarded (T020, FR-026),
    the same rule :func:`_issued_date` applies to ``PY``/``Y1``.
    """
    y2_value = raw.first("Y2")
    if not y2_value:
        return None
    y2_parts = _ris_date_parts(y2_value)
    if y2_parts:
        return {"date-parts": [list(y2_parts)]}
    return {"literal": y2_value}


# ---------------------------------------------------------------------------
# Identifiers (T014, FR-017) — ``DO``/``UR`` are unambiguous; ``SN`` is not disambiguated by the
# format itself and is resolved by value shape first, reference type second (research.md R6).
# ---------------------------------------------------------------------------

#: On these types, ``SN`` is a report or patent number, not an identifier at all (research.md R6).
_REPORT_LIKE_SN_TYPES: frozenset[str] = frozenset({"RPRT", "PAT"})

#: Scopus's inline hint, stripped before shape resolution -- it names which identifier the value
#: is, but is not part of the value itself (research.md R6, T025: ``SN - 20411723 (ISSN)``).
_SN_ANNOTATION_RE = re.compile(r"^(?P<value>.*?)\s*\((?:ISSN|ISBN)\)\s*$", re.IGNORECASE)

#: Scopus strips the hyphen from an 8-character ISSN before annotating it (research.md R6:
#: ``SN - 20411723 (ISSN)``). ``validate_issn`` requires the hyphen, so a bare candidate of this
#: shape is reformatted before validation rather than rejected for punctuation the source omitted.
_BARE_ISSN_RE = re.compile(r"^\d{7}[\dXx]$")


def _sn_candidates(raw_values: list[str]) -> list[str]:
    """Every individual value this entry's ``SN`` tag(s) carry, across Web of Science's repeated
    tag, Scopus's ``; ``-packed single tag, and EndNote's continuation-line values (which
    ``RISParser`` has already split into separate entries in ``raw_values`` by the time this runs,
    per its ``REPEATABLE_TAGS`` rule) -- with Scopus's inline ``(ISSN)``/``(ISBN)`` annotation
    stripped, since it is a hint about the value rather than part of it (research.md R6, T025).
    """
    candidates = []
    for raw_value in raw_values:
        for chunk in raw_value.split(";"):
            chunk = chunk.strip()
            if not chunk:
                continue
            match = _SN_ANNOTATION_RE.match(chunk)
            candidates.append(match.group("value").strip() if match else chunk)
    return candidates


def _sn_identifier(value: str) -> tuple[str, str] | None:
    """The ``(CSL key, value)`` pair ``value``'s shape resolves to, or ``None`` if it resolves to
    neither an ISSN nor an ISBN shape (research.md R6). Shape only — the reference-type
    tiebreaker for a value that could pass as either is not exercised by this feature's own
    corpus and is left for a later story rather than guessed at here.
    """
    issn_candidate = value
    if _BARE_ISSN_RE.match(value):
        issn_candidate = f"{value[:4]}-{value[4:]}"
    try:
        validate_issn(issn_candidate)
    except ValidationError:
        pass
    else:
        return ("ISSN", issn_candidate)

    try:
        validate_isbn(value)
    except ValidationError:
        pass
    else:
        return ("ISBN", value)

    return None


def _add_preserved(preserved: dict[str, str | list[str]], tag: str, values: list[str]) -> None:
    """Record ``values`` (already resolved to be surplus or unrescuable) under ``tag`` in
    ``preserved``: a bare string for a single value, so the common one-value case stays exactly
    the shape :class:`TestUnrescuableIdentifierPreservation` already asserts, and a list only when
    ``tag`` genuinely carries more than one surplus value (T025, T027)."""
    if not values:
        return
    preserved[tag] = values[0] if len(values) == 1 else values


#: Every tag this module resolves whatever the reference type is -- a CSL variable, a date, an
#: identifier, or a contributor role that does not vary. The type-conditional contributor tags are
#: deliberately absent: what they resolve to is a question about one entry, not about the module,
#: and :func:`_consumed_tags` is the answer to it.
_ALWAYS_CONSUMED_TAGS: frozenset[str] = frozenset(FIELD_TABLE) | frozenset(
    {"TY", "ID", "T2", "SP", "AU", "ED", "PY", "DA", "Y1", "Y2", "DO", "UR", "SN"}
)


def _consumed_tags(ref_type: str) -> frozenset[str]:
    """Every tag this module resolves for an entry of ``ref_type`` -- the production record of what
    "mapped" means, consulted by the unmapped sweep below and by the corpus-wide test that proves
    nothing else escapes it (T030, T033).

    It takes the reference type because ``A2``, ``A3`` and ``A4`` are only mapped on the types
    :func:`_contributor_role` documents a role for. Reading it as a flat set instead was how those
    tags came to be dropped on every other type: marked mapped, so the sweep skipped them, while
    no role claimed them (decisions.md D43).
    """
    return _ALWAYS_CONSUMED_TAGS | frozenset(t for t in _CONTRIBUTOR_TAGS if _contributor_role(t, ref_type))


def _unmapped(raw: RISEntry, ref_type: str) -> dict[str, str | list[str]]:
    """Every tag this entry carries that maps to no CSL variable, contributor role, date or
    identifier, preserved under its own key so nothing an entry states is silently dropped (T030,
    FR-024, FR-028). ``C7`` -- Scopus's article-number tag -- is a deliberate instance of this
    rather than a special case (decisions.md D38): it reaches the item through this sweep like
    any other unmapped tag, never through a dedicated mapping and never dropped.

    A contributor tag with no role on ``ref_type`` is another such instance (decisions.md D43):
    ``A2`` on a thesis names somebody the file states and this mapping has no CSL role for, so it
    is preserved rather than discarded.
    """
    consumed = _consumed_tags(ref_type)
    preserved: dict[str, str | list[str]] = {}
    seen: set[str] = set()
    for tag, _value in raw.tags:
        if tag in consumed or tag in seen:
            continue
        seen.add(tag)
        _add_preserved(preserved, tag, raw.values(tag))
    return preserved


def _identifiers(raw: RISEntry, ref_type: str) -> dict[str, Any]:
    """Every identifier this entry carries, mapped to its CSL top-level key.

    A value normalization could not turn into something the catalogue accepts is preserved under
    ``custom["ris"]`` rather than stored as a valid identifier or discarded (T019, FR-024, FR-027).
    Nested under that single key, never flat: `from_csl_json` turns every flat `custom` key whose
    value is a plain string into an `ItemIdentifier` row typed by that key, which is exactly what
    preservation must not become (plan.md "Preservation goes under a single `custom[\"ris\"]` key").

    ``SN``'s three producer encodings — Web of Science repeating the tag, Scopus annotating
    inline and packing several values behind ``; ``, EndNote continuing on an untagged line — are
    flattened by :func:`_sn_candidates` into one ordered list of individual values; the first
    value of each kind (ISSN, ISBN) is stored, and every other value — a second value of a kind
    already stored, or one that resolves to neither shape — is preserved (T025, research R6).

    An entry carrying more than one ``DO`` tag — a genuine Web of Science chapter record's own
    and its containing book's — stores the first, by source position, as the DOI, and preserves
    every other one, each normalized the same way as the first (T027, FR-018).

    An entry carrying more than one ``UR`` tag — every genuine EndNote and Mendeley record does,
    a search-result link followed by a duplicate DOI-resolver link — stores the first, by source
    position, as the URL, and preserves every other one the same way (T032, FR-018).

    "First" throughout means the first *populated* occurrence: each of these three blocks asks
    whether the tag carries any value at all, never whether its first occurrence does. Reading
    only index 0 dropped the whole tag — identifier and preservation alike — for an entry whose
    first ``DO`` or ``UR`` line was blank and whose second was not (decisions.md D44).
    """
    result: dict[str, Any] = {}
    preserved: dict[str, str | list[str]] = {}

    do_values = raw.values("DO")
    if any(v.strip() for v in do_values):
        normalized_dois = [IdentifierNormalizer.normalize_doi(v.strip()) for v in do_values if v.strip()]
        first_doi, *surplus_dois = normalized_dois
        try:
            validate_doi(first_doi)
        except ValidationError:
            _add_preserved(preserved, "DO", normalized_dois)
        else:
            result["DOI"] = first_doi
            _add_preserved(preserved, "DO", surplus_dois)

    ur_values = raw.values("UR")
    if any(v.strip() for v in ur_values):
        populated_urs = [v.strip() for v in ur_values if v.strip()]
        ur_value, *surplus_urs = populated_urs
        try:
            validate_url(ur_value)
        except ValidationError:
            _add_preserved(preserved, "UR", [ur_value, *surplus_urs])
        else:
            result["URL"] = ur_value
            _add_preserved(preserved, "UR", surplus_urs)

    sn_raw_values = raw.values("SN")
    if any(v.strip() for v in sn_raw_values):
        candidates = _sn_candidates(sn_raw_values)
        surplus: list[str] = []
        if ref_type in _REPORT_LIKE_SN_TYPES:
            result["number"] = candidates[0]
            surplus.extend(candidates[1:])
        else:
            for candidate in candidates:
                resolved = _sn_identifier(candidate)
                if resolved and resolved[0] not in result:
                    result[resolved[0]] = resolved[1]
                else:
                    surplus.append(candidate)
        _add_preserved(preserved, "SN", surplus)

    if preserved:
        result["custom"] = {"ris": preserved}

    return result


# ---------------------------------------------------------------------------
# Citation keys (T015, FR-019 through FR-023, FR-034) — ``ID`` verbatim where present; otherwise
# minted deterministically from the entry's own content, since RIS supplies no cite key of its
# own (unlike BibTeX's ``ID``, which is always present). An entry too sparse to mint from falls
# back to its own index rather than failing (FR-021).
# ---------------------------------------------------------------------------

#: Skipped when picking the title's first *significant* word — common articles carry no
#: bibliographic meaning of their own.
_TITLE_STOPWORDS: frozenset[str] = frozenset({"a", "an", "the"})

#: A run of letters (any script), which is what "a word" means for this purpose — digits and
#: punctuation are not carried into the minted key.
_TITLE_WORD_RE: re.Pattern[str] = re.compile(r"[^\W\d_]+", re.UNICODE)

#: Non-letter/digit characters stripped from a family name before it goes into a minted key, so
#: punctuation in the source (``O'Brien``) does not leak into the key's shape.
_KEY_COMPONENT_RE: re.Pattern[str] = re.compile(r"[^\w]+", re.UNICODE)


def _citation_key_max_length() -> int:
    """``Item.citation_key``'s ``max_length``, read from the model rather than duplicated as a
    constant here, so this stays correct if the column's width ever changes.
    """
    from literature.models import Item

    # ``max_length`` is typed ``int | None`` on the stub's generic ``Field``, since not every
    # field carries one — ``citation_key`` is a ``CharField`` and always does.
    return cast(int, Item._meta.get_field("citation_key").max_length)


def _first_significant_title_word(title: str) -> str | None:
    """The first word of ``title`` that is not a bare stopword, lowercased. ``None`` if the title
    carries no word at all (FR-021).
    """
    for word in _TITLE_WORD_RE.findall(title):
        word = str(word)
        if word.casefold() not in _TITLE_STOPWORDS:
            return word.lower()
    return None


def _first_author_family(raw: RISEntry) -> str | None:
    """The first ``AU`` value's family name, stripped of punctuation for a minted key's shape.
    ``None`` where there is no ``AU`` value, or the first one is institutional/unparsed and
    carries no ``family`` component to mint from.
    """
    au_values = raw.values("AU")
    if not au_values:
        return None
    family = _name_to_csl(au_values[0]).get("family")
    if not family:
        return None
    cleaned = _KEY_COMPONENT_RE.sub("", family)
    return cleaned or None


def _mint_citation_key(raw: RISEntry, issued: dict[str, Any] | None, index: int) -> str:
    """The key minted for an entry with no ``ID`` tag: first author family name, issued year, and
    the title's first significant word, concatenated (FR-021). An entry missing any one of the
    three is too sparse to mint from and falls back to its own index instead — deterministic
    either way, since an entry's index does not change between two imports of the same file
    (FR-023).
    """
    family = _first_author_family(raw)
    year = None
    if issued:
        date_parts = issued.get("date-parts")
        if date_parts and date_parts[0]:
            year = date_parts[0][0]
    ti_values = raw.values("TI")
    word = _first_significant_title_word(ti_values[0]) if ti_values else None

    if family and year and word:
        return f"{family.lower()}{year}{word}"
    return str(index)


def _citation_key(raw: RISEntry, issued: dict[str, Any] | None, index: int) -> str:
    """The citation key this entry carries or mints, and the key it is stored under (FR-019
    through FR-021)."""
    stated = raw.first("ID")
    if stated:
        return stated
    return _mint_citation_key(raw, issued, index)


# ---------------------------------------------------------------------------
# Published mapping (T035, FR-012, decisions.md D40) — rendered from the tables above rather than
# written alongside them, the same mechanism ``bibtex.py``'s ``_mapping_document`` established for
# the sibling format, so the page and the code cannot disagree. ``docs/ris-mapping.md`` is this
# function's output and a test asserts it still is.
# ---------------------------------------------------------------------------


def _mapping_document() -> str:
    """The reference-type, tag, contributor, date, identifier and citation-key mapping, as a
    Markdown document.

    Private on purpose, for the same reason ``bibtex._mapping_document`` is: the import contract's
    public surface is a curated, two-way-asserted list (``literature.importers.__all__``), and a
    documentation generator does not belong in it. Regenerate the published page after changing any
    table above::

        poetry run python -c "from literature.importers.ris import _mapping_document; \
            open('docs/ris-mapping.md','w').write(_mapping_document())"

    A test asserts the file on disk still matches, so a table change that skips this step fails
    rather than shipping a stale page.
    """
    lines = [
        "# RIS mapping",
        "",
        "What this package makes of a `.ris` file: which reference type becomes which CSL item",
        "type, and which tag becomes which CSL variable, contributor role, date or identifier. One",
        "format reads EndNote, Web of Science and Scopus alike — there is no producer detection, so",
        "every row below is resolved from the tag itself, never from which tool wrote the file.",
        "",
        "This page is generated from the mapping tables themselves, so it cannot describe something",
        "the importer does not do. A tag with no row here is not discarded: it is kept with the",
        'record under `custom["ris"]`, where it can be read back afterwards.',
        "",
        "## Reference types",
        "",
        "| RIS `TY` | CSL item type |",
        "| --- | --- |",
    ]
    lines += [f"| `{ris_type}` | `{csl_type}` |" for ris_type, csl_type in sorted(REFERENCE_TYPE_TABLE.items())]
    lines += [
        "",
        f"A reference type with no row above becomes `{_FALLBACK_TYPE}` rather than failing the entry.",
        "",
        "## Tags",
        "",
        "| RIS tag | CSL variable |",
        "| --- | --- |",
    ]
    lines += [f"| `{tag}` | `{csl_key}` |" for tag, csl_key in sorted(FIELD_TABLE.items())]
    lines += [
        "",
        "`T2` and `SP` map to different CSL variables depending on the entry's reference type, so",
        "they carry no single row above:",
        "",
        "- `T2` is `collection-title` on "
        + ", ".join(f"`{t}`" for t in sorted(_BOOK_LIKE_TYPES))
        + " — types that are already their own container — and `container-title` everywhere else.",
        "- `SP` is `number-of-pages` on "
        + ", ".join(f"`{t}`" for t in sorted(_PAGE_COUNT_TYPES))
        + " — a whole work rather than something with a locator inside a container — and `page` "
        + "everywhere else.",
        "",
        "## Contributors",
        "",
        "Contributor role is resolved from the tag and the entry's reference type together, since",
        "no RIS specification fixes one tag to one role across every kind of entry:",
        "",
        "| RIS tag | CSL role | Reference types |",
        "| --- | --- | --- |",
        "| `AU` | `editor` | " + ", ".join(f"`{t}`" for t in sorted(_AU_EDITOR_TYPES)) + " |",
        "| `AU` | `author` | everywhere else |",
        "| `ED` | `editor` | all — Web of Science's own editor tag, used in place of `A2` |",
        "| `A2` | `editor` | " + ", ".join(f"`{t}`" for t in sorted(_CHAPTER_LIKE_A2_EDITOR_TYPES)) + " |",
        "| `A2` | `collection-editor` | "
        + ", ".join(f"`{t}`" for t in sorted(_BOOK_LIKE_TYPES - _CHAPTER_LIKE_A2_EDITOR_TYPES))
        + " |",
        "| `A3` | `editor` | " + ", ".join(f"`{t}`" for t in sorted(_A3_EDITOR_TYPES)) + " |",
        "| `A3` | `collection-editor` | "
        + ", ".join(f"`{t}`" for t in sorted(_A3_COLLECTION_EDITOR_TYPES - _A3_EDITOR_TYPES))
        + " |",
        "| `A4` | `translator` | " + ", ".join(f"`{t}`" for t in sorted(_A4_TRANSLATOR_TYPES)) + " |",
        "",
        "A tag with no row for a given reference type is left unmapped there rather than guessed",
        "at, and its value is kept under `custom.ris` like any other unmapped tag rather than",
        "dropped — an `A2` on a thesis names somebody, whatever CSL has no role for.",
        "",
        "## Dates",
        "",
        "| RIS tag | CSL variable |",
        "| --- | --- |",
        "| `PY` | `issued` (anchor) |",
        "| `DA` | refines `issued`'s precision, when its year agrees with `PY`'s |",
        "| `Y1` | `issued`, only when `PY` is absent |",
        "| `Y2` | `accessed` |",
        "",
        "`PY` anchors the year; where `DA` also parses and agrees with it, `DA`'s extra precision",
        "(month, or month and day) is kept. A `DA` whose year disagrees is left alone, and a `DA`",
        "stating no year at all — Web of Science's own shape, `SEP 22` or `DEC` — is spliced onto",
        "`PY`'s year instead, unless it is a month range, which is discarded rather than guessed at.",
        "Without `PY`, `Y1` supplies the issued date at whatever precision it states. Where neither",
        "resolves to a structured date but one carries text, that text is kept as a literal fallback",
        "rather than discarded, `PY`'s own text taking precedence over `Y1`'s.",
        "",
        "## Identifiers",
        "",
        "| RIS tag | CSL key |",
        "| --- | --- |",
        "| `DO` | `DOI` |",
        "| `UR` | `URL` |",
        "| `SN` | `ISSN` or `ISBN`, resolved by the value's own shape |",
        "",
        "`SN` is not disambiguated by the format itself. Its value is checked against the ISSN and",
        "then the ISBN shape and stored under whichever matches, except on "
        + ", ".join(f"`{t}`" for t in sorted(_REPORT_LIKE_SN_TYPES))
        + ", where it is a report or patent number and not an identifier at all. `SN`'s three",
        "producer encodings — Web of Science repeating the tag, Scopus annotating a value inline",
        "and packing several behind `; `, EndNote continuing on an untagged line — are flattened",
        "into one ordered list of individual values before this resolution runs. `DO` and `UR` take",
        "the first value the entry carries, by source position; every other value of any of the",
        "three tags is preserved on the item rather than discarded.",
        "",
        "## Citation keys",
        "",
        "RIS supplies no cite key of its own. `ID` is taken verbatim where the entry carries one;",
        "otherwise a key is minted from the entry's own content — the first author's family name,",
        "the issued year, and the title's first significant word (skipping `a`/`an`/`the`), lowercased",
        "and run together with no separator. An entry missing any one of the three falls back to its",
        "own position in the file instead, deterministically either way. The key is stored as it stands,",
        "whether or not the catalogue already holds it, and the import result names the key as stored.",
        "",
        "## A note on producer fixtures",
        "",
        "Each producer's genuine test fixture carries a byte-for-byte fingerprint — a fragment only",
        "that producer's export is known to contain — used solely to prove the vendored corpus is",
        "what it claims to be. No mapping above depends on which producer wrote a file: there is no",
        "producer-detection branch anywhere in this module, and every row applies uniformly regardless",
        "of the file's origin.",
        "",
    ]
    return "\n".join(lines)


def _preserve(result: dict[str, Any], values: dict[str, Any]) -> None:
    """Merge ``values`` into ``result``'s preservation sink, creating it only if there is something
    to put in it.

    The sink is a single nested ``custom["ris"]`` dict, never flat keys on ``custom``:
    ``from_csl_json`` turns every flat ``custom`` key whose value is a string into an
    ``ItemIdentifier`` row, whose ``value`` is capped at 500 characters and validated on save, so a
    long preserved value written flat would fail the whole entry (plan.md "Preservation").
    """
    if not values:
        return
    result.setdefault("custom", {}).setdefault("ris", {}).update(values)


class RISFormat(BibFormat):
    """Reads ``.ris`` files, from EndNote, Web of Science and Scopus alike.

    The foundational-phase skeleton is a working :class:`RISParser` with no RIS-to-CSL mapping. US-1
    (issue #36) adds that mapping: reference types, core tags, contributors, dates, identifiers
    and citation keys.
    """

    name = "ris"
    label = _("RIS")

    def parse(self, file) -> Iterator[RISEntry | str]:
        """Yield this file's raw entries, delegating to :class:`RISParser`.

        See :meth:`RISParser.parse` for the framing, decoding and whole-file-outcome rules this
        defers to.
        """
        return RISParser().parse(file)

    def to_csl_json(self, raw: RISEntry | str) -> dict[str, Any]:
        """Turn one raw entry into CSL JSON.

        Header material arrives as a plain ``str`` (see :meth:`RISParser.parse`) and is skipped
        outright, the same pattern ``bibtex.py`` uses for a comment or preamble.

        An entry with no ``TY`` tag at all — the stray block :meth:`RISParser._entries` yields for
        a mid-file tag block that never opened one — fails alone naming what is missing, rather
        than ending the file (T021, FR-009).

        FR-009's other half — an entry carrying ``TY`` and no other bibliographic content is
        reported as skipped rather than stored as a near-empty item — raises
        :class:`~literature.importers.exceptions.SkipEntry` when every tag the entry carries is
        ``TY`` (T021, FR-009, decisions.md D31). The check is on which tags are present, not on
        whether their values are non-empty: a second tag with an empty value still disqualifies
        the skip.
        """
        if isinstance(raw, str):
            raise SkipEntry

        ty_values = raw.values("TY")
        if not ty_values:
            raise EntryError(_("This entry carries no 'TY' (reference type) tag."))

        if all(tag == "TY" for tag, _ in raw.tags):
            raise SkipEntry

        ref_type = ty_values[0].strip()

        result: dict[str, Any] = {
            "type": REFERENCE_TYPE_TABLE.get(ref_type, _FALLBACK_TYPE),
        }

        for tag, csl_key in FIELD_TABLE.items():
            value = raw.first(tag)
            if value:
                result[csl_key] = value

        t2 = raw.first("T2")
        if t2:
            result[_container_or_collection_variable(ref_type)] = t2

        sp = raw.first("SP")
        if sp:
            result[_page_variable(ref_type)] = sp

        result.update(_contributors(raw, ref_type))

        issued = _issued_date(raw)
        if issued:
            result["issued"] = issued
        accessed = _accessed_date(raw)
        if accessed:
            result["accessed"] = accessed

        identifiers = _identifiers(raw, ref_type)
        preserved = identifiers.pop("custom", None)
        result.update(identifiers)
        if preserved:
            _preserve(result, preserved["ris"])
        _preserve(result, _unmapped(raw, ref_type))

        key = _citation_key(raw, issued, raw.index)
        limit = _citation_key_max_length()
        if len(key) > limit:
            raise EntryError(
                _(
                    "This entry's citation key is {length} characters, which is longer than the "
                    "{limit}-character limit."
                ).format(length=len(key), limit=limit)
            )
        result["citation-key"] = key

        return result

    def handle_for(self, raw: RISEntry | str) -> str | None:
        """The citation key this entry will carry — verbatim ``ID``, or minted (FR-022).
        :meth:`entry_created` overrides the report for a stored entry to the key **as stored**;
        this is what a failed or skipped entry carries instead, since neither reaches storage.
        """
        if isinstance(raw, str):
            return None
        return _citation_key(raw, _issued_date(raw), raw.index)

    def entry_created(self, *, index: int, handle: str | None, item: Any, dry_run: bool) -> EntryResult:
        """Report the citation key **as stored**, read off the item rather than re-derived from
        the entry (T016, FR-022), so the report cannot drift from what the store actually holds.

        `entry_created` is the documented ``BibFormat`` override point that receives the stored
        ``item``, on a dry run too — the base drops the *report's* item for a dry run, since its
        rows do not survive the rollback, but ``item`` itself is passed to this method regardless,
        which is what lets a dry run still report the key it would have stored. No change to
        ``base.py``, ``results.py`` or ``converters.py`` is needed for this (SC-009).
        """
        return super().entry_created(index=index, handle=item.citation_key, item=item, dry_run=dry_run)

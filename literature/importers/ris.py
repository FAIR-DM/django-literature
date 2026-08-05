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
from typing import Any, ClassVar

from django.utils.translation import gettext_lazy as _

from literature.importers.base import BibFormat
from literature.importers.exceptions import ParseError, SkipEntry


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

        lines = text.splitlines()

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
        """The real framing pass: open at ``TY``, close at ``ER`` or the next ``TY`` (FR-006)."""
        header: list[str] = []
        pairs: list[list[str]] = []
        start_line = 0
        header_yielded = False
        index = 0

        for line_no, line in enumerate(lines, start=1):
            match = self._TAG_RE.match(line)

            if match is None:
                if pairs:
                    self._continue_value(pairs, line)
                elif not header_yielded:
                    header.append(line)
                continue

            tag, value = match.group(1), match.group(2)

            if tag == "TY":
                if pairs:
                    yield RISEntry(tags=tuple((t, v) for t, v in pairs), index=index, start_line=start_line)
                    index += 1
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
                continue

            if pairs:
                pairs.append([tag, value])
            elif not header_yielded:
                header.append(line)
            # else: a tag block after the first entry with no TY -- out of the foundational
            # phase's scope (US-2, T021); dropped rather than guessed at (decisions.md D18).

        if pairs:
            yield RISEntry(tags=tuple((t, v) for t, v in pairs), index=index, start_line=start_line)

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
#: that container's editor.
_CHAPTER_LIKE_A2_EDITOR_TYPES: frozenset[str] = frozenset(
    {"CHAP", "ECHAP", "CONF", "CPAPER", "ENCYC", "DICT", "SER", "EBOOK", "MUSIC", "ANCIENT", "BLOG"}
)

#: On ``BOOK``, ``A3`` is the editor (research.md R4 — the one type where ``A2``/``A3`` invert).
_A3_EDITOR_TYPES: frozenset[str] = frozenset({"BOOK"})

#: Elsewhere, where ``A3`` has a documented role, it is the collection editor.
_A3_COLLECTION_EDITOR_TYPES: frozenset[str] = frozenset(
    {"CHAP", "CONF", "SER", "EBOOK", "ADVS", "MUSIC", "SLIDE", "SOUND", "VIDEO"}
)

#: On an edited book, the author tag names the editor instead (research.md R4).
_AU_EDITOR_TYPES: frozenset[str] = frozenset({"EDBOOK"})


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


def _contributors(raw: RISEntry, ref_type: str) -> dict[str, list[dict[str, Any]]]:
    """Every contributor tag this entry carries, resolved to its CSL role in source order."""
    roles: dict[str, list[dict[str, Any]]] = {}

    au_role = "editor" if ref_type in _AU_EDITOR_TYPES else "author"
    _add_contributors(roles, au_role, raw.values("AU"))

    if ref_type in _CHAPTER_LIKE_A2_EDITOR_TYPES:
        _add_contributors(roles, "editor", raw.values("A2"))
    elif ref_type in _BOOK_LIKE_TYPES:
        _add_contributors(roles, "collection-editor", raw.values("A2"))

    if ref_type in _A3_EDITOR_TYPES:
        _add_contributors(roles, "editor", raw.values("A3"))
    elif ref_type in _A3_COLLECTION_EDITOR_TYPES:
        _add_contributors(roles, "collection-editor", raw.values("A3"))

    return roles


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
        """
        if isinstance(raw, str):
            raise SkipEntry

        ty_values = raw.values("TY")
        ref_type = ty_values[0].strip() if ty_values else ""

        result: dict[str, Any] = {
            "type": REFERENCE_TYPE_TABLE.get(ref_type, _FALLBACK_TYPE),
        }

        for tag, csl_key in FIELD_TABLE.items():
            values = raw.values(tag)
            if values and values[0].strip():
                result[csl_key] = values[0].strip()

        t2_values = raw.values("T2")
        if t2_values and t2_values[0].strip():
            result[_container_or_collection_variable(ref_type)] = t2_values[0].strip()

        sp_values = raw.values("SP")
        if sp_values and sp_values[0].strip():
            result[_page_variable(ref_type)] = sp_values[0].strip()

        result.update(_contributors(raw, ref_type))

        return result

"""Reading RIS files into the catalogue.

One format reads EndNote, Web of Science and Scopus exports alike, with no producer detection:
every tag is read by the tag itself, never by which tool wrote the file. The parser is hand-rolled
because ``rispy`` silently resynchronises past a malformed entry, where the import contract reports
what happened to every entry (``specs/005-import-references-ris/research.md``).
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
from literature.validators import (
    validate_doi,
    validate_isbn,
    validate_issn,
    validate_url,
)


@dataclasses.dataclass(frozen=True)
class RISEntry:
    """One RIS entry recovered from a file.

    ``tags`` is a sequence of pairs rather than a dict, because a repeatable tag such as ``AU`` or
    ``KW`` appears more than once (:attr:`RISParser.REPEATABLE_TAGS`).

    Attributes:
        tags: The entry's ``(tag, value)`` pairs, in source order.
        index: The entry's position among those the parser yielded.
        start_line: The line the entry's opening ``TY`` tag was found on.
    """

    tags: tuple[tuple[str, str], ...]
    index: int
    start_line: int

    def values(self, tag: str) -> list[str]:
        """Return every value this entry carries under ``tag``.

        Args:
            tag: A two-character RIS tag.

        Returns:
            The values, unstripped, in source order.
        """
        return [value for t, value in self.tags if t == tag]

    def first(self, tag: str) -> str:
        """Return this entry's first value under ``tag``, stripped.

        A tag with a blank value reads the same as an absent one, since whitespace is nothing to
        store. Use :meth:`values` for the unstripped text or every value.

        Args:
            tag: A two-character RIS tag.

        Returns:
            The first value, or ``""`` where the entry carries none.
        """
        values = self.values(tag)
        return values[0].strip() if values else ""


class RISParser:
    """Reads one ``.ris`` file into :class:`RISEntry` objects, one at a time.

    A generator, so a caller can consume one entry from a large file and leave the rest unread.
    Accepts a binary or a text handle. Bytes are decoded here as ``utf-8-sig``, so a byte-order
    mark is absorbed rather than becoming part of the first tag's value, and a decoding failure
    can name the encoding and byte offset. A text handle passes through unchanged.
    """

    #: Tolerates the one- and two-space-before-dash variants real exports use alongside the
    #: specification's own two-space form.
    _TAG_RE: ClassVar[re.Pattern[str]] = re.compile(r"^([A-Z][A-Z0-9])\s{0,2}-\s?(.*)$")

    #: RIS lines end at CR, LF or CRLF only. ``str.splitlines`` also breaks on vertical tab, form
    #: feed, NEL and the Unicode separators, which would split a value carrying one and rejoin it
    #: with a space in place of the character.
    _LINE_BREAK_RE: ClassVar[re.Pattern[str]] = re.compile(r"\r\n|\r|\n")

    #: After one of these tags an untagged line is another value. After any other tag it continues
    #: the previous value, joined with a space. Repeatability is RIS syntax, so it lives on the
    #: parser rather than the mapping tables.
    REPEATABLE_TAGS: ClassVar[frozenset[str]] = frozenset(
        {"AU", "A1", "A2", "A3", "A4", "ED", "KW", "UR", "SN", "N1"}
    )

    def parse(self, file) -> Iterator[RISEntry | str]:
        """Yield this file's entries, one at a time, in source order.

        Header material before the first ``TY`` tag is yielded once, as a plain ``str``, just
        before the first entry, and :meth:`RISFormat.to_csl_json` skips it. A file with no header
        yields no such string.

        Raises :class:`~literature.importers.exceptions.ParseError` when the file cannot be
        decoded, carries RIS tag lines but no ``TY``, or carries no tag lines at all. An empty or
        whitespace-only file yields nothing.
        """
        raw = file.read()
        if isinstance(raw, bytes):
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ParseError(
                    _(
                        "Could not decode this file as {encoding}: invalid byte at offset {offset}."
                    ).format(encoding=exc.encoding, offset=exc.start)
                ) from exc
        else:
            text = raw

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
            raise ParseError(
                _(
                    "No RIS tag lines found. Is this an RIS file, or in an unexpected encoding?"
                )
            )
        if not has_ty:
            raise ParseError(
                _(
                    "This file carries RIS tags but no 'TY' (reference type) tag anywhere."
                )
            )

        yield from self._entries(lines)

    def _entries(self, lines: list[str]) -> Iterator[RISEntry | str]:
        """Frame entries: open at ``TY``, close at ``ER`` or the next ``TY``.

        A block of tags with no ``TY`` of its own, seen after the first entry, is yielded as its
        own :class:`RISEntry` rather than dropped, and :meth:`RISFormat.to_csl_json` fails that
        entry alone. Raising here instead would end the run at this index and lose every entry
        after it.

        Args:
            lines: The file's lines.

        Yields:
            The header text once, if there is any, then each entry.
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
                    yield RISEntry(
                        tags=tuple((t, v) for t, v in pairs),
                        index=index,
                        start_line=start_line,
                    )
                    index += 1
                elif stray:
                    yield RISEntry(
                        tags=tuple((t, v) for t, v in stray),
                        index=index,
                        start_line=stray_start_line,
                    )
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
                    yield RISEntry(
                        tags=tuple((t, v) for t, v in pairs),
                        index=index,
                        start_line=start_line,
                    )
                    index += 1
                    pairs = []
                elif stray:
                    yield RISEntry(
                        tags=tuple((t, v) for t, v in stray),
                        index=index,
                        start_line=stray_start_line,
                    )
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
            yield RISEntry(
                tags=tuple((t, v) for t, v in pairs), index=index, start_line=start_line
            )
        elif stray:
            yield RISEntry(
                tags=tuple((t, v) for t, v in stray),
                index=index,
                start_line=stray_start_line,
            )

    def _continue_value(self, pairs: list[list[str]], line: str) -> None:
        """Resolve one untagged line against the tag it follows.

        Called only while a block is open, so the last pair names the tag this line continues.

        Args:
            pairs: The open block's ``[tag, value]`` pairs, modified in place.
            line: The untagged line.
        """
        last_tag = pairs[-1][0]
        if last_tag in self.REPEATABLE_TAGS:
            pairs.append([last_tag, line.strip()])
        else:
            pairs[-1][1] = f"{pairs[-1][1]} {line.strip()}"


#: RIS reference type -> CSL item type, adapted from citation-js's table (MIT). An unlisted type
#: maps to ``document``, the specification's own fallback. ``GRNT``/``GRANT`` and ``UNPD``/``UNPB``
#: are one type each, spelled as the two specification versions spell it.
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

#: A reference type with no row above becomes this rather than failing the entry.
_FALLBACK_TYPE = "document"

#: Core RIS tag -> CSL variable, for tags whose variable does not depend on the reference type.
#: ``T2`` and ``SP`` do (:func:`_container_or_collection_variable`, :func:`_page_variable`).
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

#: Reference types that are their own container, so ``T2`` names their series rather than a
#: containing work. The same fact makes ``A2`` a collection editor on them.
_BOOK_LIKE_TYPES: frozenset[str] = frozenset(
    {"BOOK", "EDBOOK", "RPRT", "ELEC", "MAP", "CLSWK", "COMP", "MULTI", "UNPB"}
)

#: Reference types where ``SP`` states a page count rather than a locator, being whole works.
_PAGE_COUNT_TYPES: frozenset[str] = frozenset({"BOOK", "EBOOK", "EDBOOK", "THES"})


def _container_or_collection_variable(ref_type: str) -> str:
    """Return the CSL variable ``T2`` maps to for ``ref_type``.

    Args:
        ref_type: The entry's ``TY`` value.

    Returns:
        ``collection-title`` or ``container-title``.
    """
    return "collection-title" if ref_type in _BOOK_LIKE_TYPES else "container-title"


def _page_variable(ref_type: str) -> str:
    """Return the CSL variable ``SP`` maps to for ``ref_type``.

    Args:
        ref_type: The entry's ``TY`` value.

    Returns:
        ``number-of-pages`` or ``page``.
    """
    return "number-of-pages" if ref_type in _PAGE_COUNT_TYPES else "page"


#: Reference types with a genuine container, where ``A2`` names its editor. ``JOUR`` is here because
#: Scopus exports book chapters as ``TY - JOUR`` with the book's editors in ``A2``.
_CHAPTER_LIKE_A2_EDITOR_TYPES: frozenset[str] = frozenset(
    {
        "CHAP",
        "ECHAP",
        "CONF",
        "CPAPER",
        "ENCYC",
        "DICT",
        "SER",
        "EBOOK",
        "MUSIC",
        "ANCIENT",
        "BLOG",
        "JOUR",
    }
)

#: On ``BOOK``, ``A3`` is the editor: the one type where ``A2`` and ``A3`` invert.
_A3_EDITOR_TYPES: frozenset[str] = frozenset({"BOOK"})

#: Elsewhere, where ``A3`` has a documented role, it is the collection editor.
_A3_COLLECTION_EDITOR_TYPES: frozenset[str] = frozenset(
    {"CHAP", "CONF", "SER", "EBOOK", "ADVS", "MUSIC", "SLIDE", "SOUND", "VIDEO"}
)

#: On an edited book, the author tag names the editor instead.
_AU_EDITOR_TYPES: frozenset[str] = frozenset({"EDBOOK"})

#: Reference types where ``A4`` has a documented role, translator. Elsewhere it is left unmapped.
_A4_TRANSLATOR_TYPES: frozenset[str] = frozenset(
    {"BOOK", "CHAP", "ANCIENT", "CLSWK", "CTLG", "DICT", "EDBOOK", "ENCYC", "PAMP"}
)


def _name_to_csl(name: str) -> dict[str, Any]:
    """Convert one RIS name to a CSL name-variable object.

    The specification's format is ``Family, Given``, with an optional suffix after a second comma.
    A name with no comma is institutional or unparsed and becomes a ``literal``, since splitting it
    would invent a split the source never stated.

    Args:
        name: One contributor value.

    Returns:
        The CSL name object, or an empty dict for a blank name.
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


def _add_contributors(
    roles: dict[str, list[dict[str, Any]]], role: str, names: list[str]
) -> None:
    """Parse each of ``names`` and append it to ``role``'s list, in order.

    Args:
        roles: The contributor lists by role, modified in place.
        role: The CSL role to append to.
        names: The raw name values.
    """
    for name in names:
        parsed = _name_to_csl(name)
        if parsed:
            roles.setdefault(role, []).append(parsed)


#: The contributor tags this module reads, in the order their roles are resolved.
_CONTRIBUTOR_TAGS: tuple[str, ...] = ("AU", "ED", "A2", "A3", "A4")


def _contributor_role(tag: str, ref_type: str) -> str | None:
    """Return the CSL role ``tag`` names on ``ref_type``.

    ``AU`` and ``ED`` always resolve. ``A2``, ``A3`` and ``A4`` resolve only on the types the 2011
    RIS specification's per-type matrix gives them a role on. A tag with no role is not discarded:
    it is preserved like any other unmapped tag, and :func:`_consumed_tags` keeps the two in step.

    Args:
        tag: A contributor tag.
        ref_type: The entry's ``TY`` value.

    Returns:
        The CSL role, or ``None`` where the tag names none on this type.
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
    """Resolve every contributor tag this entry carries to its CSL role.

    ``ED`` is Web of Science's own editor tag, used in place of ``A2``, so it is ``editor`` on
    every type.

    Args:
        raw: The entry.
        ref_type: The entry's ``TY`` value.

    Returns:
        The CSL name lists keyed by role, each in source order.
    """
    roles: dict[str, list[dict[str, Any]]] = {}

    for tag in _CONTRIBUTOR_TAGS:
        role = _contributor_role(tag, ref_type)
        if role:
            _add_contributors(roles, role, raw.values(tag))

    return roles


def _ris_date_parts(value: str) -> tuple[int, ...] | None:
    """Return the date components ``value`` states, at whatever precision it carries.

    RIS date tags share one shape: up to three slash-separated numbers, optionally followed by
    more that this parser does not need.

    Args:
        value: A ``PY``, ``DA``, ``Y1`` or ``Y2`` value.

    Returns:
        The year, then month and day where stated, or ``None`` with no leading number.
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


#: RIS's three-letter month abbreviations, for Web of Science's year-less ``DA``.
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
    """Splice Web of Science's year-less ``DA`` onto ``PY``'s ``year``.

    The value is a month alone (``DEC``) or a month and day (``SEP 22``). A month range such as
    ``JUL-DEC`` cannot refine to one month and is discarded, as is anything else not cleanly in
    that shape.

    Args:
        value: The ``DA`` value.
        year: The year ``PY`` states.

    Returns:
        The spliced date components, or ``None``.
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
    """Return the entry's ``issued`` date, at the precision the source states.

    ``PY`` anchors the year. A ``DA`` whose year agrees adds its month, or month and day, with
    nothing padded in. A ``DA`` whose year disagrees is not evidence for this date and is ignored,
    and a ``DA`` with no year, Web of Science's shape, is spliced onto ``PY``'s year. Without
    ``PY``, ``Y1`` supplies the date, since Ovid, CINAHL and RefWorks write it. Where neither
    resolves to a structured date, the text goes to the ``literal`` slot, ``PY``'s first.

    Args:
        raw: The entry.

    Returns:
        The CSL date, or ``None`` when the entry states none.
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
    """Return the entry's ``accessed`` date, from ``Y2`` only.

    An unparseable ``Y2`` goes to the ``literal`` slot, as in :func:`_issued_date`.

    Args:
        raw: The entry.

    Returns:
        The CSL date, or ``None`` when the entry has no ``Y2``.
    """
    y2_value = raw.first("Y2")
    if not y2_value:
        return None
    y2_parts = _ris_date_parts(y2_value)
    if y2_parts:
        return {"date-parts": [list(y2_parts)]}
    return {"literal": y2_value}


#: On these types ``SN`` is a report or patent number, not an identifier.
_REPORT_LIKE_SN_TYPES: frozenset[str] = frozenset({"RPRT", "PAT"})

#: Scopus's inline hint, as in ``SN - 20411723 (ISSN)``, which is not part of the value.
_SN_ANNOTATION_RE = re.compile(
    r"^(?P<value>.*?)\s*\((?:ISSN|ISBN)\)\s*$", re.IGNORECASE
)

#: Scopus strips the hyphen from an ISSN, which ``validate_issn`` requires, so a bare candidate of
#: this shape is reformatted before validation.
_BARE_ISSN_RE = re.compile(r"^\d{7}[\dXx]$")


def _sn_candidates(raw_values: list[str]) -> list[str]:
    """Flatten every value this entry's ``SN`` tags carry into one ordered list.

    Covers Web of Science's repeated tag, Scopus's ``; ``-packed single tag and EndNote's
    continuation lines, which the parser has already split into separate values. Scopus's
    ``(ISSN)``/``(ISBN)`` annotation is stripped.

    Args:
        raw_values: Every ``SN`` value, in source order.

    Returns:
        The individual values.
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
    """Resolve ``value`` to an ISSN or an ISBN by its shape alone.

    Args:
        value: One ``SN`` candidate.

    Returns:
        The ``(CSL key, value)`` pair, or ``None`` if it has neither shape.
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


def _add_preserved(
    preserved: dict[str, str | list[str]], tag: str, values: list[str]
) -> None:
    """Record surplus or unrescuable ``values`` under ``tag`` in ``preserved``.

    A single value is stored as a bare string, the common case, and a list only when there is more
    than one.

    Args:
        preserved: The preserved values by tag, modified in place.
        tag: The RIS tag.
        values: The values to preserve.
    """
    if not values:
        return
    preserved[tag] = values[0] if len(values) == 1 else values


#: Every tag this module resolves whatever the reference type. The type-conditional contributor
#: tags are absent, since :func:`_consumed_tags` decides those per entry.
_ALWAYS_CONSUMED_TAGS: frozenset[str] = frozenset(FIELD_TABLE) | frozenset(
    {"TY", "ID", "T2", "SP", "AU", "ED", "PY", "DA", "Y1", "Y2", "DO", "UR", "SN"}
)


def _consumed_tags(ref_type: str) -> frozenset[str]:
    """Return every tag this module resolves for an entry of ``ref_type``.

    The one record of what "mapped" means, used by the unmapped sweep. It takes the reference type
    because ``A2``, ``A3`` and ``A4`` are mapped only where :func:`_contributor_role` gives them a
    role. A flat set would mark them mapped everywhere, and the sweep would drop them elsewhere.

    Args:
        ref_type: The entry's ``TY`` value.

    Returns:
        The consumed tags.
    """
    return _ALWAYS_CONSUMED_TAGS | frozenset(
        t for t in _CONTRIBUTOR_TAGS if _contributor_role(t, ref_type)
    )


def _unmapped(raw: RISEntry, ref_type: str) -> dict[str, str | list[str]]:
    """Return every tag this entry carries that nothing else maps, so nothing is silently dropped.

    Scopus's article-number tag ``C7`` reaches the item this way rather than through a dedicated
    mapping, as does a contributor tag with no role on ``ref_type``, such as ``A2`` on a thesis.

    Args:
        raw: The entry.
        ref_type: The entry's ``TY`` value.

    Returns:
        The unmapped values, keyed by tag.
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
    """Return every identifier this entry carries, keyed by CSL top-level key.

    A value normalization cannot rescue is preserved under ``custom["ris"]``, never flat on
    ``custom``, because ``from_csl_json`` turns every flat string-valued ``custom`` key into an
    ``ItemIdentifier`` row.

    ``DO`` and ``UR`` store their first populated value, by source position, and preserve the rest:
    a Web of Science chapter carries its own DOI and its book's, and EndNote and Mendeley follow the
    URL with a DOI-resolver link. ``SN`` values are flattened by :func:`_sn_candidates`, then the
    first of each kind, ISSN and ISBN, is stored and the rest preserved. On report-like types
    ``SN`` is stored as ``number`` instead.

    Args:
        raw: The entry.
        ref_type: The entry's ``TY`` value.

    Returns:
        The CSL identifiers, plus ``custom["ris"]`` when anything was preserved.
    """
    result: dict[str, Any] = {}
    preserved: dict[str, str | list[str]] = {}

    do_values = raw.values("DO")
    if any(v.strip() for v in do_values):
        normalized_dois = [
            IdentifierNormalizer.normalize_doi(v.strip())
            for v in do_values
            if v.strip()
        ]
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


#: Articles, skipped when picking the title's first significant word.
_TITLE_STOPWORDS: frozenset[str] = frozenset({"a", "an", "the"})

#: A run of letters in any script, so digits and punctuation stay out of a minted key.
_TITLE_WORD_RE: re.Pattern[str] = re.compile(r"[^\W\d_]+", re.UNICODE)

#: Punctuation stripped from a family name, such as ``O'Brien``'s, before it goes into a key.
_KEY_COMPONENT_RE: re.Pattern[str] = re.compile(r"[^\w]+", re.UNICODE)


def _citation_key_max_length() -> int:
    """Return ``Item.citation_key``'s ``max_length``, read from the model so it stays in step.

    Returns:
        The column width.
    """
    from literature.models import Item

    # ``max_length`` is typed ``int | None`` on the stub's generic ``Field``, since not every
    # field carries one — ``citation_key`` is a ``CharField`` and always does.
    return cast(int, Item._meta.get_field("citation_key").max_length)


def _first_significant_title_word(title: str) -> str | None:
    """Return the first word of ``title`` that is not an article, lowercased.

    Args:
        title: The entry's title.

    Returns:
        The word, or ``None`` if the title carries no word.
    """
    for word in _TITLE_WORD_RE.findall(title):
        word = str(word)
        if word.casefold() not in _TITLE_STOPWORDS:
            return word.lower()
    return None


def _first_author_family(raw: RISEntry) -> str | None:
    """Return the first ``AU`` value's family name, stripped of punctuation.

    Args:
        raw: The entry.

    Returns:
        The family name, or ``None`` when there is no ``AU`` or the first is a literal name.
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
    """Mint a citation key for an entry with no ``ID`` tag.

    RIS has no cite key of its own, so the key is the first author's family name, the issued year
    and the title's first significant word, run together. An entry missing any of the three falls
    back to its index. Either way the key is the same on every import of the same file.

    Args:
        raw: The entry.
        issued: The entry's CSL ``issued`` date, if any.
        index: The entry's position in the file.

    Returns:
        The minted key.
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
    """Return the citation key this entry states in ``ID``, or a minted one.

    Args:
        raw: The entry.
        issued: The entry's CSL ``issued`` date, if any.
        index: The entry's position in the file.

    Returns:
        The citation key.
    """
    stated = raw.first("ID")
    if stated:
        return stated
    return _mint_citation_key(raw, issued, index)


def _mapping_document() -> str:
    """Render the RIS mapping as a Markdown document.

    Private, because a documentation generator does not belong in the import contract's public
    surface. Regenerate ``docs/ris-mapping.md`` after changing any table above::

        uv run python -c "from literature.importers.ris import _mapping_document; \
            open('docs/ris-mapping.md','w').write(_mapping_document())"

    A test asserts the file on disk still matches.

    Returns:
        The Markdown page.
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
    lines += [
        f"| `{ris_type}` | `{csl_type}` |"
        for ris_type, csl_type in sorted(REFERENCE_TYPE_TABLE.items())
    ]
    lines += [
        "",
        f"A reference type with no row above becomes `{_FALLBACK_TYPE}` rather than failing the entry.",
        "",
        "## Tags",
        "",
        "| RIS tag | CSL variable |",
        "| --- | --- |",
    ]
    lines += [
        f"| `{tag}` | `{csl_key}` |" for tag, csl_key in sorted(FIELD_TABLE.items())
    ]
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
        "| `AU` | `editor` | "
        + ", ".join(f"`{t}`" for t in sorted(_AU_EDITOR_TYPES))
        + " |",
        "| `AU` | `author` | everywhere else |",
        "| `ED` | `editor` | all — Web of Science's own editor tag, used in place of `A2` |",
        "| `A2` | `editor` | "
        + ", ".join(f"`{t}`" for t in sorted(_CHAPTER_LIKE_A2_EDITOR_TYPES))
        + " |",
        "| `A2` | `collection-editor` | "
        + ", ".join(
            f"`{t}`" for t in sorted(_BOOK_LIKE_TYPES - _CHAPTER_LIKE_A2_EDITOR_TYPES)
        )
        + " |",
        "| `A3` | `editor` | "
        + ", ".join(f"`{t}`" for t in sorted(_A3_EDITOR_TYPES))
        + " |",
        "| `A3` | `collection-editor` | "
        + ", ".join(
            f"`{t}`" for t in sorted(_A3_COLLECTION_EDITOR_TYPES - _A3_EDITOR_TYPES)
        )
        + " |",
        "| `A4` | `translator` | "
        + ", ".join(f"`{t}`" for t in sorted(_A4_TRANSLATOR_TYPES))
        + " |",
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
    """Merge ``values`` into ``result``'s ``custom["ris"]``, creating it only when needed.

    Nested, never flat on ``custom``: ``from_csl_json`` turns every flat string-valued ``custom``
    key into an ``ItemIdentifier`` row, capped at 500 characters and validated on save, so a long
    value written flat would fail the whole entry.

    Args:
        result: The entry's CSL JSON, modified in place.
        values: The values to preserve, keyed by tag.
    """
    if not values:
        return
    result.setdefault("custom", {}).setdefault("ris", {}).update(values)


class RISFormat(BibFormat):
    """Reads ``.ris`` files, from EndNote, Web of Science and Scopus alike."""

    name = "ris"
    label = _("RIS")

    def parse(self, file) -> Iterator[RISEntry | str]:
        """Yield this file's raw entries, delegating to :meth:`RISParser.parse`."""
        return RISParser().parse(file)

    def to_csl_json(self, raw: RISEntry | str) -> dict[str, Any]:
        """Turn one raw entry into CSL JSON.

        An entry carrying only ``TY`` is skipped rather than stored as a near-empty item. The check
        is on which tags are present, so a second tag with an empty value still counts.

        Args:
            raw: An entry, or the header text :meth:`RISParser.parse` yields.

        Returns:
            The entry as CSL JSON.

        Raises:
            SkipEntry: ``raw`` is header material, or the entry carries only ``TY``.
            EntryError: The entry has no ``TY`` tag, or its citation key is longer than the
                catalogue allows. Either fails this entry alone.
        """
        if isinstance(raw, str):
            raise SkipEntry(_("This is header material, not a record."))

        ty_values = raw.values("TY")
        if not ty_values:
            raise EntryError(_("This entry carries no 'TY' (reference type) tag."))

        if all(tag == "TY" for tag, _ in raw.tags):
            raise SkipEntry(
                _(
                    "This entry carries only a 'TY' (reference type) tag and no other content."
                )
            )

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
        """Return the citation key this entry will carry, stated in ``ID`` or minted.

        :meth:`entry_created` reports a stored entry under its key as stored, so this is the handle
        only a failed or skipped entry keeps.

        Args:
            raw: An entry, or header text.

        Returns:
            The citation key, or ``None`` for header material.
        """
        if isinstance(raw, str):
            return None
        return _citation_key(raw, _issued_date(raw), raw.index)

    def entry_created(
        self, *, index: int, handle: str | None, item: Any, dry_run: bool
    ) -> EntryResult:
        """Report the key as stored, read off the item, which arrives on a dry run too."""
        return super().entry_created(
            index=index, handle=item.citation_key, item=item, dry_run=dry_run
        )

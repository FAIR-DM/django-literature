"""Reading BibTeX files into the catalogue.

One format reads both classic BibTeX and BibLaTeX: they share a file syntax, and
someone exporting a library cannot tell which they were given. Where a BibLaTeX
field and its classic counterpart name the same CSL variable and disagree
(``date`` over ``year``/``month``, ``journaltitle`` over ``journal``), the
BibLaTeX field wins, since BibLaTeX's manual treats the classic one as legacy.
``bibtexparser`` is imported here and nowhere else, which a test asserts, so the
parser stays replaceable.
"""

import calendar
import dataclasses
import datetime
import re
from collections.abc import Iterator
from typing import Any

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import splitname
from bibtexparser.latexenc import latex_to_unicode
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from literature.importers.base import BibFormat
from literature.importers.exceptions import ParseError, SkipEntry
from literature.importers.normalizers import IdentifierNormalizer
from literature.validators import validate_identifier


@dataclasses.dataclass(frozen=True)
class _Mapped:
    """One table entry: the CSL name a source key maps to, and its dialect."""

    csl: str
    dialect: str  # "classic" | "biblatex"


#: BibTeX entry type -> CSL item type. BibLaTeX's ``set`` and ``xdata`` are
#: absent on purpose, as neither is a bibliographic record. Where Zotero's type
#: map (``tests/data/csl-typeMap.xml``) states an equivalent, it is followed.
ENTRY_TYPE_TABLE: dict[str, _Mapped] = {
    "article": _Mapped("article-journal", "classic"),
    "artwork": _Mapped("graphic", "biblatex"),
    "book": _Mapped("book", "classic"),
    "bookinbook": _Mapped("chapter", "biblatex"),
    "booklet": _Mapped("pamphlet", "classic"),
    "collection": _Mapped("collection", "biblatex"),
    "conference": _Mapped("paper-conference", "classic"),
    "dataset": _Mapped("dataset", "biblatex"),
    "electronic": _Mapped("webpage", "biblatex"),
    "inbook": _Mapped("chapter", "classic"),
    "incollection": _Mapped("chapter", "classic"),
    "inproceedings": _Mapped("paper-conference", "classic"),
    "inreference": _Mapped("entry", "biblatex"),
    "manual": _Mapped("book", "classic"),
    "mastersthesis": _Mapped("thesis", "classic"),
    "misc": _Mapped("document", "classic"),
    "mvbook": _Mapped("book", "biblatex"),
    "mvcollection": _Mapped("collection", "biblatex"),
    "mvproceedings": _Mapped("book", "biblatex"),
    "mvreference": _Mapped("book", "biblatex"),
    "online": _Mapped("webpage", "biblatex"),
    "patent": _Mapped("patent", "biblatex"),
    "periodical": _Mapped("periodical", "biblatex"),
    "phdthesis": _Mapped("thesis", "classic"),
    "proceedings": _Mapped("book", "classic"),
    "reference": _Mapped("book", "biblatex"),
    "report": _Mapped("report", "biblatex"),
    "suppbook": _Mapped("chapter", "biblatex"),
    "suppcollection": _Mapped("chapter", "biblatex"),
    "techreport": _Mapped("report", "classic"),
    "thesis": _Mapped("thesis", "biblatex"),
    "unpublished": _Mapped("manuscript", "classic"),
}

#: An entry type with no CSL equivalent lands here rather than failing the entry.
_FALLBACK_TYPE = "document"

#: Scalar BibTeX field -> CSL variable. Names, dates and identifiers have their
#: own tables. A field in no table, ``key`` and ``crossref`` included, is kept
#: under ``custom["bibtex"]`` instead (:func:`_unmapped_fields`).
FIELD_TABLE: dict[str, _Mapped] = {
    "abstract": _Mapped("abstract", "classic"),
    "address": _Mapped("publisher-place", "classic"),
    "annotation": _Mapped("annote", "biblatex"),
    "annote": _Mapped("annote", "classic"),
    "booktitle": _Mapped("container-title", "classic"),
    "chapter": _Mapped("chapter-number", "classic"),
    "edition": _Mapped("edition", "classic"),
    "howpublished": _Mapped("medium", "classic"),
    "institution": _Mapped("publisher", "classic"),
    "journal": _Mapped("container-title", "classic"),
    "journaltitle": _Mapped("container-title", "biblatex"),
    "keywords": _Mapped("keyword", "classic"),
    "langid": _Mapped("language", "biblatex"),
    "language": _Mapped("language", "classic"),
    "location": _Mapped("publisher-place", "biblatex"),
    "note": _Mapped("note", "classic"),
    "number": _Mapped("issue", "classic"),
    "organization": _Mapped("publisher", "classic"),
    "pages": _Mapped("page", "classic"),
    "pagetotal": _Mapped("number-of-pages", "biblatex"),
    "publisher": _Mapped("publisher", "classic"),
    "school": _Mapped("publisher", "classic"),
    "series": _Mapped("collection-title", "classic"),
    "shorttitle": _Mapped("title-short", "classic"),
    "title": _Mapped("title", "classic"),
    "type": _Mapped("genre", "classic"),
    "volume": _Mapped("volume", "classic"),
}

#: BibTeX identifier field -> top-level CSL identifier key.
IDENTIFIER_FIELD_TABLE: dict[str, _Mapped] = {
    "doi": _Mapped("DOI", "classic"),
    "isbn": _Mapped("ISBN", "classic"),
    "issn": _Mapped("ISSN", "classic"),
    "url": _Mapped("URL", "classic"),
}

#: BibTeX name-list field -> CSL name-variable role.
NAME_FIELD_TABLE: dict[str, _Mapped] = {
    "author": _Mapped("author", "classic"),
    "editor": _Mapped("editor", "classic"),
}

#: Full month names as ``@string`` macros. ``common_strings`` defines ``jul`` but
#: not ``july``, so Crossref's bare ``month = July`` would otherwise be an
#: undefined macro and abort the whole file's parse.
_MONTH_MACROS: dict[str, str] = {
    calendar.month_name[i].lower(): calendar.month_name[i] for i in range(1, 13)
}

#: Month name or abbreviation (case-insensitive) -> its 1-based number, covering
#: both macro expansions and an abbreviation written in braces or quotes.
_MONTH_NUMBERS: dict[str, int] = {
    calendar.month_abbr[i].lower(): i for i in range(1, 13)
} | {calendar.month_name[i].lower(): i for i in range(1, 13)}


def _month_number(raw: str) -> int | None:
    """Return the 1-based month number a ``month`` value states.

    Args:
        raw: The field's value, a number or a month name.

    Returns:
        The month number, or ``None`` if the value names no month.
    """
    text = raw.strip()
    if text.isdigit():
        value = int(text)
        return value if 1 <= value <= 12 else None
    return _MONTH_NUMBERS.get(text.lower())


#: The five XML predefined entities and numeric character references. Not
#: :func:`html.unescape`, which also resolves HTML5 named references without a
#: closing semicolon and would turn a title's ``&sect`` into ``§``.
_ENTITY_RE = re.compile(
    r"&(?:(amp|lt|gt|quot|apos)|#(\d{1,7})|#[xX]([0-9a-fA-F]{1,6}));"
)

_NAMED_ENTITIES = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}


def _unescape_entities(value: str) -> str:
    """Resolve XML character escaping a source wrote into a field's text.

    Runs after the LaTeX decode, so a value escaped for both LaTeX and XML
    resolves through both layers.

    Args:
        value: The LaTeX-decoded field text.

    Returns:
        The text with entities and character references resolved.
    """

    def replace(match: re.Match[str]) -> str:
        name, decimal, hexadecimal = match.groups()
        if name:
            return _NAMED_ENTITIES[name]
        code = int(decimal) if decimal else int(hexadecimal, 16)
        return chr(code) if 0 < code <= 0x10FFFF else match.group(0)

    return _ENTITY_RE.sub(replace, value)


def _clean_text(value: str) -> str:
    """Decode LaTeX escapes to the characters they represent.

    ``latex_to_unicode`` also strips capitalization-protecting braces
    (``{DNA}`` becomes ``DNA``) and leaves a construct it does not recognise in
    place. It is pure string substitution, so it never evaluates its input.
    XML escaping is resolved afterwards (:func:`_unescape_entities`): a ``.bib``
    file is not XML, but real exports carry escaping from upstream pipelines.

    Args:
        value: The raw field text.

    Returns:
        The decoded text.
    """
    return _unescape_entities(str(latex_to_unicode(value)))


#: Field-specific normalization applied after the LaTeX decode.
_IDENTIFIER_NORMALIZERS: dict[str, Any] = {
    "doi": IdentifierNormalizer.normalize_doi,
    "isbn": IdentifierNormalizer.normalize_isbn,
}


def _clean_identifier(bib_key: str, value: str) -> str:
    """Normalize one identifier field's value ahead of validation.

    Args:
        bib_key: The BibTeX field name, such as ``doi``.
        value: The raw field text.

    Returns:
        The decoded and normalized value.
    """
    cleaned = _clean_text(value).strip()
    normalizer = _IDENTIFIER_NORMALIZERS.get(bib_key)
    if normalizer is not None:
        cleaned = normalizer(cleaned)
    return cleaned


def _is_wrapped_literal(name: str) -> bool:
    """Return whether ``name`` is wrapped entirely in one brace pair.

    ``author = {{World Wide Web Consortium}}`` reaches here as
    ``{World Wide Web Consortium}`` once the parser strips the field's own
    delimiter. The remaining pair is BibTeX's convention for "do not split this
    name", used for institutions.

    Args:
        name: One name from a name list.

    Returns:
        ``True`` if one brace pair encloses the whole name.
    """
    if not (name.startswith("{") and name.endswith("}")):
        return False
    depth = 0
    for index, char in enumerate(name):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and index != len(name) - 1:
                return False
    return depth == 0


def _split_name_list(raw: str) -> list[str]:
    """Split a BibTeX name list on ``and``, ignoring one inside braces.

    The split tracks brace depth, so a braced literal name containing the word
    ``and`` stays whole.

    Args:
        raw: The name-list field's value.

    Returns:
        The non-empty names, in order.
    """
    names: list[str] = []
    current: list[str] = []
    depth = 0
    for token in raw.split():
        depth += token.count("{") - token.count("}")
        if depth == 0 and token.lower() == "and" and current:
            names.append(" ".join(current))
            current = []
        else:
            current.append(token)
    if current:
        names.append(" ".join(current))
    return [name for name in (n.strip() for n in names) if name]


def _name_to_csl(name: str) -> dict[str, Any]:
    """Convert one BibTeX name to a CSL name-variable object.

    A brace-wrapped name becomes an unsplit ``literal``. Any other name is
    decoded, then split by ``splitname`` into First/von/Last/Jr, which map onto
    CSL's ``given``, ``non-dropping-particle``, ``family`` and ``suffix``.
    Non-strict mode, so a name that cannot be parsed cleanly does not fail the
    entry. Decoding runs after the brace check, because :func:`_clean_text`
    would remove the brace pair the check looks for.

    Args:
        name: One name from a name list.

    Returns:
        The CSL name object, or an empty dict when the name names nobody.
    """
    stripped = name.strip()
    if not stripped:
        return {}
    if _is_wrapped_literal(stripped):
        # Empty braces name nobody. Returning nothing leaves the field
        # unconsumed, so it is preserved rather than stored as a nameless row.
        literal = _clean_text(stripped[1:-1]).strip()
        return {"literal": literal} if literal else {}

    parts = splitname(_clean_text(stripped), strict_mode=False)
    result: dict[str, Any] = {}
    given = " ".join(parts.get("first", []))
    family = " ".join(parts.get("last", []))
    von = " ".join(parts.get("von", []))
    jr = " ".join(parts.get("jr", []))
    if given:
        result["given"] = given
    if family:
        result["family"] = family
    if von:
        result["non-dropping-particle"] = von
    if jr:
        result["suffix"] = jr
    return result


def _names_to_csl(raw: str) -> list[dict[str, Any]]:
    """Convert a whole BibTeX name-list field to CSL name objects.

    Args:
        raw: The name-list field's value.

    Returns:
        One CSL name object per name, in source order.
    """
    return [
        parsed
        for parsed in (_name_to_csl(one) for one in _split_name_list(raw))
        if parsed
    ]


#: BibLaTeX's ``date``: a year, year-month or full date in truncated ISO 8601.
#: Ranges and season qualifiers do not match and fall to the ``literal`` slot.
_BIBLATEX_DATE_RE = re.compile(
    r"^(?P<year>\d{4})(-(?P<month>\d{2})(-(?P<day>\d{2}))?)?$"
)


def _parse_biblatex_date(value: str) -> dict[str, Any] | None:
    """Return the CSL date a BibLaTeX ``date`` value states, at its own precision.

    Args:
        value: The field's value.

    Returns:
        A CSL ``date-parts`` object, or ``None`` when the value is not a real
        date in one of the three shapes. The caller decides what happens then.
    """
    match = _BIBLATEX_DATE_RE.match(value.strip())
    if not match:
        return None
    parts = [int(match["year"])]
    if match["month"]:
        parts.append(int(match["month"]))
        if match["day"]:
            parts.append(int(match["day"]))
    # Shape is not validity: ``2024-13-45`` matches but names no real day, and
    # would fail the whole entry instead of falling to the ``literal`` slot.
    year, month, day = [*parts, 1, 1][:3]
    try:
        datetime.date(year, month, day)
    except ValueError:
        return None
    return {"date-parts": [parts]}


def _issued_date(fields: dict[str, str]) -> tuple[dict[str, Any] | None, set[str]]:
    """Return the entry's ``issued`` date, at the precision the source states.

    A BibLaTeX ``date`` wins outright, even over a disagreeing ``year`` and
    ``month``, and one that will not parse goes to CSL's ``literal`` slot
    rather than falling through to ``year``. Without ``date``, ``year`` gives
    year precision and ``year`` with a recognised ``month`` gives month
    precision, with nothing padded in. A ``year`` that is not a number
    (``in press``) also goes to ``literal``.

    Args:
        fields: The entry's raw fields.

    Returns:
        The CSL date, or ``None`` when the entry states none, and the source
        fields it was built from. An unresolvable ``month`` is left out of that
        set so it is preserved rather than dropped.
    """
    date = fields.get("date", "").strip()
    if date:
        return _parse_biblatex_date(date) or {"literal": date}, {"date"}

    year = fields.get("year", "").strip()
    if not year:
        return None, set()
    if not year.isdigit():
        return {"literal": year}, {"year"}
    parts = [int(year)]
    used = {"year"}
    month = fields.get("month", "")
    if month:
        month_number = _month_number(month)
        if month_number is not None:
            parts.append(month_number)
            used.add("month")
    return {"date-parts": [parts]}, used


#: ``babel``/``polyglossia`` language names, as a BibLaTeX ``langid`` states
#: them, -> BCP 47 tag. ``english`` says nothing about which English, so it is
#: ``en`` rather than a guess between ``en-GB`` and ``en-US``.
_LANGUAGE_TAGS: dict[str, str] = {
    "american": "en-US",
    "australian": "en-AU",
    "brazilian": "pt-BR",
    "british": "en-GB",
    "canadian": "en-CA",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "finnish": "fi",
    "french": "fr",
    "german": "de",
    "greek": "el",
    "italian": "it",
    "japanese": "ja",
    "ngerman": "de",
    "norsk": "no",
    "polish": "pl",
    "portuguese": "pt",
    "russian": "ru",
    "spanish": "es",
    "swedish": "sv",
    "turkish": "tr",
    "ukrainian": "uk",
    "usenglish": "en-US",
}

#: A value already written as a language tag (``en``, ``en-GB``, ``pt-BR``).
_LANGUAGE_TAG_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")


def _language_tag(value: str) -> str | None:
    """Return the BCP 47 tag ``value`` states.

    The catalogue's ``language`` holds a tag and nothing longer, so a name this
    table does not carry is neither truncated nor fails the entry. It goes
    unconsumed and is preserved with the other unmapped fields.

    Args:
        value: A language name or tag.

    Returns:
        The tag, or ``None`` if the value states none.
    """
    text = value.strip()
    tag = _LANGUAGE_TAGS.get(text.casefold())
    if tag:
        return tag
    return text if _LANGUAGE_TAG_RE.match(text) and len(text) <= 10 else None


#: Keys ``bibtexparser`` adds to every entry, already surfaced as ``type`` and
#: ``citation-key``.
_STRUCTURAL_KEYS = frozenset({"ENTRYTYPE", "ID"})


def _unmapped_fields(raw: dict[str, Any], consumed: set[str]) -> dict[str, str]:
    """Return every field ``raw`` carries that conversion did not use.

    Decided from what conversion consumed, not from the mapping tables: a
    recognised field can still land nowhere, such as an unresolvable
    ``language`` or an ``author`` that parses to no names. A key is kept unless
    it was consumed, is a structural key, or starts with an underscore, which
    marks the parser's own bookkeeping such as ``_FROM_CROSSREF``. ``crossref``
    is kept like any other field. Empty values are dropped, since ``{}`` is
    what a reference manager writes for a field it holds no value for.

    Args:
        raw: The parsed entry.
        consumed: The fields conversion used.

    Returns:
        The unused, non-empty fields.
    """
    return {
        key: value
        for key, value in raw.items()
        if key not in _STRUCTURAL_KEYS
        and key not in consumed
        and not key.startswith("_")
        and value
    }


def _mapping_document() -> str:
    """Render the field and entry-type mapping as a Markdown document.

    Private, because a documentation generator does not belong in the import
    contract's public surface. Regenerate ``docs/bibtex-mapping.md`` after
    changing any table above::

        uv run python -c "from literature.importers.bibtex import _mapping_document; \
            open('docs/bibtex-mapping.md','w').write(_mapping_document())"

    A test asserts the file on disk still matches.

    Returns:
        The Markdown page.
    """
    lines = [
        "# BibTeX mapping",
        "",
        "What this package makes of a `.bib` file: which entry type becomes which",
        "CSL item type, and which field becomes which CSL variable. Both dialects are",
        "listed together, each row saying which one it belongs to.",
        "",
        "This page is generated from the mapping tables themselves, so it cannot",
        "describe something the importer does not do. A field with no row here is not",
        "discarded: it is kept with the record under `custom`, where it can be read",
        "back afterwards.",
        "",
        "## Entry types",
        "",
        "| BibTeX entry type | CSL item type | Dialect |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| `@{key}` | `{m.csl}` | {m.dialect} |"
        for key, m in sorted(ENTRY_TYPE_TABLE.items())
    ]
    lines += [
        "",
        f"An entry type with no row above becomes `{_FALLBACK_TYPE}` rather than failing the entry.",
        "",
        "## Fields",
        "",
        "| BibTeX field | CSL variable | Dialect |",
        "| --- | --- | --- |",
    ]
    fields = {**FIELD_TABLE, **NAME_FIELD_TABLE, **IDENTIFIER_FIELD_TABLE}
    lines += [
        f"| `{key}` | `{m.csl}` | {m.dialect} |" for key, m in sorted(fields.items())
    ]
    lines += [
        "",
        "## Dates",
        "",
        "| BibTeX field | CSL variable |",
        "| --- | --- |",
        "| `date` | `issued` |",
        "| `year`, `month` | `issued` |",
        "| `urldate` | `accessed` |",
        "",
        "A BibLaTeX `date` takes precedence over a classic `year` and `month` pair, and",
        "a date that will not resolve to a structured value is kept as written rather",
        "than dropped.",
        "",
    ]
    return "\n".join(lines)


#: Any BibTeX block at all: ``@article{``, ``@comment{``, ``@string(``.
_BIBTEX_BLOCK_RE = re.compile(r"@\s*[A-Za-z]+\s*[{(]")


@dataclasses.dataclass(frozen=True)
class _NonRecord:
    """A ``@comment`` or ``@preamble`` block: recognised, but not an entry.

    ``bibtexparser`` collects both kinds as plain strings, so the kind is
    recorded here for :meth:`BibTeXFormat.to_csl_json` to name what it skipped.

    Attributes:
        kind: ``"comment"`` or ``"preamble"``.
        text: The block's content.
    """

    kind: str
    text: str


class BibTeXFormat(BibFormat):
    """Reads ``.bib`` files, in either the classic or the BibLaTeX dialect."""

    name = "bibtex"
    label = _("BibTeX")

    def _parser(self) -> BibTexParser:
        """Return a parser configured for real-world exports.

        ``interpolate_strings`` expands ``@string`` macros, ``common_strings``
        supplies the month abbreviations exports use bare, and
        ``add_missing_from_crossref`` resolves ``crossref`` inheritance,
        forward references included. ``ignore_nonstandard_types`` is off, so an
        unrecognised entry type maps to a generic document instead of vanishing.

        Returns:
            The parser.
        """
        parser = BibTexParser(
            interpolate_strings=True,
            common_strings=True,
            add_missing_from_crossref=True,
            ignore_nonstandard_types=False,
            homogenize_fields=False,
        )
        # Full month names, which common_strings lacks (see _MONTH_MACROS).
        parser.bib_database.strings.update(_MONTH_MACROS)
        return parser

    def parse(self, file) -> Iterator[dict[str, Any] | _NonRecord]:
        """Yield this file's entries in source order, then its preambles and comments.

        ``bibtexparser`` collects ``@comment`` and ``@preamble`` blocks into
        separate lists, so their source position is lost. They are yielded
        wrapped in :class:`_NonRecord`, and :meth:`to_csl_json` skips them.

        Accepts a binary or a text handle, since a browser upload is always
        bytes. Bytes are decoded as ``utf-8-sig``, so a byte-order mark is
        absorbed, as :class:`~literature.importers.ris.RISParser` does.

        Raises :class:`~literature.importers.exceptions.ParseError` when the
        bytes cannot be decoded, when braces nest deeper than the parser's
        recursion allows, or when the file has content but no ``@`` block.
        ``bibtexparser`` reads anything as comments, so without that last check
        an RIS file given the wrong format would import nothing and report one
        skip. An empty file yields nothing.

        A field repeated within one entry keeps its first occurrence. That is
        ``bibtexparser``'s behaviour, stated here so it can be relied on.
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
        if text.strip() and not _BIBTEX_BLOCK_RE.search(text):
            raise ParseError(
                _("No BibTeX entries found. Is this a BibTeX file?"),
            )
        try:
            database = bibtexparser.loads(text, parser=self._parser())
        except RecursionError:
            raise ParseError(
                _("This file nests braces too deeply to read."),
            ) from None
        yield from database.entries
        yield from (_NonRecord("preamble", text) for text in database.preambles)
        yield from (_NonRecord("comment", text) for text in database.comments)

    def to_csl_json(self, raw: dict[str, Any] | _NonRecord) -> dict[str, Any]:
        """Turn one parsed entry into CSL JSON.

        An entry is mapped in a fixed order: type, fields, names, dates,
        identifiers, then preservation, each value cleaned first. Where a
        classic and a BibLaTeX field target the same CSL variable, the BibLaTeX
        value wins.

        Two things end up in ``custom``. An identifier that cleaning could not
        rescue is kept under its own field name. Every field mapped nowhere is
        gathered under one ``bibtex`` key, so it cannot be mistaken for an
        identifier of the record.

        Args:
            raw: A parsed entry dict, or a :class:`_NonRecord`.

        Returns:
            The entry as CSL JSON.

        Raises:
            SkipEntry: ``raw`` is a comment or a preamble.
        """
        if isinstance(raw, _NonRecord):
            if raw.kind == "preamble":
                raise SkipEntry(
                    _("This is a @preamble block, not a bibliographic record.")
                )
            raise SkipEntry(_("This is a @comment block, not a bibliographic record."))

        result: dict[str, Any] = {
            "type": ENTRY_TYPE_TABLE.get(
                raw.get("ENTRYTYPE", ""), _Mapped(_FALLBACK_TYPE, "classic")
            ).csl,
            "citation-key": raw.get("ID", ""),
        }

        # Classic first, then BibLaTeX, so a BibLaTeX value overwrites its
        # classic counterpart for every pair the table carries.
        consumed: set[str] = set()

        # The field that supplied each CSL variable. Another field naming the
        # same variable is preserved rather than overwritten, and within a
        # dialect the first in table order wins.
        claimed: dict[str, str] = {}

        for dialect in ("classic", "biblatex"):
            for bib_key, mapping in FIELD_TABLE.items():
                if mapping.dialect != dialect:
                    continue
                value = raw.get(bib_key)
                if not value:
                    continue
                if (
                    mapping.csl in claimed
                    and FIELD_TABLE[claimed[mapping.csl]].dialect == dialect
                ):
                    continue
                cleaned = _clean_text(value)
                if mapping.csl == "language":
                    tag = _language_tag(cleaned)
                    if tag is None:
                        continue
                    cleaned = tag
                result[mapping.csl] = cleaned
                consumed.discard(claimed.get(mapping.csl, ""))
                claimed[mapping.csl] = bib_key
                consumed.add(bib_key)

        for bib_key, mapping in NAME_FIELD_TABLE.items():
            value = raw.get(bib_key)
            if value:
                names = _names_to_csl(value)
                if names:
                    result[mapping.csl] = names
                    consumed.add(bib_key)

        issued, date_fields = _issued_date(raw)
        if issued:
            result["issued"] = issued
            consumed.update(date_fields)

        # An unresolvable urldate takes the literal slot, as an unresolvable
        # issued date does, rather than generic preservation.
        urldate = raw.get("urldate", "").strip()
        if urldate:
            result["accessed"] = _parse_biblatex_date(urldate) or {"literal": urldate}
            consumed.add("urldate")

        for bib_key, mapping in IDENTIFIER_FIELD_TABLE.items():
            value = raw.get(bib_key)
            if not value:
                continue
            cleaned = _clean_identifier(bib_key, value)
            consumed.add(bib_key)
            try:
                validate_identifier(mapping.csl, cleaned)
            except ValidationError:
                # Kept under its own field name rather than failing the entry.
                result.setdefault("custom", {})[bib_key] = cleaned
            else:
                result[mapping.csl] = cleaned

        unmapped = _unmapped_fields(raw, consumed)
        if unmapped:
            result.setdefault("custom", {})["bibtex"] = unmapped

        return result

    def handle_for(self, raw: dict[str, Any] | _NonRecord) -> str | None:
        """Return the cite key, which is what a reader will search for.

        Args:
            raw: A parsed entry dict, or a :class:`_NonRecord`.

        Returns:
            The cite key, or ``None`` for a comment or preamble.
        """
        if not isinstance(raw, dict):
            return None
        return raw.get("ID") or None

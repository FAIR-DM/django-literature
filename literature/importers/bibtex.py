"""Reading BibTeX files into the catalogue.

The first concrete format behind the import contract (spec 003). It supplies
only the two stages a format owns, :meth:`~BibTeXFormat.parse` and
:meth:`~BibTeXFormat.to_csl_json`, plus :meth:`~BibTeXFormat.handle_for`;
the workflow, atomicity, per-entry reporting and dry runs all come from
:class:`~literature.importers.base.BibFormat` unchanged.

One format reads both dialects. Classic BibTeX is what publisher export links
and academic databases emit; BibLaTeX is what current Zotero and JabRef write
by default. They share a file syntax and disagree on field names and entry
types, and someone exporting a library has no way to know which they were
given, so asking them would be the adoption barrier this feature exists to
remove (spec 004, D2). Both tables carry both dialects, each entry annotated
with the one it belongs to.

Where a BibLaTeX field and its classic counterpart both name the same CSL
variable — ``date`` over ``year``/``month``, ``journaltitle`` over
``journal`` — and an entry supplies both with disagreeing values, the
BibLaTeX field wins (FR-024, decisions.md D17). BibLaTeX's own manual treats
the classic field as the legacy one its BibLaTeX equivalent replaces, and
``date`` states a precision ``year``/``month`` cannot, so the more expressive
field is also the more current one.

``bibtexparser`` is imported here and nowhere else in the package. That is
deliberate and asserted by a test: the parser is an implementation detail of
this class, which is what makes it replaceable (research.md).
"""

import calendar
import dataclasses
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
from literature.importers.exceptions import SkipEntry
from literature.validators import validate_identifier

# ---------------------------------------------------------------------------
# Mapping tables — data, not code (plan.md "Design in brief"). Each entry
# is annotated with the dialect it belongs to, so US3 can extend these in
# place rather than maintaining a parallel table.
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Mapped:
    """One table entry: the CSL name a source key maps to, and its dialect."""

    csl: str
    dialect: str  # "classic" (this story) | "biblatex" (US3, issue #32)


#: BibTeX entry type -> CSL item type (FR-006). A type not listed here maps
#: to the generic ``document`` type rather than failing the entry. The
#: BibLaTeX-only entries are drawn from the type list its own manual
#: documents (`3.1 Entry Types`), minus ``set`` (a grouping construct, not a
#: bibliographic record of its own) and ``xdata`` (data-only, never a real
#: entry either) — neither would mean anything mapped to a CSL type, and
#: they are the two this table is expected never to carry. Where Zotero's
#: own type map (``tests/data/csl-typeMap.xml``) states an equivalent, it is
#: followed rather than second-guessed: that is where ``artwork``,
#: ``dataset`` and ``patent`` come from (D18).
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

#: An entry type with no CSL equivalent lands here rather than failing the
#: entry (FR-006, acceptance scenario 3).
_FALLBACK_TYPE = "document"

#: Scalar BibTeX field -> CSL variable (FR-007). Name fields, date fields
#: and identifier fields are mapped separately (later stories in this
#: file's history); ``key`` (BibTeX's sorting hint) and ``crossref``
#: (consumed for inheritance, not copied) have no entry here and are simply
#: not carried directly into CSL JSON — both, like every other field with no
#: entry in any of this module's tables, are preserved instead under
#: ``custom["bibtex"]`` (US4, FR-025, :func:`_unmapped_fields`).
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

#: BibTeX identifier field -> top-level CSL identifier key (FR-011).
IDENTIFIER_FIELD_TABLE: dict[str, _Mapped] = {
    "doi": _Mapped("DOI", "classic"),
    "isbn": _Mapped("ISBN", "classic"),
    "issn": _Mapped("ISSN", "classic"),
    "url": _Mapped("URL", "classic"),
}

#: BibTeX name-list field -> CSL name-variable role (FR-008).
NAME_FIELD_TABLE: dict[str, _Mapped] = {
    "author": _Mapped("author", "classic"),
    "editor": _Mapped("editor", "classic"),
}

#: Month names, both the three-letter abbreviation ``common_strings`` already
#: supplies and the full spelling real exports write bare (``month = July``).
#: Crossref's own classic BibTeX export is the case this table exists for:
#: ``common_strings`` defines ``jul`` but not ``july``, so a bare ``July``
#: macro reference is otherwise undefined and aborts the whole file's parse.
#: This is macro *resolution* (FR-013's territory, the same thing
#: ``common_strings`` already does for abbreviations), not a value cleanup —
#: no field's already-parsed content is altered.
_MONTH_MACROS: dict[str, str] = {calendar.month_name[i].lower(): calendar.month_name[i] for i in range(1, 13)}

#: Month name or abbreviation (case-insensitive) -> its 1-based number, for
#: building date-parts (FR-010). Covers both the abbreviation
#: ``common_strings`` expands to and the full name ``_MONTH_MACROS`` expands
#: to, plus the abbreviation itself for a value written in braces or quotes,
#: which never goes through macro expansion at all.
_MONTH_NUMBERS: dict[str, int] = {calendar.month_abbr[i].lower(): i for i in range(1, 13)} | {
    calendar.month_name[i].lower(): i for i in range(1, 13)
}


def _month_number(raw: str) -> int | None:
    """The 1-based month number a source's ``month`` value states, if any."""
    text = raw.strip()
    if text.isdigit():
        value = int(text)
        return value if 1 <= value <= 12 else None
    return _MONTH_NUMBERS.get(text.lower())


# ---------------------------------------------------------------------------
# Cleaning (FR-017, FR-018, FR-019, FR-029) — recovery before rejection
# (spec 004, D1). A value in a form the catalogue would reject is normalized
# where its meaning is recoverable; nothing here evaluates its input, since a
# ``.bib`` file is untrusted content (Article V).
# ---------------------------------------------------------------------------


#: The five entities XML predefines, plus a decimal or hexadecimal character
#: reference. Deliberately not :func:`html.unescape`, which also resolves the
#: ~2000 HTML5 named references and does so without requiring the closing
#: semicolon: that would rewrite ordinary bibliographic prose, turning a
#: title containing ``&not`` or ``&sect`` into ``¬`` or ``§``. What real
#: exports actually emit is XML escaping — Crossref's own BibTeX export
#: writes ``Knowledge Discovery &amp; Data Mining`` — so this recognises
#: exactly that and leaves every other ampersand alone.
_ENTITY_RE = re.compile(r"&(?:(amp|lt|gt|quot|apos)|#(\d{1,7})|#[xX]([0-9a-fA-F]{1,6}));")

_NAMED_ENTITIES = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}


def _unescape_entities(value: str) -> str:
    """Resolve XML character escaping a source wrote into a field's text.

    Applied after the LaTeX decode, so a value written ``\\&amp;`` — escaped
    once for LaTeX and once for XML — resolves through both layers.
    """

    def replace(match: re.Match[str]) -> str:
        name, decimal, hexadecimal = match.groups()
        if name:
            return _NAMED_ENTITIES[name]
        code = int(decimal) if decimal else int(hexadecimal, 16)
        return chr(code) if 0 < code <= 0x10FFFF else match.group(0)

    return _ENTITY_RE.sub(replace, value)


def _clean_text(value: str) -> str:
    """Decode LaTeX escapes to the characters they represent (FR-018).

    ``bibtexparser.latexenc.latex_to_unicode`` also strips braces once it has
    finished decoding, which is what removes capitalization-protecting braces
    (``{DNA}`` -> ``DNA``) without a separate step. A construct it does not
    recognise is left in the string rather than raising or dropping anything
    — pure string substitution, so it never evaluates its input.

    XML character escaping is resolved afterwards (:func:`_unescape_entities`).
    A ``.bib`` file is not XML, but real exports carry escaping from the
    pipeline upstream of them, and a title reading ``Knowledge Discovery
    &amp; Data Mining`` in the catalogue is the same shape of defect as an
    undecoded ``Kr{\\"u}ger``: recoverable, so recovered (D1).
    """
    return _unescape_entities(str(latex_to_unicode(value)))


#: A DOI written with its resolver URL prefix (FR-017's named case).
_DOI_URL_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)

#: A DOI carrying a plain ``doi:`` label rather than a bare identifier.
_DOI_LABEL_RE = re.compile(r"^doi:\s*", re.IGNORECASE)


def _normalize_doi(value: str) -> str:
    """Strip a resolver URL prefix or a ``doi:`` label, leaving the bare DOI.

    A value carrying neither is returned unchanged — normalization only
    removes what it recognises, and cleaning that cannot recover a value
    leaves it for preservation rather than guessing at it (D1).
    """
    text = _DOI_URL_RE.sub("", value.strip())
    return _DOI_LABEL_RE.sub("", text).strip()


#: An ISBN carrying a redundant ``isbn:`` / ``isbn-13:`` label, the same
#: shape of malformation the DOI case is named for (FR-017), applied to the
#: other identifier field T023 names by field.
_ISBN_LABEL_RE = re.compile(r"^isbn(?:-1[03])?:?\s*", re.IGNORECASE)


def _normalize_isbn(value: str) -> str:
    """Strip a redundant ``isbn:`` label. Hyphens and spaces are the
    validator's own job (``validate_isbn`` strips them before checking).
    """
    return _ISBN_LABEL_RE.sub("", value.strip()).strip()


#: Field-specific normalization beyond the generic LaTeX decode (T023).
_IDENTIFIER_NORMALIZERS: dict[str, Any] = {
    "doi": _normalize_doi,
    "isbn": _normalize_isbn,
}


def _clean_identifier(bib_key: str, value: str) -> str:
    """Normalize one identifier field's value ahead of validation."""
    cleaned = _clean_text(value).strip()
    normalizer = _IDENTIFIER_NORMALIZERS.get(bib_key)
    if normalizer is not None:
        cleaned = normalizer(cleaned)
    return cleaned


# ---------------------------------------------------------------------------
# Names (FR-008, FR-009)
# ---------------------------------------------------------------------------


def _is_wrapped_literal(name: str) -> bool:
    """Whether ``name`` is a single name string entirely wrapped in one brace pair.

    ``author = {{World Wide Web Consortium}}`` leaves one brace level on the
    field value once the outer pair (the field's own value delimiter) is
    stripped by the parser — ``{World Wide Web Consortium}``. That remaining
    pair is BibTeX's convention for "do not split this name", used for
    institutions and other unparsed names (FR-009, acceptance scenario 5).
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
    """Split a BibTeX name list on ``and``, ignoring one braced inside a name.

    BibTeX separates a name list with the literal word ``and``. A name may
    itself contain braced text, so the split has to track brace depth rather
    than being a plain ``str.split`` — otherwise a literal name that happened
    to contain the word would be cut in two. None of this story's names do,
    but the corpus is not the full space of real exports.
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
    """One name string to a CSL name-variable object.

    A brace-wrapped literal goes to ``literal`` unsplit (FR-009), decoded but
    not split. Otherwise the whole name is LaTeX-decoded (FR-018) before
    ``splitname`` breaks it into First/von/Last/Jr, which map directly onto
    CSL's ``given``, ``non-dropping-particle``, ``family`` and ``suffix``
    (FR-008). Non-strict mode: a name this story cannot parse cleanly should
    not abort the entry over a name, which is the contract's own per-entry
    robustness (base.py), not a cleaning transform on the name's content.

    Decoding runs after :func:`_is_wrapped_literal`'s check, not before —
    that check looks for one surviving brace pair once the parser has
    stripped the field's own outer delimiter, and ``_clean_text`` would
    already have removed it, along with every other brace in the name.
    """
    stripped = name.strip()
    if not stripped:
        return {}
    if _is_wrapped_literal(stripped):
        # A pair of braces with nothing in them names nobody. Returning it as
        # a literal would put a contributor row carrying no name on the record
        # (D22); returning nothing leaves the source field unconsumed, so it
        # is preserved instead (FR-025).
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
    """A whole BibTeX name-list field to a CSL name-variable array, in order."""
    return [parsed for parsed in (_name_to_csl(one) for one in _split_name_list(raw)) if parsed]


# ---------------------------------------------------------------------------
# Dates (FR-010)
# ---------------------------------------------------------------------------

#: BibLaTeX's single ``date`` field: a year, a year and month, or a full
#: date, each truncated ISO 8601 (US3 acceptance scenario 2). BibLaTeX also
#: allows an open or closed range (``1970/``, ``1970/1975``) and a season
#: qualifier; neither is a precision this table's three CSL shapes cover, so
#: a value in one of those forms does not match and falls to the ``literal``
#: fallback below, the same as any other date the source states that this
#: importer cannot resolve to a structured one (FR-020).
_BIBLATEX_DATE_RE = re.compile(r"^(?P<year>\d{4})(-(?P<month>\d{2})(-(?P<day>\d{2}))?)?$")


def _parse_biblatex_date(value: str) -> dict[str, Any] | None:
    """The CSL date-parts a BibLaTeX ``date`` value states, at its own precision.

    ``None`` for a value that is not one of the three shapes ``date`` is
    documented to carry — the caller's job, not this function's, to decide
    what happens to a date it cannot parse.
    """
    match = _BIBLATEX_DATE_RE.match(value.strip())
    if not match:
        return None
    parts = [int(match["year"])]
    if match["month"]:
        parts.append(int(match["month"]))
        if match["day"]:
            parts.append(int(match["day"]))
    return {"date-parts": [parts]}


def _issued_date(fields: dict[str, str]) -> dict[str, Any] | None:
    """The entry's ``issued`` date, at the precision the source states.

    BibLaTeX's ``date`` is checked first and, when present, decides the
    result on its own — including when a classic ``year``/``month`` pair is
    also present and disagrees, which is the precedence FR-024 requires and
    D17 documents. A ``date`` that will not parse still wins, going to CSL's
    ``literal`` fallback rather than falling through to ``year``: the source
    stated a date, and preservation over discarding, not preferring a
    different field, is the answer to a value this importer cannot resolve
    (FR-020).

    Without a ``date`` field, a classic ``year`` alone gives year precision;
    ``year`` with a recognised ``month`` gives month precision. Neither pads
    a component the source did not state (FR-010) — there is no day field in
    classic BibTeX to make a full date from. A ``year`` that cannot be
    resolved to a structured date at all (``in press``, a prose range) is not
    discarded either — it goes to the same ``literal`` fallback, which is
    ``ItemDate.literal`` on the far side of ``from_csl_json`` (D13:
    unparseable dates are not the general preservation US4 owns, since
    ``ItemDate`` already has a slot for them).
    """
    date = fields.get("date", "").strip()
    if date:
        return _parse_biblatex_date(date) or {"literal": date}

    year = fields.get("year", "").strip()
    if not year:
        return None
    if not year.isdigit():
        return {"literal": year}
    parts = [int(year)]
    month = fields.get("month", "")
    if month:
        month_number = _month_number(month)
        if month_number is not None:
            parts.append(month_number)
    return {"date-parts": [parts]}


#: The language names ``babel`` and ``polyglossia`` define, which is what a
#: BibLaTeX ``langid`` states, mapped to the BCP 47 tag CSL's ``language``
#: variable expects. Only the unambiguous ones: ``langid = {english}`` says
#: nothing about which English, so it is ``en`` rather than a guess between
#: ``en-GB`` and ``en-US``, while ``british`` and ``american`` do say.
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
    """The BCP 47 tag ``value`` states, or ``None`` if it states none.

    ``None`` rather than the raw string, because the catalogue's ``language``
    holds a tag and nothing longer than one. A name this table does not carry
    is not truncated to fit and does not fail the entry: it goes unconsumed,
    which sends it to preservation with everything else (D1, FR-025).
    """
    text = value.strip()
    tag = _LANGUAGE_TAGS.get(text.casefold())
    if tag:
        return tag
    return text if _LANGUAGE_TAG_RE.match(text) and len(text) <= 10 else None


# ---------------------------------------------------------------------------
# Preservation (FR-025, FR-026, D3, D20) — a field this importer maps to no
# CSL variable is not discarded, and preserving it must not open a second
# reporting channel: per-entry reporting stays exactly what the import
# contract already defines (D3, spec 004 US4).
# ---------------------------------------------------------------------------

#: The two keys ``bibtexparser`` adds to every entry structurally — already
#: surfaced as ``type`` and ``citation-key`` — rather than fields the source
#: file itself wrote.
_STRUCTURAL_KEYS = frozenset({"ENTRYTYPE", "ID"})

#: The three fields :func:`_issued_date` reads (FR-010, FR-024). Consumed
#: together, since ``issued`` is built from whichever of them an entry
#: carries and the ones it does not carry are absent anyway.
_DATE_SOURCE_FIELDS = frozenset({"year", "month", "date"})


def _unmapped_fields(raw: dict[str, Any], consumed: set[str]) -> dict[str, str]:
    """Every field ``raw`` carries that conversion did not put anywhere.

    ``consumed`` is what :meth:`BibTeXFormat.to_csl_json` actually used, not
    what the mapping tables promise it might. The difference matters: a field
    a table recognises can still land nowhere — a ``language`` this importer
    cannot resolve to a language tag, an ``author`` list that parses to no
    names, a ``month`` with no ``year`` to date. Deciding preservation from
    the tables would call all three mapped and drop them; deciding it from
    what happened preserves them, which is what FR-025 asks for.

    So a key survives here unless conversion consumed it, it is one of the
    two structural keys the parser itself adds (already surfaced as ``type``
    and ``citation-key``), or the parser prefixes it with an underscore as
    its own bookkeeping. That last is why ``_FROM_CROSSREF`` — its record of
    which fields it copied, not something the source file wrote — does not
    leak into the preserved bookkeeping.

    ``crossref`` is preserved by the ordinary rule. Inheritance copies the
    parent's fields onto the child (FR-015), but the ``crossref`` key itself
    names no CSL variable whether or not it resolved, so nothing consumes it
    either way and there is no branch for the unresolvable case (acceptance
    scenario 3). An empty value is not preserved: there is no content to
    keep, and ``{}`` is what a reference manager writes for a field it holds
    no value for.
    """
    return {
        key: value
        for key, value in raw.items()
        if key not in _STRUCTURAL_KEYS and key not in consumed and not key.startswith("_") and value
    }


# ---------------------------------------------------------------------------
# Published mapping (FR-007) — the documentation of what maps to what is
# rendered from the tables above rather than written alongside them, so the
# two cannot disagree. ``docs/bibtex-mapping.md`` is ``_mapping_document``'s output
# and a test asserts it still is.
# ---------------------------------------------------------------------------


def _mapping_document() -> str:
    """The field and entry-type mapping, as a Markdown document.

    Private on purpose. The import contract's public surface is a curated,
    two-way-asserted list (``literature.importers.__all__``), and a
    documentation generator does not belong in it. Regenerate the published
    page after changing any table above::

        poetry run python -c "from literature.importers.bibtex import _mapping_document; \
            open('docs/bibtex-mapping.md','w').write(_mapping_document())"

    A test asserts the file on disk still matches, so a table change that
    skips this step fails rather than shipping a stale page.
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
    lines += [f"| `@{key}` | `{m.csl}` | {m.dialect} |" for key, m in sorted(ENTRY_TYPE_TABLE.items())]
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
    lines += [f"| `{key}` | `{m.csl}` | {m.dialect} |" for key, m in sorted(fields.items())]
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


class BibTeXFormat(BibFormat):
    """Reads ``.bib`` files, in either the classic or the BibLaTeX dialect."""

    name = "bibtex"
    label = _("BibTeX")

    def _parser(self) -> BibTexParser:
        """The configured parser.

        ``interpolate_strings`` expands ``@string`` macros in the entries that
        reference them (FR-013), ``common_strings`` supplies the month
        abbreviations that real exports use bare, and
        ``add_missing_from_crossref`` resolves ``crossref`` inheritance
        (FR-015) — including the forward references classic BibTeX requires,
        since it runs over the whole database once parsing is done.

        ``ignore_nonstandard_types`` is off: an unrecognised entry type maps to
        a generic document rather than vanishing (FR-006), and a dropped entry
        would be a silent loss of exactly the kind this feature exists to stop.
        """
        parser = BibTexParser(
            interpolate_strings=True,
            common_strings=True,
            add_missing_from_crossref=True,
            ignore_nonstandard_types=False,
            homogenize_fields=False,
        )
        # See _MONTH_MACROS: without this, a bare full month name that is not
        # also a three-letter abbreviation (``July``, unlike ``May``) is an
        # undefined macro reference and aborts parsing the whole file.
        parser.bib_database.strings.update(_MONTH_MACROS)
        return parser

    def parse(self, file) -> Iterator[dict[str, Any] | str]:
        """Yield this file's entries, then its comments and preambles.

        ``@comment`` and ``@preamble`` blocks are not bibliographic records
        (FR-014), and ``bibtexparser`` collects them into their own lists
        rather than interleaving them with entries, so there is no source
        position to recover them at. They are yielded as plain strings,
        which :meth:`to_csl_json` uses to tell them apart from an entry
        (always a ``dict``) and skip. Entries themselves keep their source
        order, which is what FR-004 is asserted against.
        """
        database = bibtexparser.load(file, parser=self._parser())
        yield from database.entries
        yield from database.preambles
        yield from database.comments

    def to_csl_json(self, raw: dict[str, Any] | str) -> dict[str, Any]:
        """Turn one parsed entry into CSL JSON.

        Comments and preambles arrive as plain strings (see :meth:`parse`)
        and are skipped outright (FR-014). Everything else is a classic or
        BibLaTeX entry dict, mapped in the fixed order plan.md lays out:
        type, fields, names, dates, identifiers, preservation, each cleaned
        ahead of mapping (FR-017, FR-018, D1). Where a dialect pair targets
        the same CSL variable and disagree, the BibLaTeX value wins
        (FR-024, D17).

        Two things end up in ``custom``, and they are not the same
        mechanism. An identifier cleaning could not rescue is written under
        its own source field name, one field at a time, at the point its
        own validation fails (FR-019, D13) — the narrow case. Every field
        this importer maps nowhere at all is swept up afterwards, nested
        under a single ``bibtex`` key rather than spilled flat, so it
        cannot be mistaken for an identifier of the catalogue record itself
        (FR-025, FR-026, D3, D20, :func:`_unmapped_fields`) — the general
        case.
        """
        if not isinstance(raw, dict):
            raise SkipEntry

        result: dict[str, Any] = {
            "type": ENTRY_TYPE_TABLE.get(raw.get("ENTRYTYPE", ""), _Mapped(_FALLBACK_TYPE, "classic")).csl,
            "citation-key": raw.get("ID", ""),
        }

        # Classic fields first, then BibLaTeX: where a dialect pair targets
        # the same CSL variable (``journal``/``journaltitle``) and an entry
        # carries both, the second pass's assignment overwrites the first's,
        # so the BibLaTeX value is what survives (FR-024, D17). Two passes
        # over the table rather than one sorted by dialect, so the rule
        # holds for every present and future pair FIELD_TABLE carries, not
        # just the one case a single insertion-order trick would happen to
        # get right.
        consumed: set[str] = set()

        for dialect in ("classic", "biblatex"):
            for bib_key, mapping in FIELD_TABLE.items():
                if mapping.dialect != dialect:
                    continue
                value = raw.get(bib_key)
                if not value:
                    continue
                cleaned = _clean_text(value)
                if mapping.csl == "language":
                    tag = _language_tag(cleaned)
                    if tag is None:
                        continue
                    cleaned = tag
                result[mapping.csl] = cleaned
                consumed.add(bib_key)

        for bib_key, mapping in NAME_FIELD_TABLE.items():
            value = raw.get(bib_key)
            if value:
                names = _names_to_csl(value)
                if names:
                    result[mapping.csl] = names
                    consumed.add(bib_key)

        issued = _issued_date(raw)
        if issued:
            result["issued"] = issued
            consumed.update(_DATE_SOURCE_FIELDS)

        accessed = _parse_biblatex_date(raw.get("urldate", "").strip())
        if accessed:
            result["accessed"] = accessed
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
                # Cleaning could not turn this into something the catalogue
                # accepts. Preserved under its own source field name rather
                # than failing the entry (FR-019, D13) — the narrow,
                # one-field-at-a-time case; the general sweep over every
                # unmapped field is US4.
                result.setdefault("custom", {})[bib_key] = cleaned
            else:
                result[mapping.csl] = cleaned

        unmapped = _unmapped_fields(raw, consumed)
        if unmapped:
            result.setdefault("custom", {})["bibtex"] = unmapped

        return result

    def handle_for(self, raw: dict[str, Any] | str) -> str | None:
        """The cite key, which is what a reader will search for (FR-012).

        ``None`` for a comment or preamble (see :meth:`parse`), which has no
        cite key to report.
        """
        if not isinstance(raw, dict):
            return None
        return raw.get("ID") or None

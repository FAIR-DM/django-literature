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
remove (spec 004, D2). This module currently maps the classic dialect only;
US3 (issue #32) extends both tables to BibLaTeX.

``bibtexparser`` is imported here and nowhere else in the package. That is
deliberate and asserted by a test: the parser is an implementation detail of
this class, which is what makes it replaceable (research.md).
"""

import dataclasses
from collections.abc import Iterator
from typing import Any

import bibtexparser
from bibtexparser.bparser import BibTexParser
from django.utils.translation import gettext_lazy as _

from literature.importers.base import BibFormat

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
#: to the generic ``document`` type rather than failing the entry.
ENTRY_TYPE_TABLE: dict[str, _Mapped] = {
    "article": _Mapped("article-journal", "classic"),
    "book": _Mapped("book", "classic"),
    "booklet": _Mapped("pamphlet", "classic"),
    "conference": _Mapped("paper-conference", "classic"),
    "inbook": _Mapped("chapter", "classic"),
    "incollection": _Mapped("chapter", "classic"),
    "inproceedings": _Mapped("paper-conference", "classic"),
    "manual": _Mapped("book", "classic"),
    "mastersthesis": _Mapped("thesis", "classic"),
    "misc": _Mapped("document", "classic"),
    "phdthesis": _Mapped("thesis", "classic"),
    "proceedings": _Mapped("book", "classic"),
    "techreport": _Mapped("report", "classic"),
    "unpublished": _Mapped("manuscript", "classic"),
}

#: An entry type with no CSL equivalent lands here rather than failing the
#: entry (FR-006, acceptance scenario 3).
_FALLBACK_TYPE = "document"

#: Scalar BibTeX field -> CSL variable (FR-007). Name fields, date fields
#: and identifier fields are mapped separately (later stories in this
#: file's history); ``key`` (BibTeX's sorting hint) and ``crossref``
#: (consumed for inheritance, not copied) have no entry here and are simply
#: not carried into CSL JSON by this story — preservation of unmapped
#: fields is US4 (issue #33).
FIELD_TABLE: dict[str, _Mapped] = {
    "address": _Mapped("publisher-place", "classic"),
    "annote": _Mapped("annote", "classic"),
    "booktitle": _Mapped("container-title", "classic"),
    "chapter": _Mapped("chapter-number", "classic"),
    "edition": _Mapped("edition", "classic"),
    "howpublished": _Mapped("medium", "classic"),
    "institution": _Mapped("publisher", "classic"),
    "journal": _Mapped("container-title", "classic"),
    "note": _Mapped("note", "classic"),
    "number": _Mapped("issue", "classic"),
    "organization": _Mapped("publisher", "classic"),
    "pages": _Mapped("page", "classic"),
    "publisher": _Mapped("publisher", "classic"),
    "school": _Mapped("publisher", "classic"),
    "series": _Mapped("collection-title", "classic"),
    "title": _Mapped("title", "classic"),
    "type": _Mapped("genre", "classic"),
    "volume": _Mapped("volume", "classic"),
}


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
        return BibTexParser(
            interpolate_strings=True,
            common_strings=True,
            add_missing_from_crossref=True,
            ignore_nonstandard_types=False,
            homogenize_fields=False,
        )

    def parse(self, file) -> Iterator[dict[str, Any]]:
        """Yield this file's entries in source order."""
        database = bibtexparser.load(file, parser=self._parser())
        yield from database.entries

    def to_csl_json(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Turn one parsed entry into CSL JSON.

        Mapped in the fixed order plan.md lays out: type, then fields. Names,
        dates, identifiers, cleaning and preservation are later stories in
        this file's history; a field this story does not recognise is simply
        not carried into the result yet.
        """
        result: dict[str, Any] = {
            "type": ENTRY_TYPE_TABLE.get(raw.get("ENTRYTYPE", ""), _Mapped(_FALLBACK_TYPE, "classic")).csl,
            "citation-key": raw.get("ID", ""),
        }

        for bib_key, mapping in FIELD_TABLE.items():
            value = raw.get(bib_key)
            if value:
                result[mapping.csl] = value

        return result

    def handle_for(self, raw: dict[str, Any]) -> str | None:
        """The cite key, which is what a reader will search for (FR-012)."""
        return raw.get("ID") or None

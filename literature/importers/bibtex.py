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
remove (spec 004, D2).

``bibtexparser`` is imported here and nowhere else in the package. That is
deliberate and asserted by a test: the parser is an implementation detail of
this class, which is what makes it replaceable (research.md).
"""

from collections.abc import Iterator
from typing import Any

import bibtexparser
from bibtexparser.bparser import BibTexParser
from django.utils.translation import gettext_lazy as _

from literature.importers.base import BibFormat


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

        Only the type and the citation key so far; the mapping, cleaning,
        dialect and preservation stages land with their stories.
        """
        return {
            "type": "document",
            "citation-key": raw.get("ID", ""),
        }

    def handle_for(self, raw: dict[str, Any]) -> str | None:
        """The cite key, which is what a reader will search for (FR-012)."""
        return raw.get("ID") or None

# BibTeX corpus

Test files for the BibTeX importer. Acceptance is judged against this directory, so the result is
reproducible and no test reaches the network.

## Constructed fixtures

Every file except the two below is written by hand to isolate one malformation, so a failing test
points at the rule it broke rather than at a file with several problems in it. The names say which:
`doi_as_url.bib`, `crossref_cycle.bib`, `latin1_encoded.bib`, and so on. `clean_multi_type.bib` is
the control, covering several entry types with nothing wrong.

`latin1_encoded.bib` is deliberately not UTF-8. Do not re-save it.

`bulk_500_entries.bib` holds 500 generated entries, and exists so that materialising a whole file's
converted content would be visible rather than theoretical. It tests volume, not correctness.

## Real exports

`real_crossref_classic.bib` is genuine. It was fetched once from Crossref by content negotiation
against six well-known DOIs, and it is what an academic database actually emits. It is worth keeping
because it carries things nobody would think to construct:

- Field names in uppercase (`ISSN`, `DOI`), which BibTeX treats case-insensitively.
- Bare month macros (`month=July`) rather than braced values.
- HTML entities in titles (`&amp;`).
- Real Unicode en-dashes in page ranges rather than the `--` a person would type.

`constructed_biblatex.bib` is **not** a genuine export. It is written to follow the conventions
Zotero's and JabRef's BibLaTeX exporters use, `journaltitle` over `journal`, a single `date` field,
and the `@online`, `@thesis`, `@report` and `@collection` entry types. A real export from one of
those tools would be better, for the same reason the Crossref file is: it would carry the quirks
nobody thought to write down. Replacing it is worth doing if one becomes available.

Both files hold bibliographic metadata only, which is factual, and nothing personal.

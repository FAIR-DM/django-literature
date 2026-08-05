# Negative RIS corpus

Files that are not RIS at all, named `.ris` anyway — the mirror of the failure the BibTeX format
found in its own parser (spec.md Edge Cases: "A file that is not RIS at all").

## `wos_native_tagged.ris`

Web of Science's *native* tagged export format — not RIS, despite using two-letter tags of its
own (`FN`, `VR`, `PT`, `AU`, `TI`, …) and coming from the same producer RIS's Web of Science
support targets. It carries no `-` after its tags, so nothing in it matches the RIS line grammar.

Source: `rispy`'s own `tests/data/example_wos.ris` (<https://github.com/mrtidyup/rispy>, MIT
licence, retrieved 2026-08-05) — research.md R10 names this exact file as "the natural test for
the 'a file that is not RIS' edge case."

## `bibtex_under_ris_name.ris`

A BibTeX entry — copied from this repo's own `tests/fixtures/bibtex/clean_multi_type.bib`, whose
content is already this project's — saved under a `.ris` name. Its lines use `=` for field
assignment, never `TAG  - value`, so nothing in it matches the RIS line grammar either.

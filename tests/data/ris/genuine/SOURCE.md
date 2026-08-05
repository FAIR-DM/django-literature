# Genuine RIS corpus

Test files for the RIS format. Acceptance is judged against this directory, so the result is
reproducible and no test reaches the network (spec.md "Verification corpus").

All three files below are the same ten bibliographic references, exported through three different
producers, published by **`asreview/citation-file-formatting`**
(<https://github.com/asreview/citation-file-formatting>) under **CC0-1.0** — public domain,
freely vendorable. Retrieved 2026-08-05 (research.md R10). A file the producer or a third party
publishes counts as genuine; a file this project constructs does not (spec.md FR-030, D8).

None of the three is byte-identical to what its export tool wrote today — producers change their
export format over time — but each is what its named producer actually emitted, which is what
"genuine" means here. The repo's own formatting hooks additionally trimmed trailing whitespace
(a trailing space after `ER  -`'s empty value) and a final blank line on vendoring; neither
touches a tag or a value, so nothing evidenced by these files changed.

## `endnote.ris`

Source: `_baseline_endnote.ris`. EndNote is the primary support target (spec.md D7).

Fingerprint (research.md R10): tags within an entry in alphabetical order, unindented
multi-value continuation lines (`KW`, `SN`), a trailing `ID` tag, no byte-order mark.

## `scopus.ris`

Source: `_baseline_scopus.ris`.

Fingerprint: `DB  - Scopus`, `N1  - Export Date:`, a `scopus.com/inward/record.uri` URL,
`SN  - NNNNNNNN (ISSN)` annotated inline, `C7` (article number), a byte-order mark.

## `webofscience.ris`

Source: `_baseline_webofscience.ris`.

Fingerprint: `AN  - WOS:…`, `WE  - Science Citation Index Expanded`, `J9`/`JI`, no `UR` and no
`DB`, a byte-order mark.

## Limitation

Every record in the EndNote baseline is `TY - JOUR`, so it evidences nothing about the
chapter-editor question (research.md R10, R4). The same is true of all twenty-five baselines in the
upstream corpus, and the two corpora that do publish genuine chapter records are GPL-3.0, which this
MIT-licensed package cannot redistribute. That case therefore rests on
`../constructed/chapter_with_editors.ris` instead, and spec.md's *Verification corpus* section
records the substitution (T002, decisions.md D28).

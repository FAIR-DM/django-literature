# Research — 005 Import References from RIS Files

Conducted 2026-08-05, at S3, against live sources. Every library behaviour below was verified by
running the library, not read off its documentation. Every producer behaviour was verified against a
genuine export file, not inferred from a specification.

## R1 — Parser: hand-rolled, no new runtime dependency

**Decision: write the parser in `literature/importers/ris.py`. Do not add `rispy`.**

`rispy` (MIT, 0.10.0, May 2025) is the only maintained general-purpose Python RIS parser. `gris` is
GPL-2.0-or-later, which is incompatible with shipping inside an MIT package, and its only entry point
opens a path itself, which the import contract forbids. `RISparser` is `rispy` under its old name and
is dead.

`rispy` was installed and exercised. It fails four of this feature's requirements outright, and the
failures are not configuration:

| Requirement | `rispy` 0.10.0 behaviour |
|---|---|
| FR-006 — recover the final entry when the closing `ER` is missing | **Silently drops it.** Records are appended only on `ER`. |
| FR-008 — report material before the first entry as skipped | Discards it, reports nothing. |
| FR-009 — fail a tag block carrying no reference type, with a reason | Discards it, reports nothing. |
| FR-018 — store the first repeated value and preserve the rest | Default `enforce_list_tags=True` discards the rest. |
| Edge case — a file carrying a byte-order mark imports normally | **Returns zero records.** BOM handling was deliberately reverted in PR #64. |

Two further findings weigh against it. Its `ParseError` class is exported but never raised anywhere
in 0.10.0, so a file that is not RIS returns `[]` with no error — the opposite of FR-014's "reported
through the result rather than raised". And a stray continuation line after an entry boundary raises
an uncaught `KeyError`, which is not in its issue tracker.

The deeper reason is that `rispy`'s recovery strategy is to resynchronise to the next `TY` and say
nothing, where this feature's entire reporting contract is to say what happened to every entry.
Satisfying the requirements means replacing its `parse_lines`, which is the whole parser and is not a
documented override point. Preserving raw tags (FR-024) additionally means passing an identity
mapping, which discards `TAG_KEY_MAPPING` — the one asset left.

Against Article VII, no justification for the dependency survives contact with the requirements.
Against Article III, `rispy`'s friendly field names would become a third naming layer between RIS
tags and CSL variables that nothing else in the package speaks.

RIS is a line-oriented format: a tag line, a continuation rule, and `ER`. A prototype generator of
about 45 lines passed every case above that `rispy` fails, while yielding one entry at a time — a
genuine FR-004 win the library cannot provide, since all of `rispy`'s entry points materialise a
list.

**Departing from the BibTeX format's precedent of using a library is deliberate and is recorded in
`decisions.md` (D11).** Data, not code, is lifted: `rispy`'s `TAG_KEY_MAPPING` and
`TYPE_OF_REFERENCE_MAPPING` are MIT-licensed and serve as a census of tags and reference types.

**Encoding:** the file is decoded `utf-8-sig` at the format's own read step, whichever route is
taken. Scopus and Web of Science both emit a byte-order mark; EndNote does not.

## R2 — The specification: two source documents, not one

The authoritative primary document is Thomson Reuters ResearchSoft's *RIS Format Documentation*
(last updated May 2009), available at
<https://www.knime.com/sites/default/files/direct_export_ris_documentation_0.pdf>.

There are **two specification generations**, and the difference is load-bearing:

- **Old RIS** (Thomson, 2001) — flat tag meanings. `A1`/`AU` are authors, `A2`/`ED` editors,
  `A3` series editors.
- **New RIS** (2011) — re-tabulated per reference type, so a tag's meaning became type-dependent.

The line format is exactly `XX␣␣-␣`: two spaces, a dash, one space. `TY` must be first and `ER`
last; every other tag may appear in any order. Only the author tags and `KW` are documented as
repeatable, which producers ignore.

The spec's own fallback rule for an unrecognised reference type is *"it will be labeled as
Generic"*, which maps directly to this feature's FR-011 and CSL `document`.

## R3 — The mapping table to adapt: citation-js, MIT

`@citation-js/plugin-ris` is the only open-source project mapping RIS directly to CSL JSON with no
intermediate item-type vocabulary, and it is **MIT licensed**:

- Types (61 RIS codes → CSL): `packages/plugin-ris/src/spec/types.json`
- Fields, 2011 spec, 143 type-conditional rules: `packages/plugin-ris/src/spec/new.json`
- Fields, pre-2011 spec: `packages/plugin-ris/src/spec/old.js`

Its rules carry a `when.source.TY` condition, which is exactly the shape FR-013, FR-015 and FR-017
require for their type-conditional resolutions.

**Zotero's `RIS.js` is AGPL-3.0-or-later.** It is richer on creator-role nuance and is the only
source modelling producer-degenerate tags, but its tables must **not** be copied into this package.
It was read as evidence and is cited as such, nothing more.

Output is validated against CSL JSON 1.0.2's own schema
(`citation-style-language/schema`, `schemas/input/csl-data.json`, MIT).

## R4 — Contributor tags resolve on the reference type, and the spec says so

The primary specification defines `AU`, `A2`, `A3`, `A4` as *"Authors, Editors, Translators… preceded
by the tag that corresponds to the author role (see individual ref type matrix for role
definitions)"*. There is no fixed global meaning for `A2`, by design.

The spec's own `CHAP` sample puts the book's editors in `A2`. The resolution, from citation-js's
encoding of the 2011 matrix:

| Tag | CSL role | On reference types |
|---|---|---|
| `A2` | `editor` | `CHAP`, `ECHAP`, `CONF`, `CPAPER`, `ENCYC`, `DICT`, `SER`, `EBOOK`, `MUSIC`, `ANCIENT`, `BLOG` |
| `A2` | `collection-editor` | `BOOK`, `EDBOOK`, `RPRT`, `ELEC`, `MAP`, `CLSWK`, `COMP`, `MULTI`, `UNPB` |
| `A3` | `editor` | `BOOK` |
| `A3` | `collection-editor` | `CHAP`, `CONF`, `SER`, `EBOOK`, `ADVS`, `MUSIC`, `SLIDE`, `SOUND`, `VIDEO` |
| `A4` | `translator` | `BOOK`, `CHAP`, `ANCIENT`, `CLSWK`, `CTLG`, `DICT`, `EDBOOK`, `ENCYC`, `PAMP` |
| `AU` | `editor` | `EDBOOK` |

So on a book the editor is `A3`, on a chapter it is `A2`, and on an edited book it is `AU`.

**`ED` is in neither official specification** — Zotero's maintainers reject it on those grounds — and
**Web of Science uses it as its only editor tag, never `A2`.** Verified: a genuine WoS `CHAP` record
carries three `ED` tags and zero `A2`. It must be supported and documented as non-canonical.

**`TA` is not supported.** It is absent from the primary spec, Zotero drops it explicitly, and in the
one corpus file where it appears it is PubMed's journal-title abbreviation — an unrelated meaning.
Treating it as a name field would be actively wrong.

**Producer summary:** EndNote follows the spec (`A2`). Web of Science uses `ED` exclusively. Scopus
uses `A2` exclusively and repurposes `A4` for conference sponsors.

## R5 — Dates: `PY` is the anchor, `DA` is not an access date

Measured across the corpus in R7, for the three supported producers:

| Producer | Emits |
|---|---|
| EndNote | `PY` only |
| Scopus | `PY` only |
| Web of Science | `PY` + `DA` |

None of the three emits `Y1`, which is the signature of Ovid, CINAHL, RefWorks, Google Scholar and
Rayyan — worth handling anyway, since those files reach users.

**Wikipedia states that `DA` is the date accessed. It is wrong.** The primary spec documents `DA`
with a publication-date format (`YYYY/MM/DD/other info`, where the slashes are mandatory and the
components optional), Zotero maps it to the issued date, and citation-js maps it to `issued` for
about forty types. Do not source this field from Wikipedia.

**Web of Science's `DA` carries no year.** Real values are `SEP 22`, `DEC`, and ranges like
`JUL-DEC`. It matches neither the spec's grammar nor any date parser on its own, and is only usable
spliced with `PY`.

**Resolution, deterministic and documented:** `issued` comes from `PY`. Where `DA` parses, it refines
the precision. Where `DA` is a year-less month fragment, `PY`'s year is spliced in. `Y1` is a
fallback alias for `PY` when `PY` is absent. `Y2` is the access date — the case FR-016 names — and
none of the three supported producers emits one.

Precedent for getting this wrong: JabRef #6065, where preferring `Y2` over `Y1` produced an access
date as the publication year.

## R6 — `SN`: no disambiguation in the format, so resolve on shape then type

`SN` is documented as "ISSN/ISBN" with no way to tell them apart, and the primary spec's own samples
use it both ways. Resolution is by value shape first (ISSN is `NNNN-NNNC` with a checksum, ISBN is
10 or 13 digits with its own) and by reference type second, with citation-js's per-type table as the
tiebreaker. On `RPRT` and `PAT`, `SN` is a report or patent number and **not an identifier at all**.

Each producer encodes multiple values differently, and all three cases are real:

- **Web of Science** — repeated `SN` tags. A genuine chapter record carries four: two series ISSNs
  and two ISBNs, print and electronic, in no marked order. The same record carries **two `DO`
  tags**, the chapter's and the book's.
- **Scopus** — annotates inline and strips the hyphen: `SN  - 20411723 (ISSN)`, and packs multiple
  values into one tag separated by `; `. The suffix must be stripped.
- **EndNote** — one tag, second value on an unprefixed continuation line. See R7.

CSL JSON holds one `ISSN` and one `ISBN`, so surplus values go to preservation under FR-024, which
is what FR-018 already requires.

## R7 — Continuation lines mean different things by producer *(spec fault, see Refinements)*

**This is the highest-risk finding in the research, and the approved spec gets it wrong.**

The specification permits wrapping a long value onto the next line and **does not require the
continuation line to be indented**. Producers exploit that in two incompatible ways. Counted across
genuine files:

| Producer | Untagged lines per 10 records | Indented | What they mean |
|---|---|---|---|
| **EndNote** | 120 | No | **another value** — 8 keywords under one `KW`, 2 ISSNs under one `SN` |
| **Web of Science** | 33 | Mostly | **wrapped prose** — a continued `AB` or `N1` |
| Scopus | 11 | No | wrapped prose, in the `N1` references block |

A real EndNote record:

```
KW  - article
biostratigraphy
Colorado
dinosaur
SN  - 1932-8494
1932-8486
```

Those are eight keywords and two ISSNs, not one long keyword and one long serial number.

The approved FR-007 says a value continued across several lines "MUST be read as one value". Applied
to that record it concatenates eight keywords into one string and two ISSNs into a nonsense
identifier — **on the primary support target.** Indentation does not separate the two cases reliably:
it is a Web of Science habit, not a rule, and EndNote never indents.

**Resolution: the rule is per tag, not per file.** A tag that is repeatable by nature — the author
tags, `KW`, `UR`, `SN`, `N1` — treats an untagged line as another value. A scalar or prose tag —
`AB`, `TI`, `T2` — joins it to the value with a single space. FR-007 is amended accordingly.

## R8 — `TY` can be absent from a whole Scopus export *(spec gap, see Refinements)*

If the person exporting unchecks "Source & document type", **Scopus omits `TY` entirely**, confirmed
by Scopus support in Zotero forum #40918 and independently in asreview discussion #1284.

Under the approved spec that file imports as nothing at all: FR-008 skips everything before the
first reference-type tag, there is no first reference-type tag, so every entry is skipped and the
run reports a successful import of nothing. A legitimate export from a supported producer silently
yields an empty catalogue, which is the exact failure mode FR-013 of the import contract exists to
prevent.

**Resolution:** a file containing no reference-type tag anywhere, but which does contain RIS tag
lines, is a parse failure reported through the result, naming the missing `TY`. FR-008 is amended to
scope the skip rule to files that have a first entry.

## R9 — Scopus mistypes book chapters as `JOUR`

A genuine Scopus record for a book chapter carries `TY - JOUR`, the book's title in `T2`, the book's
editors in `A2`, and `M3 - Book Chapter`. `M3` is the more reliable type signal from Scopus than
`TY`.

This is not corrected. The catalogue stores what the source states, and inferring that an entry is
really a chapter from a combination of other tags is exactly the guessing FR-031's "read the
specification, preserve the rest" boundary rules out. It is recorded here so the behaviour is a known
consequence rather than a surprise, and `M3` is preserved on the item under FR-024, so nothing is
lost.

It does mean `A2` must resolve to `editor` on `JOUR` as well, which is Zotero's rule and which
citation-js omits. Adopted, because the case is real in a supported producer's output.

## R10 — The verification corpus exists, and it is CC0

**`asreview/citation-file-formatting`** (<https://github.com/asreview/citation-file-formatting>)
publishes **the same ten bibliographic records exported through twenty-five different producers**,
licensed **CC0-1.0** — public domain, freely vendorable as fixtures. It includes genuine
`_baseline_endnote.ris`, `_baseline_scopus.ris` and `_baseline_webofscience.ris`.

**This satisfies FR-030 for all three supported producers, so no producer falls back to a
documentation-built fixture.** The *Verification corpus* section records that outcome.

One limitation: every record in the EndNote baseline is `TY - JOUR`, so it evidences nothing about
the chapter-editor question. Genuine chapter records come from:

- Web of Science chapters with `ED`: `ESHackathon/CiteSource`, `vignettes/benchmark_data` — **licence
  to be confirmed before vendoring.**
- Scopus chapters and the mistyped-`JOUR` case: `tributetotobler/bibliotobler`, `data/scopus.ris` —
  **licence unconfirmed.**
- JabRef's importer fixtures, **MIT**, including a genuine Scopus file.

Where a licence cannot be confirmed, the file is not vendored: the case it evidences is reproduced as
a constructed fixture and the *Verification corpus* section says so.

Producer fingerprints, for labelling fixtures:

- **Web of Science** — `AN - WOS:…`, `WE - Science Citation Index Expanded`, `J9`/`JI`, `PU`/`PI`/`PA`,
  a byte-order mark, no `UR` and no `DB`.
- **Scopus** — `DB - Scopus`, `N1 - Export Date:`, a `scopus.com/inward/record.uri` URL,
  `SN - NNNNNNNN (ISSN)`, `J2`, `C7`, a byte-order mark.
- **EndNote** — tags in alphabetical order, unindented multi-value continuation lines, `ST`, a
  trailing `ID`, no byte-order mark.

**Negative fixture:** `rispy`'s `example_wos.ris` is not RIS at all — it is Web of Science's native
tagged format under a `.ris` extension. It is the natural test for the "a file that is not RIS"
edge case, alongside a `.bib` file.

## R11 — Other mappings worth pinning now

- **`T2` is the container title for all three supported producers.** `JO` and `JF` are absent from
  every one of their exports. Several producers use `JO` for the full name against the spec, which is
  a documented source of real bugs (JabRef #1074, #2506). `J2` is the abbreviation and Scopus emits
  it.
- **`SP` alone can carry a whole range** (`SP - 476-481`), including in the primary spec's own
  sample. On `BOOK`, `EBOOK`, `EDBOOK` and `THES`, `SP` is the number of pages, not a locator.
- **`C7` is the article number** in both Scopus and Web of Science output — a genuine cross-producer
  convergence worth honouring.
- **`M1` has eleven conflicting type-conditional meanings** between citation-js and Zotero. No
  consensus exists, so it is mapped only where this feature explicitly supports the type and
  preserved otherwise.
- **`AN` is Web of Science's record identifier** in RIS output (`WOS:000282053100002`). Clarivate's
  documentation names `UT` instead, but that describes their native export format, and no genuine WoS
  RIS file uses it.
- **`DO` values carry prefixes in the wild**, including in the primary spec's own examples
  (`DO - DOI:10…`). The existing BibTeX normalizer already handles the resolver-URL and `doi:` label
  cases.

## Open questions carried into implementation

- **Licence confirmation** for the CiteSource and bibliotobler fixture files, before either is
  vendored.
- **EndNote's chapter-editor tag is inferred, not observed.** No genuine EndNote file containing a
  book chapter was found anywhere, and no first-party Clarivate document enumerating EndNote's RIS
  output per reference type is public. The behaviour follows the specification EndNote implements.
  This is the likeliest thing to need correcting against a real file later, and it is the risk
  already named at the Spec gate.

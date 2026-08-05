# Implementation Plan: Import References from RIS Files

**Branch**: `005-import-references-ris` · **Date**: 2026-08-05 · **Spec**: `spec.md` ·
**Research**: `research.md` · **Decisions**: `decisions.md`

**Constitution**: v3.1.0 (`memory/constitution.md`) — three core articles were ratified after the
spec was written and are checked below.

## Summary

Add a hand-rolled RIS format at `literature/importers/ris.py`, plugged into the `BibFormat` seam
delivered under issue #21. It supplies `parse` (file → entries, as a generator) and `to_csl_json`
(one entry → CSL JSON), plus `handle_for`, and inherits atomicity, per-entry reporting, ordering and
dry runs unchanged. It ships in `DEFAULTS` alongside BibTeX.

The work divides along the spec's four stories, and they are genuinely independent after a
foundational phase that puts the parser and the class skeleton in place.

## Technical Context

**Language**: Python 3.12+ · **Framework**: Django 5.2 / 6.0 · **Test**: pytest + pytest-django +
factory_boy (`mvp-shared[test]`)

**New runtime dependency**: none. The parser is hand-rolled — see `decisions.md` D11 and research R1.
`rispy` fails FR-006, FR-008, FR-009 and FR-018 outright and returns zero records for a file carrying
a byte-order mark.

**Existing code this builds on:**

| Path | Role |
|---|---|
| `literature/importers/base.py` | `BibFormat` — `parse`, `to_csl_json`, `handle_for` abstract; the rest of the workflow provided |
| `literature/importers/config.py` | `DEFAULTS` tuple; the RIS format is appended here (FR-003) |
| `literature/importers/results.py` | `Outcome`, `EntryResult`, `ImportResult` — unchanged |
| `literature/converters.py` | `from_csl_json` — unchanged; `_resolve_citation_key` is why FR-019 exists |
| `literature/importers/bibtex.py` | **Read for pattern, not rewritten.** Its `_normalize_doi`, `_normalize_isbn` and `_clean_text` solve problems RIS has too |

**Shared normalization — narrowed at S3R.** Exactly two helpers in `bibtex.py` are format-neutral and
genuinely needed by RIS: `_normalize_doi` and `_normalize_isbn`. They move to
`literature/importers/normalizers.py` as an `IdentifierNormalizer` class, and `bibtex.py` imports
them from there — a move that changes no BibTeX behaviour and is covered by the existing BibTeX
suite. This is the one place the plan touches `bibtex.py`.

**`_clean_text`, `_unescape_entities` and `_clean_identifier` stay in `bibtex.py`.** The design review
caught the original plan moving them too. They are a LaTeX layer: `_clean_text` is
`_unescape_entities(latex_to_unicode(value))`, and `_clean_identifier` dispatches on BibTeX's own
field names. RIS carries no LaTeX, so running that decoder over RIS values would silently rewrite
genuine content — a DOI or URL containing `~`, `_`, `^`, `%` or braces comes out altered, against
FR-024 and FR-025. RIS does its own whitespace cleaning, because RIS has no escape layer to decode.

## Constitution Check

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I — Test-First | Every task writes its test before its code. Corpus fixtures land before the mapping they exercise. | Satisfied by task order |
| II — Simplicity | One new module plus one extracted normalizer module. No registry and no plug-in machinery beyond what #21 already delivers. | Pass |
| III — Anti-Abstraction | No base class or hierarchy invented for a third format that does not exist. `BibFormat` is the abstraction and it already ships. Declining `rispy` avoids a third naming layer. | Pass |
| V — Security & data-safety | `.ris` content is untrusted (FR-035). The parser is pure line handling: no `eval`, no path resolution, no network. Decoding is `utf-8-sig` with explicit error handling. | Pass |
| VI — Documentation | `CONTEXT.md` gains the minted citation key, *record* as RIS's spelling of *entry*, the extended *dialect* entry, and RIS spellings on *field* and *entry type* (FR-036). The tag mapping is documented (FR-012). | Task T-DOC |
| VII — Dependency discipline | **No new runtime dependency.** The alternative was examined empirically and rejected with evidence. | Pass |
| VIII — i18n | Every failure reason wrapped in `gettext_lazy` (FR-034). | Pass |
| IX — CSL JSON lingua franca | RIS maps to CSL JSON and nothing else; the existing conversion builds the item. | Pass |
| X — Embeddable package | Public names importable from `literature` (FR-033); the format is in `DEFAULTS` so no configuration is required (FR-003). | Pass |
| XI — Data integrity | Entry atomicity is the contract's, inherited unchanged. No half-built items. | Pass |
| **XIII — Data-model conventions** *(new in v3.1.0)* | **No model fields are added and no migration is generated.** Preservation uses the mechanism the BibTeX format already writes to. | Not engaged — asserted by a test |
| **XIV — Test structure** *(new in v3.1.0)* | `tests/test_importers/test_ris.py` mirrors `literature/importers/ris.py`; `test_normalizers.py` mirrors the extracted module. Tests grouped in `Test<Subject>` classes. Shared fixtures in `conftest.py`, corpus files under `tests/data/ris/`. No new model, so no new factory. | Pass |
| **XV — Cohesion** *(new in v3.1.0)* | **The constraining one.** `bibtex.py` is 15 module-level functions sharing subjects, which this article now rules out. RIS is written to the article: `RISParser`, `RISMapping` and `IdentifierNormalizer` are classes and `RISFormat` composes them. `bibtex.py`'s existing shape is pre-existing drift, out of scope under the spec's own assumption — noted, not fixed here. | Pass for new code |

**No constitution violation requires justification.** The Complexity Tracking table is empty.

## Project Structure

### Documentation (this feature)

```
specs/005-import-references-ris/
├── spec.md              # approved at the Spec gate; amended at S3 (see Refinements)
├── research.md          # R1–R11
├── decisions.md         # D1–D15
├── data-model.md        # the RIS→CSL mapping tables, as documentation (FR-012)
├── plan.md              # this file
├── tasks.md
├── progress.md
└── feature-state.json
```

### Source code

```
literature/importers/
├── config.py            # MODIFIED: append RISFormat to DEFAULTS
├── normalizers.py       # NEW: shared value normalization, extracted from bibtex.py
├── bibtex.py            # MODIFIED: import normalizers from the new module (a move, no behaviour change)
└── ris.py               # NEW: RISParser, RISMapping, RISFormat

tests/
├── data/ris/            # NEW: the verification corpus
│   ├── genuine/         # CC0 producer-written exports (endnote, scopus, webofscience)
│   ├── constructed/     # one malformation per file
│   └── negative/        # a .bib file and WoS native format, both under .ris names
└── test_importers/
    ├── test_ris.py      # NEW
    └── test_normalizers.py   # NEW
```

## Design

### The parser (`RISParser`)

A generator, not a list builder — this is where FR-004 is genuinely satisfied and where `rispy` could
not help, since all its entry points materialise a list. It yields one entry at a time, each carrying
its raw tags in source order, its index, and the line number it started at, so a failure reason can
name a location.

Line grammar: `^([A-Z][A-Z0-9])\s{0,2}-\s?(.*)$`, deliberately tolerant of the single-space and
double-space-after-dash variants real producers emit. An entry opens at `TY` and closes at `ER` or at
the next `TY`, which is what recovers the final entry of a file whose `ER` is missing (FR-006).

Untagged lines resolve **per tag**, per FR-007 as amended: a repeatable tag takes another value, a
scalar tag joins with a space. The repeatable set is a class-level frozenset **on `RISParser`**, not
on `RISMapping` — tag repeatability is a fact about RIS syntax, decidable from the tag alone, and has
nothing to do with the CSL mapping. Putting it on the mapping would make the parser untestable
without the mapping tables, for a purely syntactic decision.

**Decoding.** Read as `utf-8-sig`. On `UnicodeDecodeError`, raise a `ParseError` whose
`gettext_lazy` message names the attempted encoding and the byte offset (FR-034, and the spec's
encoding edge case). Without that, the reported reason is a raw untranslated Python string naming no
encoding — the failure is contained, but useless to the person holding the file.

**Whole-file outcomes, three distinct cases.** The original plan collapsed these and made an empty
file a parse failure, which the spec's Edge Cases forbid:

1. An empty or whitespace-only file is a **successful import of nothing** — empty result, catalogue
   unchanged (spec Edge Cases).
2. A file with RIS tag lines but no `TY` anywhere is a **parse failure** naming the missing tag
   (FR-008a).
3. A file with content but no recognisable tag lines is a **parse failure** naming the encoding or
   the format (spec Edge Cases, SC-008).

**How the skipped header is signalled.** Header material is **yielded** as a sentinel entry, and
`to_csl_json` raises `SkipEntry` for it — the pattern `bibtex.py` already uses for `@comment` and
`@preamble`. It is not raised from the generator: `base.py` catches `SkipEntry` from the iterator
with a `try` spanning the whole loop, so raising it there would end the file after the header and
report a single skipped entry for an otherwise good export. The header consequently occupies index 0
and shifts entry indices, which is intended and is what FR-007 of the import contract means by one
result per element found.

### The mapping (`RISMapping`)

Data tables plus the resolutions that need the reference type. Adapted from citation-js's
MIT-licensed per-type rules, never from Zotero's, which is AGPL (research R3).

- Reference type → CSL item type, `document` as the documented fallback (FR-011).
- Tag → CSL variable, type-conditional where the format demands it (FR-012).
- Contributor roles resolved on the reference type: `A2` is `editor` on chapter-like types and
  `collection-editor` on book-like ones, `A3` inverts on `BOOK`, `AU` is `editor` on `EDBOOK`, and
  `ED` is supported as Web of Science's non-canonical editor tag (FR-013, research R4).
- Dates: `PY` anchors, `DA` refines precision, a year-less `DA` is spliced with `PY`'s year, `Y1`
  falls back for `PY`, `Y2` is the access date (FR-015, FR-016, research R5).
- `SN` resolved by value shape first and reference type second; on `RPRT` and `PAT` it is a report or
  patent number, not an identifier at all (FR-017, research R6).

### The citation key

`ID` verbatim where present (FR-020). Otherwise minted from the first author's family name, the
issued year, and the first significant title word, deterministically (FR-021). An entry with none of
those falls back to its index. The scheme is documented in `data-model.md` and in the module
docstring, which is what FR-021 means by documented where a user can read it.

**FR-022 is delivered by overriding `entry_created`, not by `handle_for` — corrected at S3R.** The
original plan had `handle_for` report the stored key, which the inherited workflow makes impossible:
`import_entry` calls `handle_for` first, and the de-duplication suffix is only chosen two steps
later, inside `from_csl_json` → `_resolve_citation_key`, at store time. `handle_for` receives only
the raw entry and cannot know it. So `handle_for` returns the minted or `ID` key — which is what
failed and skipped entries carry — and `RISFormat` overrides `entry_created`, which does receive the
stored `Item`, to report `item.citation_key`. `entry_created` is a documented override point on
`BibFormat` and receives the item on dry runs too, before the base drops it, so both halves of FR-022
are satisfied with **no change to `base.py`, `results.py` or `converters.py`**, which keeps SC-009
honest.

**Preservation goes under a single `custom["ris"]` key.** `from_csl_json` treats `custom` two ways
at once: the whole dict lands on `Item.custom`, and every key whose value is a plain string
*additionally* becomes an `ItemIdentifier` row typed by that key. `bibtex.py` deliberately nests its
unmapped sweep under one `custom["bibtex"]` dict to dodge that, and RIS does the same. Written flat,
every unmapped RIS tag would become an identifier row — and since `ItemIdentifier.value` is capped at
500 characters and validated in `save()`, a long Scopus `N1` block or a Web of Science address block
would raise and **fail the whole entry**, which is exactly what US-4 acceptance scenario 2 forbids.

## The de-duplication ceiling (issue #41) — closed, not carried

Design review found that `_generate_dedup_suffix` in `converters.py` emits 701 distinct suffixes and
then repeats forever, while `_resolve_citation_key` consumes it in a loop that only exits on a free
key. Past 701 items sharing a base key the loop does not terminate.

**It is closed as not worth fixing, and this feature does not depend on it.** Reaching the ceiling
needs 702 records agreeing on family name, year *and* first significant title word — in practice the
same single record imported 702 times, which is artificial rather than merely unlikely. The secondary
effect, one query per suffix candidate, costs a few dozen queries at realistic collision counts.

Recorded here because the first revision of this plan had it fixed in-branch and made a separate pull
request a merge dependency, on a severity that had been adopted from a reviewer rather than checked.
The diagnosis is preserved on the closed issue if anyone ever meets it.

## Story boundaries

| Story | Issue | Delivers | Depends on |
|---|---|---|---|
| **Foundational** | — | `normalizers.py` extraction, the #41 fix, `RISParser`, the class skeleton, corpus vendoring | — |
| **US-1** | #36 | Reference types, core tag mapping, contributors, dates, identifiers, citation keys, skip and fail outcomes | Foundational |
| **US-2** | #37 | Normalization and recovery: DOI forms, unparseable dates, malformed identifiers, tolerant separation | US-1 |
| **US-3** | #38 | Producer conventions: `ED`, `A2` on `JOUR`, `SN` disambiguation, `DA` splicing, multi-value encodings | US-1 |
| **US-4** | #39 | Preservation of unmapped tags and surplus values | US-1 |

**US-2 depends on US-1 — corrected at S3R.** The original plan called it independent on the grounds
that it exercises the parser and the normalizers rather than the mapping. Every US-2 task in fact
asserts on a *stored* item, and storing one goes through `from_csl_json`, which raises when the item
type is missing or unrecognised and again when no citation key is present. Those are T010 and T015,
both US-1. The spec agrees: US-2's own Independent Test is "asserting the two produce equivalent
catalogue items". So all three later stories depend on US-1, and only the foundational phase runs
before it.

## Complexity Tracking

No constitutional violation is claimed, so this table is empty.

## Risks

- **EndNote's chapter-editor tag is inferred, not observed.** No genuine EndNote file containing a
  book chapter was found, and Clarivate publishes no per-type tag table. The mapping follows the
  specification EndNote implements. This is the likeliest thing to need correcting against a real
  file later, and it is the risk already named at the Spec gate.
- **Two fixture corpora have unconfirmed licences.** The Web of Science and Scopus chapter files come
  from repositories whose licences must be checked before vendoring. Where a licence cannot be
  confirmed, the case is reproduced as a constructed fixture and the corpus section says so.
- **`bibtex.py` is now non-conformant with Article XV.** Pre-existing drift, out of scope here, and
  the standards-alignment pass is its proper home rather than this feature.

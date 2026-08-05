# Tasks: Import References from RIS Files

**Feature**: `005-import-references-ris` · **Spec**: `spec.md` · **Plan**: `plan.md`

Article I is Test-First: within every task the test is written and seen to fail before the code that
makes it pass. `[P]` marks tasks that may run in parallel with their siblings — different files, no
shared state.

*Revised 2026-08-05 after the S3R design-review panel. Changes are marked `(S3R)`.*

## Phase 0 — Foundational (blocks every story)

- **T001** Vendor the genuine corpus. Add `tests/data/ris/genuine/{endnote,scopus,webofscience}.ris`
  from `asreview/citation-file-formatting` (CC0-1.0), each with a `SOURCE.md` recording origin,
  licence and retrieval date. Assert in a test that each file is non-empty and carries its
  producer's fingerprint (research R10). **FR-030**
- **T002 [P]** Check the licences of the Web of Science and Scopus *chapter* corpora
  (`ESHackathon/CiteSource`, `tributetotobler/bibliotobler`). Vendor where the licence permits;
  otherwise reproduce the chapter-with-editors case as a constructed fixture and record the
  substitution in the spec's *Verification corpus* section. **FR-030**
- **T003 [P]** Add constructed fixtures under `tests/data/ris/constructed/`, one malformation per
  file: **an empty file (S3R)**; missing final `ER`; no `TY` anywhere; a tag block with no `TY` after
  a valid entry; header material before the first entry; a byte-order mark; CRLF line endings;
  single-space separator; wrapped prose values; EndNote-style multi-value continuation lines; an entry
  with `TY` and nothing else; a truncated final entry; **a CP1252-encoded entry (S3R)**; **an entry
  carrying an unmapped tag whose value exceeds 500 characters (S3R)**; **a file of several hundred
  entries, which is the file FR-004 is asserted against (S3R)**.
- **T004 [P]** Add negative fixtures under `tests/data/ris/negative/`: a BibTeX file and Web of
  Science's native tagged format, both named `.ris` (research R10).
- **T005** Extract `normalizers.py`. **Narrowed at S3R to `_normalize_doi` and `_normalize_isbn`
  only**, as an `IdentifierNormalizer` class per Article XV. `_clean_text`, `_unescape_entities` and
  `_clean_identifier` stay in `bibtex.py` — they are a LaTeX layer, and running that decoder over RIS
  values would silently rewrite genuine content. Re-point `bibtex.py`'s imports. Add
  `tests/test_importers/test_normalizers.py`. **The whole existing BibTeX suite must stay green and
  unmodified** — that is what proves this is a move and not a rewrite. **Article XV**
- **T006** `RISParser` — the line grammar and entry framing. Tag regex tolerant of the separator
  variants; entry opens at `TY`, closes at `ER` or the next `TY`; yields one entry at a time carrying
  raw tags in source order, index and start line. **Decode `utf-8-sig`, and on `UnicodeDecodeError`
  raise a `ParseError` whose `gettext_lazy` message names the attempted encoding and byte offset
  (S3R)** — otherwise the reason is a raw untranslated Python string naming no encoding. **Assert the
  streaming property (S3R): consume one entry from the large fixture and assert the remainder was
  never read or converted, so the test fails if `parse` is ever rewritten to build a list.**
  **FR-004, FR-006, FR-010, FR-034, spec Verification corpus**
- **T007** Per-tag continuation handling: a repeatable tag takes an untagged line as another value, a
  scalar tag joins it with a space. **The repeatable set is a class-level frozenset on `RISParser`
  (S3R)**, not on `RISMapping` — repeatability is RIS syntax, not CSL mapping. Asserted against both
  the EndNote multi-value fixture and the Web of Science wrapped-prose fixture. **FR-007 (amended)**
- **T008** Whole-file outcomes, **three distinct cases (S3R)**: an empty or whitespace-only file is a
  successful import of nothing; a file with tag lines and no `TY` anywhere is a parse failure naming
  the missing tag; a file with content but no recognisable tag lines is a parse failure naming the
  encoding or format. None raised to the caller. **Header material is *yielded* as a sentinel entry
  and `SkipEntry` is raised from `to_csl_json` (S3R)** — the pattern `bibtex.py` uses — never from the
  generator, where `base.py`'s `try` spans the whole loop and would end the file after the header.
  **FR-008, FR-008a, FR-009, SC-008, spec Edge Cases**
- **T009** `RISFormat` skeleton subclassing `BibFormat`, wired into `DEFAULTS` in `config.py`, and
  exported from the `literature` namespace. A smoke test imports it by name through
  `available_formats()` and runs an import over the empty-file fixture. **FR-001, FR-003, FR-033**

**Checkpoint:** `forge verify` green. A `.ris` file parses into entries and reports outcomes, with no
mapping yet.

## Phase 1 — US-1: Import a set of search results (P1, issue #36)

- **T010** Reference-type table: RIS type → CSL item type, unknown types to `document`. Accept the
  `GRNT`/`GRANT` and `UNPD`/`UNPB` spelling variants (research R2). **FR-011**
- **T011** Core tag → CSL variable table, with the type-conditional cases the format demands
  (`T2` as container versus collection title, `SP` as locator versus page count). **FR-012**
- **T012** Contributors: repeated tags become contributor records in order; roles resolved on the
  reference type (`A2` editor on chapter-like, `collection-editor` on book-like; `A3` inverts on
  `BOOK`; `AU` editor on `EDBOOK`). Institutional and unparsed names stored as literals rather than
  split. **FR-013, FR-014**
- **T013** Dates: `PY` anchors, `DA` refines precision, `Y1` falls back for `PY`, `Y2` is the access
  date. Precision preserved with no padded month or day. **FR-015, FR-016**
- **T014** Identifiers: `DO` and `UR` become typed identifier records; `SN` resolved by value shape
  then reference type; on `RPRT` and `PAT` it is a report or patent number and not an identifier.
  **FR-017**
- **T015** Citation keys: `ID` verbatim where present, otherwise minted deterministically from first
  author family name, issued year, and first significant title word, falling back to the entry's
  index. A test imports the same file twice and asserts identical minted keys, and asserts no entry
  in the corpus fails for want of one. **Any key `RISFormat` produces — minted or verbatim `ID` —
  is checked against `Item.citation_key`'s `max_length`, with headroom reserved for the
  de-duplication suffix that is appended afterwards, and a key that cannot fit fails the entry with a
  `gettext_lazy` reason naming the limit (S3R, widened round 2)** — `from_csl_json` excludes
  `citation_key` from `full_clean`, so nothing else catches it and the behaviour would otherwise
  differ between PostgreSQL and SQLite. **SC-003, SC-004, FR-019, FR-020, FR-021, FR-023, FR-034**
- **T016** **FR-022 via an `entry_created` override, not `handle_for` (S3R).** `handle_for` returns
  the minted or `ID` key, which is what failed and skipped entries carry. `RISFormat` overrides
  `entry_created` — a documented `BibFormat` override point that receives the stored `Item`, on dry
  runs too — to report `item.citation_key`, suffix included. The suffix does not exist when
  `handle_for` runs, so the original design was unimplementable without changing `base.py`. Assert no
  change to `base.py`, `results.py` or `converters.py` is required by this, **and that a dry run still
  reports the key while carrying `item is None` (S3R round 2)** — the base drops the item deliberately,
  because those rows do not survive the rollback. **FR-022, FR-002, SC-009**
- **T017** End-to-end over `genuine/endnote.ris`: one item per entry, all created, in source order,
  with expected types, contributor order, date precision and identifiers — in one call, with no prior
  conversion. **US-1 acceptance, SC-001, SC-007**

**Checkpoint:** US-1 independently testable and complete.

## Phase 2 — US-2: A messy export still imports (P2, issue #37)

*Depends on US-1 (S3R): every task here asserts on a stored item, and storing one needs the type
table (T010) and the citation key (T015).*

- **T018 [P]** DOI recovery: resolver-URL and `doi:` label forms normalized to a bare DOI through
  `IdentifierNormalizer.normalize_doi`. **FR-025**
- **T019 [P]** A value in a known identifier's tag that cannot be normalized is preserved on the item
  rather than discarded or stored as valid. **Preserved under `custom["ris"]` like every other
  preserved value (S3R round 2)** — RIS deliberately does not reproduce `bibtex.py`'s second, narrow
  mechanism of writing an unrescuable identifier flat under its source field name, which would create
  an `ItemIdentifier` row and fail the entry on a value over 500 characters. **FR-024, FR-027**
- **T020 [P]** An unparseable date goes to the item's existing fallback and does not fail the entry.
  **FR-026**
- **T021** An entry the parser cannot read fails alone with a reason, and the rest of the file still
  imports. An entry carrying `TY` and no other bibliographic content is reported as skipped.
  **FR-009, FR-027**
- **T022** Tolerant separation: CRLF, a byte-order mark, single-space separators and inconsistent
  entry separation all still yield the file's entries. **FR-010**
- **T023** The large mixed fixture from T003: every entry accounted for exactly once, and no entry
  refused for a reason normalization resolves. **US-2 acceptance, SC-002**

**Checkpoint:** US-2 independently testable and complete.

## Phase 3 — US-3: Web of Science and Scopus (P3, issue #38)

- **T024** `ED` supported as Web of Science's editor tag, documented as non-canonical. `A2` resolves
  to `editor` on `JOUR` as well, which is what Scopus's mistyped chapters require. **FR-013,
  research R4, R9**
- **T025 [P]** `SN` producer encodings: Web of Science repeats the tag, Scopus annotates inline with
  `(ISSN)`/`(ISBN)` and packs multiple values behind `; `, EndNote continues on an untagged line. The
  first resolves to an identifier and the surplus is preserved. **FR-017, FR-018, FR-024**
- **T026 [P]** Web of Science `DA` carries no year (`SEP 22`, `DEC`, `JUL-DEC`): splice `PY`'s year
  to reach month precision, or discard it rather than storing a wrong date. **FR-015**
- **T027 [P]** Multiple `DO` tags on one entry: first stored, remainder preserved. **FR-018**
- **T028** Equivalence, **and the one-name assertion folded in from the deleted T040 (S3R)**: the
  same ten references from `genuine/{endnote,scopus,webofscience}.ris` all import through the same
  registered format name, with no argument naming a producer, and produce equivalent catalogue items
  on item type, contributors and order, dates and precision, and identifiers. Divergences genuinely
  present in the source data are asserted explicitly rather than smoothed over. **US-3 acceptance,
  SC-005, FR-029**
- **T029** A file from an unnamed producer still imports: the tags the specification defines are read
  and the entry lands. **Narrowed at S3R round 2**: the "and the rest preserved" half is asserted
  corpus-wide by T033, inside the story that delivers preservation, so asserting it here made US-3
  depend on US-4 against the plan's own dependency graph. **FR-031**

*T040 deleted at S3R: its behavioural half is now in T028, and its structural half — a test asserting
the module "contains no producer-detection branch" — was a source-introspection assertion that breaks
on any refactor and passes vacuously if a fingerprint is spelled differently. The intent is recorded
as prose in `data-model.md` instead.*

**Checkpoint:** US-3 independently testable and complete.

## Phase 4 — US-4: Nothing is thrown away (P4, issue #39)

- **T030** Unmapped tags preserved **under a single `custom["ris"]` key (S3R)**, exactly as
  `bibtex.py` nests under `custom["bibtex"]`, never as flat `custom` keys. `from_csl_json` turns any
  flat `custom` key whose value is a string into an `ItemIdentifier` row, and `ItemIdentifier.value`
  is capped at 500 characters and validated in `save()` — so a flat write would turn a long Scopus
  `N1` block into a `ValidationError` that fails the whole entry. Assert **no `ItemIdentifier` row is
  created for any preserved tag**, and — folding in the deleted T031 — that such an entry is reported
  as created exactly as any other, with no extra outcome and no per-tag channel. No new model field
  and no migration. **FR-024, FR-028, Article XIII**
- **T032 [P]** A surplus value for a single-slot identifier or date is preserved rather than widening
  the model, and the entry is not failed. **A preserved value longer than 500 characters still leaves
  the entry created (S3R).** **FR-018, FR-024**
- **T033** Corpus-wide assertion: every tag in every genuine file is either mapped to a CSL variable
  or retrievable from the stored item. No tag absent from both. **US-4 acceptance, SC-006**

**Checkpoint:** US-4 independently testable and complete.

## Phase 5 — Cross-cutting and documentation

- **T034** `CONTEXT.md`: add the *minted citation key*; add *record* as RIS's spelling of *entry*;
  extend *dialect* to cover producer conventions that are not specified variants; add RIS spellings
  to *field* and *entry type*. **FR-036**
- **T035 [P]** `data-model.md`: the full tag and reference-type mapping tables, the contributor role
  resolution, the date precedence, the `SN` resolution, the citation-key scheme, and the note that
  producer fingerprints label fixtures and never reach the code. **FR-012**
- **T036 [P]** README: the support boundary — the package reads the common producers as best it can,
  makes no promise that every variant imports perfectly, and grows through bug reports and feature
  requests. Names EndNote primary, Web of Science and Scopus secondary. **FR-032**
- **T038 [P]** Security: assert no `.ris` content causes code execution, filesystem access, network
  access or an unhandled error, including over the negative fixtures. **FR-035, SC-008**
- **T039** **A PR-exit checklist item, not a test (S3R).** Confirm by `git diff` that the branch
  touches **no** file under the import contract — `base.py`, `results.py`, `converters.py` — and that
  the pre-existing import-contract, converters and BibTeX suites are green and unmodified. Also
  confirm `makemessages` is clean and that no human-readable string in the diff is unwrapped,
  **folded in from the deleted T037 (S3R round 2)**. Record the outcome against SC-009 in the PR body.
  **FR-002, FR-005, SC-009, FR-034**

*T041 removed at S3R round 2.* It was to fix the citation-key de-duplication ceiling (issue #41) in
`converters.py` from this branch. `converters.py` is literally "the code that builds an item from CSL
JSON", so SC-009's "any change that proved unavoidable is recorded as its own issue **rather than
made here**" forbids it, and amending T039 to grant its own exception is a gate certifying itself.
The fix lands as its own pull request off `main`, merged before this feature — which closes the hang
before the feature that makes it reachable ships, and keeps SC-009 true as written rather than
amending an approved success criterion.

## Dependencies

```
Phase 0 (T001–T009)
   └── Phase 1 US-1 (T010–T017) ──┬── Phase 2 US-2 (T018–T023)
                                  ├── Phase 3 US-3 (T024–T029)
                                  └── Phase 4 US-4 (T030–T033)
Phase 5 (T034–T036, T038, T039) last — T039 is the final gate
```

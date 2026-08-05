# Tasks: Import References from RIS Files

**Feature**: `005-import-references-ris` · **Spec**: `spec.md` · **Plan**: `plan.md`

Article I is Test-First: within every task the test is written and seen to fail before the code that
makes it pass. `[P]` marks tasks that may run in parallel with their siblings — different files, no
shared state.

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
  file: missing final `ER`; no `TY` anywhere; a tag block with no `TY` after a valid entry; header
  material before the first entry; a byte-order mark; CRLF line endings; single-space separator;
  wrapped prose values; EndNote-style multi-value continuation lines; an entry with `TY` and nothing
  else; a truncated final entry.
- **T004 [P]** Add negative fixtures under `tests/data/ris/negative/`: a BibTeX file and Web of
  Science's native tagged format, both named `.ris` (research R10).
- **T005** Extract `normalizers.py`. Move `_normalize_doi`, `_normalize_isbn`, `_clean_identifier`,
  `_unescape_entities` and `_clean_text` from `bibtex.py` into
  `literature/importers/normalizers.py` as a class, per Article XV. Re-point `bibtex.py`'s imports.
  Add `tests/test_importers/test_normalizers.py`. **The whole existing BibTeX suite must stay green
  and unmodified** — that is what proves this is a move and not a rewrite. **Article XV**
- **T006** `RISParser` — the line grammar and entry framing. Tag regex tolerant of the separator
  variants; entry opens at `TY`, closes at `ER` or the next `TY`; yields one entry at a time carrying
  raw tags in source order, index and start line. Decode `utf-8-sig`. **FR-004, FR-006, FR-010**
- **T007** Per-tag continuation handling: a repeatable tag takes an untagged line as another value, a
  scalar tag joins it with a space; the repeatable set is data, not a branch. Asserted against both
  the EndNote multi-value fixture and the Web of Science wrapped-prose fixture. **FR-007 (amended)**
- **T008** Whole-file outcomes: header material before the first entry reported as skipped; a file
  with tag lines and no `TY` anywhere reported as a parse failure naming the missing tag; a file with
  no recognisable tag lines reported as a parse failure naming the encoding or format; neither raised
  to the caller. **FR-008, FR-008a, FR-009, FR-014**
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
  index. A test imports the same file twice and asserts identical minted keys, and asserts no entry in the corpus fails for want of one. **SC-003, SC-004, FR-019, FR-020,
  FR-021, FR-023**
- **T016** `handle_for` reports the citation key **as stored**, de-duplication suffix included, and
  in a dry run the key that would have been stored. **FR-022**
- **T017** End-to-end over `genuine/endnote.ris`: one item per entry, all created, in source order,
  with expected types, contributor order, date precision and identifiers — in one call, with no prior conversion. **US-1 acceptance, SC-001, SC-007**

**Checkpoint:** US-1 independently testable and complete.

## Phase 2 — US-2: A messy export still imports (P2, issue #37)

- **T018 [P]** DOI recovery: resolver-URL and `doi:` label forms normalized to a bare DOI through
  `normalizers.py`. **FR-025**
- **T019 [P]** A value in a known identifier's tag that cannot be normalized is preserved on the item
  rather than discarded or stored as valid. **FR-024, FR-027**
- **T020 [P]** An unparseable date goes to the item's existing fallback and does not fail the entry.
  **FR-026**
- **T021** An entry the parser cannot read fails alone with a reason, and the rest of the file still
  imports. An entry carrying `TY` and no other bibliographic content is reported as skipped.
  **FR-009, FR-012, FR-027**
- **T022** Tolerant separation: CRLF, a byte-order mark, single-space separators and inconsistent
  entry separation all still yield the file's entries. **FR-010**
- **T023** A large mixed file: every entry accounted for exactly once, and no entry refused for a
  reason normalization resolves. **US-2 acceptance, SC-002**

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
- **T028** Equivalence: the same ten references from `genuine/{endnote,scopus,webofscience}.ris`
  produce equivalent catalogue items on item type, contributors and order, dates and precision, and
  identifiers. Divergences that are genuinely in the source data are asserted explicitly rather than
  smoothed over. **US-3 acceptance, SC-005**
- **T029** A file from an unnamed producer still imports: specified tags read, the rest preserved.
  **FR-031**
- **T040** One name, no detection. All three genuine files import through the same registered format
  name with no argument naming a producer, and a test asserts the format contains **no
  producer-detection branch** — nothing keys behaviour on `DB`, `AN`, a byte-order mark, or any other
  fingerprint. The fingerprints in `research.md` label fixtures; they must not reach the code.
  **FR-029**

**Checkpoint:** US-3 independently testable and complete.

## Phase 4 — US-4: Nothing is thrown away (P4, issue #39)

- **T030** Unmapped tags preserved on the item and retrievable afterwards, through the mechanism the
  BibTeX format already writes to. No new model field and no migration. **FR-024, Article XIII**
- **T031 [P]** Preservation changes no reporting: such an entry is created exactly as any other, with
  no extra outcome and no per-tag channel. **FR-028**
- **T032 [P]** A surplus value for a single-slot identifier or date is preserved rather than
  widening the model, and the entry is not failed. **FR-018, FR-024**
- **T033** Corpus-wide assertion: every tag in every genuine file is either mapped to a CSL variable
  or retrievable from the stored item. No tag absent from both. **US-4 acceptance, SC-006**

**Checkpoint:** US-4 independently testable and complete.

## Phase 5 — Cross-cutting and documentation

- **T034** `CONTEXT.md`: add the *minted citation key*; add *record* as RIS's spelling of *entry*;
  extend *dialect* to cover producer conventions that are not specified variants; add RIS spellings
  to *field* and *entry type*. **FR-036**
- **T035 [P]** `data-model.md`: the full tag and reference-type mapping tables, the contributor role
  resolution, the date precedence, the `SN` resolution, and the citation-key scheme — the documented
  artifact FR-012, FR-013, FR-015, FR-017, FR-018 and FR-021 each require. **FR-012**
- **T036 [P]** README: the support boundary — the package reads the common producers as best it can,
  makes no promise that every variant imports perfectly, and grows through bug reports and feature
  requests. Names EndNote primary, Web of Science and Scopus secondary. **FR-032**
- **T037 [P]** i18n: every human-readable string, failure reasons among them, wrapped in
  `gettext_lazy`; `makemessages` clean. **FR-034**
- **T038 [P]** Security: assert no `.ris` content causes code execution, filesystem access, network
  access or an unhandled error, including over the negative fixtures. **FR-035, SC-008**
- **T039** Assert the import contract is untouched: no change to `base.py`, `results.py` or
  `converters.py`, and the pre-existing import-contract and BibTeX suites green and unmodified.
  **FR-002, FR-005, SC-009**

## Dependencies

```
Phase 0 (T001–T009)
   ├── Phase 1 US-1 (T010–T017) ──┬── Phase 3 US-3 (T024–T029)
   │                              └── Phase 4 US-4 (T030–T033)
   └── Phase 2 US-2 (T018–T023)
Phase 5 (T034–T039) last — T039 is the final gate
```

# Tasks: Import References from BibTeX Files

**Input**: Design documents in `specs/004-import-references-bibtex/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md)

**Tests**: Required. Article I is Test-First, so within every story the test task comes before the
behaviour it describes and is expected to fail when written.

**Organization**: Grouped by user story. Phases 1 and 2 are shared and block everything. After them
US1, US2, US3 and US4 are independently implementable and independently testable, though they are
listed in priority order and US2 through US4 build on the mapping US1 establishes.

**Specification refinement applied 2026-08-04**: FR-005 is removed and FR-004 restored to the import
contract's scope, approved with the plan. The entry-level splitter and macro pre-pass that the
alternative would have required are not needed, so this list stands as written.

## Format: `[ID] [P?] [Story] Description`

- **[P]** — can run in parallel with others marked `[P]` in the same phase (different files, no
  shared dependency). Note that the story test tasks all write to the same `test_bibtex.py`, so they
  are sequential within a phase even though they are independent in subject.
- **[Story]** — the user story the task serves

---

## Phase 1: Setup

**Purpose**: Somewhere for every later task to land.

- [ ] T001 Create `tests/fixtures/bibtex/` for the corpus. Tests go in a single `tests/test_importers/test_bibtex.py` paired with the single source module, per the constitution's rule that test modules mirror the `literature/` tree; concerns are separated by test class, not by file.

---

## Phase 2: Foundational (blocking)

**Purpose**: The dependency, the corpus, and a format the contract's lookup can find. No story can
start until an import naming `bibtex` resolves to something.

- [ ] T002 Add `bibtexparser>=1.4.4,<2` and its declared `pyparsing>=2.0.3` to `[project.dependencies]` in `pyproject.toml`, refresh the lock file, and confirm `deptry` is green with both declared directly rather than relied on transitively (Article VII).
- [ ] T003 [P] Build the constructed half of the corpus in `tests/fixtures/bibtex/`: one file per malformation named in the specification (LaTeX-escaped names, DOI as resolver URL, DOI with a `doi:` label, unparseable date, unknown entry type, unknown fields, duplicate cite keys, duplicate field within an entry, `@string` macros, `@comment` and `@preamble`, `crossref` forward reference, `crossref` cycle, `crossref` to a missing entry, empty file, truncated file, non-BibTeX content, Latin-1 encoding), plus one clean multi-type file.
- [ ] T004 [P] Source the real half of the corpus: one genuine classic BibTeX export and one genuine BibLaTeX export from a mainstream reference manager, stripped of anything personal, plus one file large enough that a whole-file conversion would be visible. Record provenance in a `README.md` beside them.
- [ ] T005 Write `TestRegistration` in `tests/test_importers/test_bibtex.py`: `BibTeXFormat` is importable from the `literature` namespace (Article X), appears in `available_formats()` with no configuration because it is in the shipped defaults (FR-003), and `get_format("bibtex")` returns it.
- [ ] T006 Create `literature/importers/bibtex.py` with `BibTeXFormat`, its `name` and `label`, a `parse` that loads through `bibtexparser` and yields entries in source order, and a `to_csl_json` that returns the entry's type and cite key and nothing else yet. Add it to `DEFAULTS` in `literature/importers/config.py` and export it from `literature/__init__.py`. T005 goes green.

---

## Phase 3: US-1 — Import a reference library from a `.bib` file (P1)

**Goal**: A well-formed `.bib` file becomes catalogue items of the right kind, with contributors,
dates and identifiers intact.

**Independent test**: Import the clean multi-type fixture and assert item type, contributor order,
date precision and identifiers for every entry.

- [ ] T007 [US1] Write `TestEntryTypes`: every classic entry type maps to its CSL item type, and an unrecognised type maps to `document` rather than failing the entry (FR-006).
- [ ] T008 [US1] Write `TestFields`: each classic field maps to its CSL variable (FR-007).
- [ ] T009 [US1] Write `TestNames`: contributor lists keep source order and role; `von` particles, `Jr` suffixes and `Last, First` forms land in the right parts of `Name`; a brace-wrapped institutional name goes to `literal` unsplit (FR-008, FR-009).
- [ ] T010 [US1] Write `TestDates`: a year alone stores year precision, a year and month store month precision, and neither pads a component the source did not state (FR-010).
- [ ] T011 [US1] Write `TestIdentifiers`: `doi`, `isbn`, `issn` and `url` become typed identifier records (FR-011).
- [ ] T012 [US1] Write `TestHandles`: the cite key becomes the item's citation key and is the handle on every entry result (FR-012).
- [ ] T013 [US1] Write `TestBlocks`: `@string` macros are expanded in the entries referencing them (FR-013); `@comment` and `@preamble` are reported as skipped, not failed, and create no item (FR-014); a field repeated inside one entry resolves deterministically (FR-016).
- [ ] T014 [US1] Write `TestCrossref`: an entry inherits its parent's fields where it states none of its own, including where the parent appears later in the file, and the child is still reported at its own position; a cycle terminates and is reported rather than hanging (FR-015).
- [ ] T015 [US1] Define the entry-type table and the field table at the top of `literature/importers/bibtex.py`, each entry annotated with the dialect it comes from. Classic BibTeX only at this stage; US3 extends both. T007 and T008 go green.
- [ ] T016 [US1] Implement name mapping in `bibtex.py` using `customization.splitname`, mapping First/von/Last/Jr onto given, particles, family and suffix, and routing brace-wrapped names to `literal`. T009 goes green.
- [ ] T017 [US1] Implement date mapping, building CSL date parts at the precision stated. T010 goes green.
- [ ] T018 [US1] Implement identifier mapping to top-level CSL identifier fields. T011 goes green.
- [ ] T019 [US1] Implement `handle_for` and citation-key mapping. T012 goes green.
- [ ] T020 [US1] Configure `parse` with `interpolate_strings`, `common_strings` and `add_missing_from_crossref`, and yield comments and preambles explicitly so `to_csl_json` can raise `SkipEntry` for them. Resolve repeated fields deterministically and document the rule. T013 and T014 go green.

**Checkpoint**: US1 is independently deliverable. A clean library imports correctly.

---

## Phase 4: US-2 — A messy export still imports (P2)

**Goal**: Recoverable values are cleaned on the way in, unrecoverable ones are kept, and an entry is
refused only when nothing is left to build from.

**Independent test**: Import the malformed fixtures alongside the clean file holding the same
references and assert the two produce equivalent records.

- [ ] T021 [US2] Write `TestCleaning`: a DOI written as a resolver URL or carrying a `doi:` label normalizes to the bare identifier (FR-017); LaTeX escapes decode to the characters they represent and capitalization-protecting braces are removed, while an unrecognised construct is left as it stands rather than dropped (FR-018).
- [ ] T022 [US2] Write `TestRecovery`: a value that cannot be normalized into something the catalogue accepts is preserved instead of failing its entry (FR-019); an unresolvable date goes to the record's existing fallback (FR-020); an entry is reported as failed only where it cannot be parsed or the catalogue rejects it after recovery (FR-021).
- [ ] T023 [US2] Add the cleaning helpers to `bibtex.py`: LaTeX decoding through `latexenc.latex_to_unicode`, brace stripping, and per-field normalization for DOI and ISBN. Nothing in them evaluates their input (FR-029). T021 goes green.
- [ ] T024 [US2] Wire cleaning into `to_csl_json` ahead of mapping, and route values that survive cleaning but still will not validate into preservation rather than failure. T022 goes green.
- [ ] T025 [US2] Assert the whole corpus imports with no entry refused for a reason normalization resolves, and every refusal carrying a reason naming what could not be recovered (SC-002).

**Checkpoint**: US2 is independently deliverable. A real, messy export imports.

---

## Phase 5: US-3 — A BibLaTeX export imports the same way (P3)

**Goal**: One format name reads both dialects, with no caller intervention.

**Independent test**: Import equivalent libraries exported in both dialects and assert equivalent
records.

- [ ] T026 [US3] Write `TestBibLaTeX`: `journaltitle` lands as container title exactly as `journal` does; a single `date` field stores at the precision it states; BibLaTeX-only entry types map to their CSL types rather than to `document`; a file mixing both conventions reads correctly (FR-022, FR-023).
- [ ] T027 [US3] Write `TestPrecedence`: an entry carrying both `date` and `year` that disagree resolves deterministically, in the documented direction (FR-024).
- [ ] T028 [US3] Extend both tables to BibLaTeX types and fields, keeping the dialect annotation. T026 goes green.
- [ ] T029 [US3] Implement field precedence where the dialects supply the same information twice, and document the direction. T027 goes green.
- [ ] T030 [US3] Assert equivalence across the two real exports: same item types, contributors and order, date precision, and identifiers (SC-005).

**Checkpoint**: US3 is independently deliverable. Either dialect imports under one name.

---

## Phase 6: US-4 — Nothing in the file is thrown away (P4)

**Goal**: Source fields with no CSL equivalent survive on the record without changing what an import
reports.

**Independent test**: Import a file carrying reference-manager bookkeeping fields and assert they are
retrievable afterwards.

- [ ] T031 [P] [US4] Write `TestPreservation`: unmapped fields are retrievable from the stored item (FR-025); the entry is reported as created exactly as one without them, with no extra outcome and no per-field reporting (FR-026); an unresolvable `crossref` is preserved as an ordinary unmapped field and does not fail the entry.
- [ ] T032 [US4] Collect every unmapped source field into CSL `custom` so it lands in `Item.custom`, including an unresolved `crossref`. T031 goes green.
- [ ] T033 [US4] Assert across the corpus that every field present in a source entry is either mapped to a CSL variable or retrievable from the stored record, with none absent from both (SC-006).

**Checkpoint**: All four stories deliverable. The feature is functionally complete.

---

## Phase 7: Cross-cutting (convergence)

**Purpose**: The obligations that span the feature rather than belonging to one story.

- [ ] T034 [P] Generate `docs/bibtex-mapping.md` from the tables in `bibtex.py` so the published mapping cannot drift from the code, and add a test asserting the two agree (FR-007).
- [ ] T035 [P] Add the four glossary entries to `CONTEXT.md`: entry type, field, dialect, and cite key, with cite key recording its relationship to the existing *citation key* (FR-030).
- [ ] T036 [P] Write `TestContainment`: `bibtexparser` is imported by `literature/importers/bibtex.py` and by no other module, so the parser stays replaceable.
- [ ] T037 i18n pass: every human-readable string the feature emits, failure reasons included, wrapped for translation, and `makemessages` clean (FR-028).
- [ ] T038 Security pass against FR-029: assert no corpus file causes code execution, filesystem access, network access, or an unhandled error, with the malformed and non-BibTeX fixtures as the adversarial cases (SC-008).
- [ ] T039 Full verification: `forge verify` green, coverage floors held (project 90%, patch 85%), and the whole corpus imported end to end.

---

## Dependencies

- Phase 1 blocks everything.
- Phase 2 blocks every story. T002 blocks T006; T003 and T004 block every acceptance assertion.
- Within a story, test tasks precede the implementation task that turns them green.
- US1 establishes the tables and the mapping that US2, US3 and US4 extend. US2 through US4 are
  independent of one another and could run in either order once US1 lands.
- Phase 7 runs at convergence, after the stories.

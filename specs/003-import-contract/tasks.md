# Tasks: A Standard Contract for Importing Bibliographic Files

**Input**: Design documents in `specs/003-import-contract/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/importers.md](contracts/importers.md)

**Tests**: Required. Article I is Test-First, so within every story the test task comes before the
behaviour it describes and is expected to fail when written.

**Organization**: Grouped by user story. Phases 1 and 2 are shared and block everything; after
them US1, US2, and US3 are independently implementable and independently testable.

## BibFormat: `[ID] [P?] [Story] Description`

- **[P]** — can run in parallel with others marked `[P]` in the same phase (different files, no
  shared dependency)
- **[Story]** — the user story the task serves

---

## Phase 1: Setup

**Purpose**: The package skeleton, so every later task has somewhere to land.

- [x] T001 Create `literature/importers/__init__.py` and `tests/test_importers/__init__.py` as empty modules, mirroring the source tree per the architecture constraints.

---

## Phase 2: Foundational (blocking)

**Purpose**: The vocabulary every story reports through. Nothing story-specific can start until
this is done, because all three describe their outcomes with it.

- [x] T002 [P] Write `tests/test_importers/test_results.py`: `Outcome` has exactly `CREATED`, `SKIPPED`, `FAILED` and its labels are translatable; `EntryResult` holds outcome, index, handle, item, reason; the invariant that `reason` is set if and only if the outcome is `FAILED`; `ImportResult` exposes `entries`, `dry_run`, and the `created`/`skipped`/`failed`/`ok` views over them.
- [x] T003 [P] Write `tests/test_importers/test_exceptions.py`: `SkipEntry`, `EntryError`, `ParseError`, `UnknownFormat`, `FormatAlreadyRegistered` exist, carry their messages, and each message is translatable.
- [x] T004 Implement `literature/importers/results.py` — `Outcome` as a `TextChoices` (translatable labels, consistent with `literature/choices.py`), plus frozen `EntryResult` and `ImportResult` per [data-model.md](data-model.md). T002 goes green.
- [x] T005 Implement the exception hierarchy in `literature/importers/exceptions.py`, every message wrapped in `gettext_lazy` (FR-022). T003 goes green.

**Checkpoint**: the reporting vocabulary exists and is tested. US1, US2, and US3 can now proceed in
any order.

---

## Phase 3: User Story 1 — Import a file and learn what happened to every entry (P1)

**Goal**: One documented call takes a file and a format and returns one outcome per entry, with
failures carrying a reason and nothing dropped in silence.

**Independent test**: A test-only format yielding a known mix of good, unreadable, skippable, and
part-way-failing entries. The catalogue ends up holding exactly the good ones and the result
accounts for every entry in the file.

- [x] T006 [US1] Write `tests/test_importers/conftest.py`: the test-only format and its variants as fixtures — all-good, one-entry-fails-at-conversion, one-entry-fails-at-save (violate the `(item, type)` unique constraint on `ItemIdentifier`, which is a real `IntegrityError` and not a `ValidationError`; see research.md R2), one-entry-skipped, unparseable-file, empty-file, and one that yields entries lazily so consumption can be observed.
- [x] T007 [P] [US1] Write `tests/test_importers/test_base.py`: `BibFormat` cannot be instantiated without `parse` and `to_csl_json`; `handle_for` defaults to `None`; a subclass supplying all three works.
- [x] T008 [US1] Implement `literature/importers/base.py` — the `BibFormat` abstract base class and the `Entry` record per [data-model.md](data-model.md). The class exposes `parse`, `to_csl_json`, and `handle_for` and nothing else, so a format has no route to the stage that builds an `Item` (FR-003); test that no such hook exists rather than only that the three do. T007 goes green.
- [x] T009 [US1] Write `tests/test_importers/test_runner.py`, the reporting half: one result per entry in source order each appearing once (FR-007, SC-002); outcomes drawn only from the vocabulary (FR-008); every failure carries a reason (FR-010); every result carries its index and, where the format offers one, the source handle (FR-009, SC-009); a skipped entry is distinguishable from a failed one (FR-011); **every failure appears in the returned result and not only in the log** — assert against the result with logging captured and silenced, so a run that reports solely through `logger` fails the test (FR-013, SC-005); a caller reading only the result learns every entry's fate and every failure's reason without consulting anything format-specific (SC-001).
- [x] T010 [US1] Write `tests/test_importers/test_runner.py`, the resilience half, treating file content as untrusted throughout (FR-023) — including that `import_file` accepts an already-open file object and never opens a path itself, so nothing in a file can steer what gets read: a failing entry does not stop the ones after it (FR-012, SC-003); an entry failing part-way leaves nothing at all behind, asserted by counting `Item`, `ItemName`, `ItemDate`, and `ItemIdentifier` rows (FR-006, SC-008); an unparseable file returns a one-entry failed result rather than raising (FR-014, SC-007); an empty file is a successful import of nothing; a file in an unexpected encoding is reported, not stored corrupted.
- [x] T011 [US1] Implement `literature/importers/runner.py` — `import_file` as the single documented entry point (FR-001), identical for every format and callable without reference to the file's syntax (FR-005), driving the four fixed stages (FR-002), a `transaction.atomic()` savepoint per entry with the failure caught **outside** the block, and `from_csl_json` called per entry. `literature/converters.py` is **not** modified (FR-004). T009 and T010 go green.
- [x] T012 [US1] Write and satisfy the consumption test: a format yielding lazily is consumed one entry at a time rather than drained before the first is stored (FR-024, US1 scenario 8). Assert against the generator's observed progress, not against timing.
- [x] T013 [US1] Assert `from_csl_json` and `from_csl_json_list` are untouched: the existing `tests/test_converters.py` still passes unchanged, and a test pins that `from_csl_json_list` keeps skipping invalid items with a warning (FR-004, decision D5).

**Checkpoint**: US1 is independently deliverable. A caller can import a file by handing over a
format and learn what happened to every entry.

---

## Phase 4: User Story 2 — Rehearse an import without changing anything (P2)

**Goal**: The same call, run as a rehearsal, reports every outcome and writes nothing.

**Independent test**: Import the same file twice, once as a rehearsal and once in earnest, and
assert the reported outcomes match while the catalogue is untouched after the rehearsal.

- [x] T014 [US2] Write `tests/test_importers/test_dry_run.py`: a dry run over a file of good entries reports them created and leaves the row counts for `Item` and all three related models unchanged (FR-015, SC-004); a failing entry's reason appears identically in a dry run (FR-015); `result.dry_run` says which mode ran (FR-016); the outcomes of a dry run and the equivalent real run over the same file match (US2 scenario 4); a dry run's entry results carry no `item`, per plan.md.
- [x] T015 [US2] Implement the dry-run path in `literature/importers/runner.py` — an outer `transaction.atomic()` entered only when `dry_run` is true, with `set_rollback(True)` before leaving it. Same code path as a real run, no rehearsal-specific branch beyond the transaction. T014 goes green.

**Checkpoint**: US2 is independently deliverable on top of US1.

---

## Phase 5: User Story 3 — Discover which formats are available (P3)

**Goal**: Formats register under a name, the registered set can be enumerated, and an import can be
run by naming one.

**Independent test**: Register a test-only format, assert it is enumerated, run an import by name,
and assert an unregistered name is rejected with a message naming what is registered.

- [x] T016 [US3] Write `tests/test_importers/test_registry.py`: a registered format is enumerated by `available_formats` (FR-017) and can be named in `import_file` (FR-018); an unregistered name raises `UnknownFormat` whose message names the registered formats (FR-019); registering a taken name raises `FormatAlreadyRegistered` rather than replacing the first (FR-020); `register` returns its argument so it works as a decorator; `available_formats` returns a mapping a caller cannot mutate. Use a fixture that restores the registry afterwards, so registration in one test cannot leak into another.
- [x] T017 [US3] Implement `literature/importers/registry.py` — `register`, `get_format`, `available_formats`. T016 goes green.
- [x] T018 [US3] Accept a registered name in `import_file`'s `format` argument, resolving it through `get_format`. `UnknownFormat` reaches the caller rather than becoming a failed result, since it is programmer error and not file content (contracts/importers.md).

**Checkpoint**: all three stories complete.

---

## Phase 6: Polish and public surface

**Purpose**: The parts that make it a public API rather than four modules that happen to work.

- [x] T019 Re-export the public surface from `literature/importers/__init__.py`, so every public name is reachable from the `literature` namespace (FR-021, Article X) — `import_file`, `BibFormat`, `Outcome`, `EntryResult`, `ImportResult`, `register`, `get_format`, `available_formats`, and the five exceptions — with `__all__`. `literature/__init__.py` stays empty, per research.md R3. Test that every name in `__all__` imports.
- [x] T020 [P] Add the new vocabulary to `CONTEXT.md` — format, entry, outcome, import result — and extend *Synonyms to avoid* with "provider" (use **format**) and "record" for a source-side entry (use **entry**). FR-025, decision D7.
- [x] T021 [P] Update `README.md` with an import section drawn from [quickstart.md](quickstart.md), and add a `CHANGELOG.md` entry. Article VI, both in this PR.
- [x] T022 Write the end-to-end smoke path in `tests/test_importers/test_smoke.py`: register a format, enumerate it, dry-run a mixed file, import it for real, and assert the catalogue and the two results agree. This is the one test that exercises all three stories together, and it is the standing demonstration that a new format needs only the two stages plus registration (SC-006).
- [x] T023 Run `forge verify` and fix anything red: ruff, mypy, deptry, the full suite, and `makemessages` clean over the package source (Article VIII, quality bar). Confirm coverage has not decreased.

---

## Dependencies

```text
T001 ──> T002,T003 ──> T004,T005 ──┬──> US1: T006 ──> T007,T008 ──> T009,T010 ──> T011 ──> T012,T013
                                   ├──> US2: T014 ──> T015          (needs T011)
                                   └──> US3: T016 ──> T017 ──> T018 (T018 needs T011)
                                                                     all ──> T019 ──> T020,T021,T022 ──> T023
```

- **Phase 2 blocks everything.** All three stories report through `Outcome` and `EntryResult`.
- **US2 and US3 both need the runner from T011**, so US1 lands first in practice even though the
  stories are independently *testable*. This is sequencing, not coupling: neither story changes
  US1's behaviour, and each can be reverted without touching it.
- **T020, T021 and T022 are parallel** once the code is complete.

## Parallel opportunities

- T002 and T003 (different test files, no shared code).
- T007 alongside T009 and T010 (different test files).
- T020 and T021 (documentation, no code).

## Notes

- **`literature/converters.py` is not modified by any task.** If a task appears to need it changed,
  that is a design deviation and belongs in `decisions.md` before the change, not after.
- **No migration is created by any task.** No model changes, so `makemigrations --check` must stay
  clean; a migration appearing is a signal something was misread.
- Every user-facing string added anywhere in this feature is wrapped in `gettext_lazy` (FR-022,
  Article VIII, non-negotiable).

---

## Phase 7: Maintainer review rework (2026-08-04)

Three changes agreed in session after the maintainer read the branch. See the *Refinements*
section of [spec.md](spec.md) for the reasoning. Task numbering continues; nothing above is
renumbered.

- [x] T024 Rename `Format` to `BibFormat` throughout — class, imports, `__all__`, tests, docstrings, `CONTEXT.md`, README, CHANGELOG, and the spec artifacts that name it. Mechanical, but it must be complete: a stale `Format` in a docstring is the kind of thing that outlives three releases.
- [ ] T025 Write the tests for the split workflow in `tests/test_importers/test_base.py`: each of `import_file`, `import_entries`, `import_entry` and `get_result` is callable on its own; overriding `import_entry` in a subclass changes only that step and the rest of the workflow still runs; overriding `get_result` changes the returned report. These tests are the point of the split — they prove the hooks are genuinely usable, not just present.
- [x] T026 Move the workflow from `runner.py` onto `BibFormat` as ordinary overridable methods, and delete `runner.py`. **No `@final`, no guard against overriding anything** — the base class gets the job done for a format that implements the two required stages, and a developer who replaces a step is doing so deliberately. Split per the maintainer's shape: `import_file` (opens the dry-run transaction, drives the rest), `import_entries` (the loop over parsed entries), `import_entry` (one entry, its savepoint, and its outcome), `get_result` (builds the `ImportResult`), plus small `entry_created` / `entry_skipped` / `entry_failed` helpers so a subclass can change how an outcome is reported without reimplementing the loop. **The `except` must stay outside the per-entry `transaction.atomic()` block** — catching inside marks the whole transaction unusable (research.md R2).
- [x] T027 Write the tests for settings-declared formats in `tests/test_importers/test_config.py`: a format listed in `LITERATURE = {"BIB_FORMATS": [...]}` is enumerated and can be named in an import; an unconfigured name fails with an error naming what is configured; an unset setting yields the shipped defaults; an entry that does not resolve, or resolves to something that is not a `BibFormat` subclass, fails at first read naming the offending entry. Use `override_settings` so no test leaks configuration into another.
- [x] T028 Replace `registry.py` with settings resolution: read `LITERATURE["BIB_FORMATS"]`, import each path, key by `name`. Keep `available_formats()` as the read side. Delete `register`, `get_format`'s registry lookup, and `FormatAlreadyRegistered`. Cache the resolved mapping and invalidate it on `setting_changed`, so tests and `override_settings` behave. Delete `tests/test_importers/test_registry.py`.
- [ ] T029 Rewrite ADR-0006 and ADR-0007. Both currently claim every format inherits the guarantee and none can weaken it, which the overridable workflow makes false. They describe what the base class does **by default**; say that, and say what a subclass overriding the relevant hook takes on. Do not delete either — the decisions stand, only their reach changes.
- [ ] T030 Update the documentation to match: `CONTEXT.md` (format entry, the configured-set note), `README.md` (the import section and a settings example), `CHANGELOG.md` (registration becomes configuration), `data-model.md`, `contracts/importers.md`, `quickstart.md`, and `plan.md`'s module tree and structure decision. Delete D17 from `decisions.md` — the import-timing hazard it records does not exist once formats come from settings — and add a decision recording the three changes and their reasoning.
- [ ] T031 Full verify: `poetry run pytest`, ruff, mypy, deptry, `makemigrations --check`, and `makemessages` clean. Coverage must not decrease.

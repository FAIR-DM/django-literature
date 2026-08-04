# Progress: FS-003 — A standard contract for importing bibliographic files

Append-only. Each entry is written at the moment the event happens, not reconstructed afterwards.

| When (UTC) | Stage | Event | Detail |
|---|---|---|---|
| 2026-08-03T19:48:14Z | S2 | **Spec gate: APPROVED** | Approved in session by the maintainer with no revisions requested. Review surface was epic #21 (promoted in place), stories #25/#26/#27, and `spec.md` on branch `003-import-contract`. Draft PR #29, bot-authored. `stage-exit S2` green on clarifications, issue titles, and PR title. |
| 2026-08-03T19:48:14Z | S3 | Stage entered | Planning begins. |
| 2026-08-03T19:55:00Z | S3 | Plan complete | research.md (5 questions, R2 verified by running it), plan.md, data-model.md, contracts/importers.md, quickstart.md, tasks.md (23 tasks across 6 phases), feature-state.json. Constitution check clean on both passes. |
| 2026-08-03T19:55:00Z | S3 | Analyze | Cross-artifact scan found two coverage gaps (FR-013 and FR-023 named in no task) and one structural drift (`exceptions.py` in tasks.md, absent from plan.md's tree). All three fixed; every FR-001..025 and SC-001..009 now named by at least one task. No CRITICAL findings. |
| 2026-08-03T19:55:00Z | S3 | **Plan gate: notified** | Veto window, not a blocking gate. Proceeding to S4. |

## 2026-08-03T20:05:00Z · Implementer US1 · T006 (`tests/test_importers/conftest.py`)

**Did**: Test-only `Format` factories — `make_echo_format` (raw dicts tagged by `kind`: good/skip/entry_error, plus an `on_yield` hook for T012), `make_unparseable_format` (a generator whose first `next()` raises `ParseError`), and `DuplicateCustomIdentifier` + `bypass_identifier_validation` for the IntegrityError scenario (see decisions.md D11).

**Verified**: `poetry run pytest tests/test_importers/ -q --no-cov` — collection failed with `ModuleNotFoundError: No module named 'literature.importers.base'` (right reason: `base.py` doesn't exist yet).

**Next**: T007/T008 — `Format` ABC.

**Watch**: `import_file` takes `type[Format]`, not an instance, so every factory here returns a *class* with entries closed over — matches the registry's return type for US3 later.

## 2026-08-03T20:10:00Z · Implementer US1 · T007 (`tests/test_importers/test_base.py`)

**Did**: ABC-enforcement tests (missing `parse`/`to_csl_json` individually and together refuse instantiation), `handle_for` default/override, a full subclass working end to end, and — per the task's explicit instruction to test the absence of extra surface, not just the presence of the three — `vars(Format)` public-name enumeration asserting the class exposes exactly `{parse, to_csl_json, handle_for}` (FR-003). `Entry` immutability/defaults/field tests included.

**Verified**: `poetry run pytest tests/test_importers/test_base.py -q --no-cov` — same `ModuleNotFoundError` as T006 (still no `base.py`).

**Next**: T008 implementation.

**Watch**: none.

## 2026-08-03T20:12:00Z · Implementer US1 · T008 (`literature/importers/base.py`)

**Did**: `Format` ABC (`parse`, `to_csl_json` abstract; `handle_for` defaults to `None`) and frozen `Entry` dataclass, per data-model.md.

**Verified**: `poetry run pytest tests/test_importers/ -q --no-cov` → 52 passed. Full suite `poetry run pytest -q --no-cov` → 385 passed. `ruff check literature tests` clean, `ruff format --check` clean, `makemigrations --check --dry-run` → no changes.

**Next**: T009/T010 runner tests.

**Watch**: none.

## 2026-08-03T20:25:00Z · Implementer US1 · T009–T010 (`tests/test_importers/test_runner.py`)

**Did**: `TestReporting` (FR-007..013, SC-001, SC-002, SC-005, SC-009 — ordering/completeness, outcome vocabulary, reason presence, index+handle carry-through, skip-vs-fail distinction, `caplog`-silenced-logging still leaves the failure in the result) and `TestResilience` (FR-006, FR-012, FR-014, FR-023, SC-003, SC-007, SC-008 — file passthrough via identity check, a failing entry doesn't stop the rest, partial-entry atomicity from *both* a `ValidationError` and a genuine `IntegrityError`, unparseable file → one failed entry, empty file → success, encoding failure reported not stored, truncated-file mid-stream `ParseError` recovers prior entries).

**Verified**: `poetry run pytest tests/test_importers/test_runner.py -q --no-cov` — collection failed, `ModuleNotFoundError: No module named 'literature.importers.runner'` (right reason).

**Next**: T011 implementation.

**Watch**: the two partial-failure tests (`ValidationError` via a malformed DOI, `IntegrityError` via `DuplicateCustomIdentifier` + `bypass_identifier_validation`) are the direct test-level proof of research.md R2's finding — see decisions.md D11 for why the IntegrityError one needs that fixture at all.

## 2026-08-03T20:35:00Z · Implementer US1 · T011 (`literature/importers/runner.py`)

**Did**: `import_file(file, format)` — no `dry_run`, no `format: str` (explicitly out of scope for T011 per the task brief; US2/US3 add them later). Four fixed stages: iterate `format.parse(file)` inside a `try/except ParseError` (so entries recovered before a mid-stream parse failure keep their results), convert via `to_csl_json` catching `SkipEntry` → `SKIPPED` and `(EntryError, ValidationError)` → `FAILED`, then `from_csl_json` inside a per-entry `transaction.atomic()` with `(ValidationError, IntegrityError)` caught **outside** that block (research.md R2) → `FAILED`, else `CREATED`. `literature/converters.py` untouched.

**Verified**: `poetry run pytest tests/test_importers/ -q --no-cov` → 69 passed, first run, no fix-up cycles. Full suite → 402 passed. `ruff check` initially flagged `A002` (`format` shadows a builtin, per the contract's own naming) — suppressed with an inline `# noqa: A002` rather than renaming the parameter away from the documented contract signature; `ruff format` reformatted one line. Both clean after. `makemigrations --check --dry-run` → no changes.

**Next**: T012 lazy-consumption test.

**Watch**: none.

## 2026-08-03T20:45:00Z · Implementer US1 · T012 (lazy consumption test)

**Did**: `TestLazyConsumption` in `test_runner.py` — `on_yield` records `Item.objects.count()` at the instant each raw entry is produced; asserts the observed sequence is `[0, 1, 2]` for three good entries, which only holds if each entry is stored before the next is requested from the generator (an eager `list(fmt.parse(file))` would observe `[0, 0, 0]`).

**Verified**: `poetry run pytest tests/test_importers/test_runner.py -q --no-cov -k Lazy` → 1 passed, first run (runner's `for raw in fmt.parse(file):` was already lazy by construction). Full suite → 403 passed. Ruff/format clean.

**Next**: T013.

**Watch**: none.

## 2026-08-03T20:50:00Z · Implementer US1 · T013 (`tests/test_importers/test_converters_unchanged.py`)

**Did**: New test pinning that `from_csl_json_list` still skips invalid items via `logger.warning` (decision D5) — the existing `tests/test_converters.py` already covered the skip-on-error *return value* but not the warning. `tests/test_converters.py` and `literature/converters.py` left untouched (`git status` on both is clean).

**Verified**: `poetry run pytest tests/test_importers/test_converters_unchanged.py -q --no-cov` → 1 passed. Full suite `poetry run pytest -q --no-cov` → 404 passed. `ruff check literature tests` clean, `ruff format --check literature tests` clean, `makemigrations --check --dry-run --settings=tests.settings` → no changes. `git status --short tests/test_converters.py literature/converters.py` → empty (no modifications).

**Next**: US1 (T006-T013) complete. US2 (dry run, T014-T015) and US3 (registry, T016-T018) are next in tasks.md, out of this story's scope.

**Watch**: none — all 8 tasks done, budget not exhausted on any of them (each went green within 1 implementation attempt).

## 2026-08-04T07:35:00Z · Implementer US2 · T014 (`tests/test_importers/test_dry_run.py`)

**Did**: `TestDryRun` — created entries reported but row counts (`Item`, `ItemName`, `ItemDate`, `ItemIdentifier`) unchanged (FR-015, SC-004); a failing entry's reason identical to a real run; `result.dry_run` true/false per mode (FR-016); outcomes/reasons/handles match between a dry run and the equivalent real run over the same file (US2 scenario 4); a dry run's created entries carry `item=None` (plan.md, data-model.md); a failing entry inside a dry run still lets the rest through, both for an ordinary `EntryError` and for a genuine `IntegrityError` via the existing `bypass_identifier_validation` fixture — exercising the per-entry savepoint nested inside the outer dry-run transaction (research.md R2).

**Verified**: `poetry run pytest tests/test_importers/test_dry_run.py -q --no-cov` — 7 failed, all `TypeError: import_file() got an unexpected keyword argument 'dry_run'` (right reason — `runner.py` had no `dry_run` parameter yet).

**Next**: T015 implementation.

**Watch**: reused `make_echo_format` and `DuplicateCustomIdentifier`/`bypass_identifier_validation` from `conftest.py` rather than adding a second set of format fixtures, per the story brief.

## 2026-08-04T07:45:00Z · Implementer US2 · T015 (`literature/importers/runner.py`)

**Did**: Added `dry_run: bool = False` to `import_file`. The existing four-stage loop is unchanged; it is now wrapped in `transaction.atomic() if dry_run else contextlib.nullcontext()` so there is exactly one copy of the loop rather than two (decision D14), with `transaction.set_rollback(True)` called just before leaving that block on a dry run. The one `if dry_run` inside the loop sets a `CREATED` entry's `item` to `None` rather than the real (in-memory, about-to-be-rolled-back) `Item` — decision D13 explains why this is not the rehearsal-specific branch the task brief warns against: `from_csl_json` still runs unconditionally, the branch only decides what is handed back. `ImportResult(entries=entries, dry_run=dry_run)` now threads the flag through (`ImportResult.dry_run` already existed in `results.py`, T004; it was just never set to anything but its `False` default before this).

**Verified**: `poetry run pytest tests/test_importers/test_dry_run.py -q --no-cov` → 7 passed, first attempt, no fix-up cycles. `poetry run pytest tests/test_importers/ -q --no-cov` → 77 passed. Full suite `poetry run pytest -q --no-cov` → 410 passed (baseline before this story was reconfirmed at 403, not the 404 the T013 entry above recorded — re-ran the baseline today and got 403 both before and, mechanically, 403 + 7 = 410 after; not investigated further since it is outside T014/T015's scope). `ruff check literature tests` → all checks passed. `ruff format --check literature tests` → 33 files already formatted. `poetry run python -m django makemigrations --check --dry-run --settings=tests.settings` → no changes detected.

**Next**: US2 (T014-T015) complete. US3 (registry, T016-T018) is next in tasks.md, out of this story's scope.

**Watch**: decisions.md D13 and D14 record the two non-obvious calls in this task — the `item=None` branch and the `contextlib.nullcontext()` swap — plus a restated pointer (not a new finding) to research.md R5's long-open-transaction caveat for a future format's dry run at scale. Raising this in `concerns` for the review gate as requested by the task brief, not fixing it here: it is a caller-side sizing question, not a defect in this mechanism.

## 2026-08-04T08:05:00Z · Review US2 · `tests/test_importers/test_dry_run.py`

**Did**: Verified T014/T015 independently — re-ran the full suite (410 passed), ruff, format and
`makemigrations --check` from a clean checkout of the story branch, and tamper-checked the mechanism
by deleting `transaction.set_rollback(True)` (3 of the 7 dry-run tests fail, the right 3). Read the
diff against the contract: the signature, the stage order, the outer-block-only-on-dry-run rule and
the `item=None` rule all match `contracts/importers.md` and `data-model.md` as written.

Added `TestDryRunOutsideATestTransaction` (decision D15) — every committed dry-run test runs under
non-transactional `django_db`, which exercises only Django's savepoint branch. A caller in
autocommit takes the other branch. Two tests under `django_db(transaction=True)` now cover it: a dry
run stores nothing, and a real run still commits. Confirmed the first fails when
`set_rollback(True)` is removed.

**Resolved the baseline discrepancy T015 flagged** (403 vs the 404 recorded at T013): not a lost
test. The US1 review commit `a489550` dropped the unused `Entry` dataclass with its 3 tests and
added 2 regression tests for the `EntryError`-from-`parse` fix — net −1, so 404 → 403. Nothing to
investigate.

**Verified**: full suite → 412 passed. `ruff check` clean, `ruff format --check` → 33 files already
formatted. `makemigrations --check --dry-run` → no changes.

**Next**: merge US2 into `003-import-contract`, then US3 (registry, T016–T018).

**Watch**: `django_db(transaction=True)` flushes tables rather than rolling back, so those two tests
are slower than the rest and must not grow into a habit — they exist because this one guarantee
cannot be proved any other way.

## 2026-08-04T08:30:00Z · Implementer US3 · T016 (`tests/test_importers/test_registry.py`)

**Did**: Wrote `test_registry.py` against FR-017 through FR-020: a registered format is enumerated
by `available_formats` and resolvable by name through `import_file` (`TestImportByName`); an
unregistered name raises `UnknownFormat` naming what is registered; registering a taken name raises
`FormatAlreadyRegistered` and the first registration still resolves afterwards; `register` returns
its argument (decorator use); `available_formats()` refuses mutation (`TypeError` on item
assignment). Added an autouse `_isolated_registry` fixture that saves and restores
`registry._registry` around every test, per the story brief's warning that a per-test
`try/finally` still leaks a registration left behind by a failed assertion. Reused
`make_echo_format` from `conftest.py` rather than adding a second set of format fixtures.

**Verified (confirmed red for the right reason)**:
```
poetry run pytest tests/test_importers/test_registry.py -q --no-cov
```
→ collection error: `ModuleNotFoundError: No module named 'literature.importers.registry'`. The
module does not exist yet (T017), not a typo in the test.

**Next**: T017 implements `literature/importers/registry.py` to turn this green.

## 2026-08-04T08:50:00Z · Implementer US3 · T017 (`literature/importers/registry.py`)

**Did**: Added `register`, `get_format`, `available_formats` — a module-level `dict[str,
type[Format]]`, matching the shape of `base.py`/`exceptions.py`/`results.py` already in the
package. `register` raises `FormatAlreadyRegistered` (with a `gettext_lazy` message; its
constructor was not touched, per the story brief) rather than replacing an existing entry.
`get_format` raises `UnknownFormat(name, available=_registry.keys())`, reusing the message-building
already written for that exception in T002. `available_formats` wraps the live dict in
`types.MappingProxyType`, so the read view is genuinely read-only rather than read-only by
convention, and stays live rather than a stale copy.

**Verified**:
```
poetry run pytest tests/test_importers/test_registry.py -q --no-cov
```
→ 6 of 9 passed (`TestRegister`, `TestGetFormat`). The 3 `TestImportByName` cases still fail —
`import_file` does not yet resolve a `str`, which is T018.

**Next**: T018 wires `get_format` into `import_file`.

## 2026-08-04T09:15:00Z · Implementer US3 · T018 (`literature/importers/runner.py`)

**Did**: `format: type[Format] | str` per contracts/importers.md. A `str` is resolved through
`registry.get_format` before `fmt = format_class()` and before the outer transaction opens, so an
`UnknownFormat` reaches the caller untouched — nothing in `import_file` catches it, matching
contracts/importers.md's "reaches the caller" note for programmer error. A `Format` subclass still
passes straight through, unchanged from before. Updated the module docstring, which previously said
this lookup "is not implemented here — it belongs to US3". The four-stage loop, the per-entry
savepoints, and the dry-run wrapper (D13, D14) were not touched.

Also set `ImportResult.format_name` to the name used on a by-name run (decision D16 — the task
brief did not ask for this, but data-model.md's `ImportResult` table already documented the field
and nothing before this story could set it).

**Verified**:
```
poetry run pytest tests/test_importers/test_registry.py -q --no-cov   → 9 passed
poetry run pytest tests/test_importers/ -q --no-cov                    → 88 passed
poetry run pytest -q --no-cov                                          → 421 passed (412 baseline + 9 new)
poetry run ruff check literature tests                                 → all checks passed
poetry run ruff format --check literature tests                        → 35 files already formatted
poetry run python -m django makemigrations --check --dry-run --settings=tests.settings → no changes detected
```

**Next**: US3 (T016–T018) complete — all three stories now implemented. Phase 6 (T019–T023: public
re-exports, CONTEXT.md/README/CHANGELOG, smoke test, `forge verify`) is next in tasks.md, out of
this story's scope.

**Watch**: decisions.md D16 records the `format_name` call for the review gate. Also worth a note
for whoever does T019: `literature/importers/registry.py` is not yet re-exported from
`literature/importers/__init__.py` (that re-export is T019's job, not this story's — `__init__.py`
is explicitly out of scope per the story brief), so `register`/`get_format`/`available_formats` are
only reachable via the submodule import until then.

## Phase 6 — T019–T023 (polish), reviewer

**T019** — `literature/importers/__init__.py` re-exports the whole contract: `import_file`,
`Format`, `Outcome`, `EntryResult`, `ImportResult`, `register`, `get_format`, `available_formats`,
and all six exceptions including the `ImporterError` root, with `__all__` (FR-021, Article X).
`literature/__init__.py` stays empty per research.md R3. `tests/test_importers/test_public_surface.py`
holds the documented surface as data and checks it in both directions, so a name added to a
submodule and never exported fails here rather than at whoever tries to import it. Tamper-checked:
dropping `register` from the re-export turns three of its tests red.

**T022** — `tests/test_importers/test_smoke.py`. A format written the way a real one will be —
two stages, an optional handle, a registration, nothing else — then the whole contract used as
`quickstart.md` describes it: enumerate, rehearse, import, and check the catalogue agrees with both
results. The file it reads carries all four outcomes, with the two failures arriving by different
routes: one the format itself rejects (`EntryError`), one the CSL JSON conversion rejects
(`ValidationError`). This is the standing demonstration of SC-006.

The registry isolation fixture moved from `test_registry.py` to the package `conftest.py` as an
autouse fixture, since the smoke test needs it too and a duplicated copy is one a new test file can
forget.

**T023** — full verify, all green:
```
poetry run pytest -q                                                    → 452 passed, 98% coverage
poetry run ruff check literature tests                                  → all checks passed
poetry run ruff format --check literature tests                         → 37 files already formatted
poetry run mypy literature                                              → no issues in 14 source files
poetry run deptry .                                                     → no dependency issues
poetry run python -m django makemigrations --check --dry-run            → no changes detected
```
`literature/importers` is at 99% (the two misses are the abstract `raise NotImplementedError`
bodies in `base.py`).

**Not run**: `makemessages`. GNU gettext is not installed in this environment
(`CommandError: Can't find msguniq`) and no CI job runs it either, so Article VIII was checked by
reading instead: every message the contract produces is either wrapped in `gettext_lazy`
(`exceptions.py`, `registry.py`, `Outcome` labels) or is `str(exc)` of a message the format
supplied. Log lines and the two `ValueError`s guarding `EntryResult` construction are internal and
deliberately untranslated. Flagged rather than claimed green.

**Next**: convergence and review, then the merge gate.

## Convergence review

Three independent reviews of the finished branch, on separate lenses: requirement-by-requirement
conformance, an adversarial defect hunt with probes, and standards and documentation accuracy. They
converged on the same defect from three directions, which is the one worth reading about.

**`import_file` could still be escaped.** The per-entry net named `SkipEntry`, `EntryError`,
`ValidationError` and `IntegrityError`. `from_csl_json` raises none of those for a CSL JSON dict
whose *shape* is wrong rather than whose values are — `{"issued": "2020"}` calls `.get()` on a
string and raises `AttributeError`. Reproduced before touching anything: three entries, the middle
one carrying a string date, and `import_file` raised, entry one already committed, entry three never
attempted, no `ImportResult` returned. FR-013, FR-014 and FR-023 failing at once, in the case the
contract exists for, and unfixable from a format because FR-003 gives it no route to the stage that
fails. Both blocks now catch `Exception`. Recorded as D18, with what that costs and what keeps it
honest.

Five more, each reproduced with a probe first and each now covered by a test that fails without its
fix:

- `handle_for` shared a block with `to_csl_json`, so a `SkipEntry` out of it reported a good record
  as deliberately skipped and stored it nowhere (D19).
- A dry run under a `DATABASE_ROUTERS` setup committed every row and reported that it had stored
  nothing, because the transaction named the default alias and the writes did not (D20).
- A failure reason was the `repr` of the list inside a `ValidationError`, brackets and all.
- An exception raised with no message gave `str(exc) == ""`, which is not `None`, so it passed the
  invariant meant to stop exactly that and printed as a blank line.
- `SkipEntry` from `parse` escaped, and `ParseError` from `to_csl_json` was filed one index past the
  entry that raised it, leaving that entry with no result at all.

**Two tests were replaced rather than kept.** The one asserting the `UnknownFormat` message is
translatable passed just as well against a bare f-string. The public-surface guard derived every
assertion from a hand-written list, so a name added to a submodule and left out of both that list
and `__all__` — the omission it exists for — sailed through. Both now fail when tampered with.

**Coverage at the transaction level a caller actually runs at.** The resilience and atomicity tests
all ran under non-transactional `django_db`, where the per-entry block is a savepoint nested in the
test's own transaction. In autocommit it is outermost and rolls back through a different branch.
Both behave the same, which was checked rather than assumed.

**Verified**: 494 passing, ruff, ruff format, mypy, deptry and `makemigrations --check` all clean.

## 2026-08-04T12:45:00Z · Review panel · full diff

**Reviewer**: independent subagent, clean context, refutation brief, ~4700 lines of diff against spec.md,
contracts/importers.md and the constitution.

**Verdict**: approve. No critical or high findings. One low: `register()` did not check that a `Format`
subclass had implemented its abstract stages, so a half-written format registered cleanly and failed
later inside `import_file` with a raw `TypeError`, outside the documented exception vocabulary.

**Fixed**: reproduced with a probe first (`HalfFormat` with no `to_csl_json` registered and was
enumerable). `register()` now rejects any class with outstanding `__abstractmethods__`, naming them.
Test `test_a_format_missing_a_stage_is_refused_and_names_the_stage`, tamper-checked by reverting the
guard — the new test goes red alone, the other 13 stay green. Recorded as D21.

**Also at convergence**: `forge verify` conformance was red on the Article X mirror rule for
`test_dry_run.py`, `test_public_surface.py` and `test_converters_unchanged.py`. Each folded into the
module of its subject with its tests unchanged; 495 passed either side of the move (D23). Two
`tamper-check` flags on `tests/settings.py` and `tests/test_documentation.py` reviewed and approved as
additive (D22).

**Verified**: `forge verify --base origin/main` → conformance, lint, typecheck, test, build all pass.
`forge stage-exit --stage S6` → green on all five checks. CI green on `15cd7f9` across four
Python/Django combinations plus code quality and security scan.

## 2026-08-04T13:30:00Z · Implementer · Phase 7 rework begins (T024)

**Did**: Mechanical rename `Format` → `BibFormat` across `literature/importers/{base,runner,registry,__init__}.py`, `tests/test_importers/{conftest,test_base,test_runner,test_registry,test_smoke}.py`, and the spec artifacts (`spec.md`, `plan.md`, `tasks.md`, `data-model.md`, `decisions.md`, `contracts/importers.md`, `quickstart.md`) via a word-boundary substitution (`\bFormat\b`), which left `FormatAlreadyRegistered` and unrelated hits (`tests/data/csl-typeMap.xml`'s CSL field label, `docs/adr/0002`'s prose "Format validation") untouched. `progress.md`'s own history (append-only) is not rewritten — those entries describe what was literally true when written.

**Verified**: `poetry run pytest -q --no-cov` → 495 passed. `ruff check literature tests` → 2 auto-fixed (import/`__all__` sort order in `__init__.py` and `test_smoke.py`, alphabetical placement of `BibFormat`), 0 remaining. `ruff format --check` clean. `mypy` → no issues in 14 source files. Grepped `\bFormat\b` afterward and every remaining hit is justified (above).

**Next**: T025 — write the split-workflow tests in `test_base.py` against the not-yet-built `BibFormat.import_file`/`import_entries`/`import_entry`/`get_result`, expected to fail (`base.py` still only has `parse`/`to_csl_json`/`handle_for`).

**Watch**: `runner.py` and `registry.py` still exist and still work post-rename (T026/T028 delete them next) — this commit is a pure rename with no behaviour change, so the existing 495 tests are the safety net for it, unchanged.

## 2026-08-04T13:35:00Z · Implementer · T025 (`tests/test_importers/test_base.py`)

**Did**: Tests for the split workflow, written against methods that do not exist yet: `TestWorkflowMethodsAreIndividuallyCallable` (`import_entry`, `import_entries`, `get_result` and `import_file` each callable on their own, not only as part of one another), `TestOverridingImportEntry` (a subclass overriding `import_entry` changes only entry 0's outcome — the rest of the file still imports in order), `TestOverridingGetResult` (a subclass overriding `get_result` drops skipped entries from the report). `TestFormatHasNoRouteToBuildingAnItem` is left in place for now — it still holds until T026 actually adds methods to `BibFormat`, at which point it is replaced rather than deleted, per the maintainer's ruling that a route to the workflow is now deliberate, not a defect.

**Verified**: `poetry run pytest tests/test_importers/test_base.py -q --no-cov` → 6 failed (all `AttributeError: '_EchoFormat' object has no attribute 'import_entry'` / `import_entries` / `get_result` / `import_file`, the right reason), 8 passed (the pre-existing contract tests, untouched). `ruff check`/`ruff format --check` clean on the file.

**Next**: T026 — move the workflow from `runner.py` onto `BibFormat`, delete `runner.py`, make T025 green, and replace `TestFormatHasNoRouteToBuildingAnItem`.

**Watch**: `make_echo_format` returns a *class*; the overriding tests subclass its return value inline (`class SkipsTheFirstEntry(make_echo_format(entries)): ...`), which only works because the factory closes over `entries` per call rather than sharing state — confirmed already true from T006.

## 2026-08-04T13:50:00Z · Implementer · T026 (`literature/importers/base.py`, `runner.py` deleted)

**Did**: Moved the workflow onto `BibFormat` as ordinary, overridable instance methods — `import_file` (opens the dry-run transaction, drives the rest), `import_entries` (the loop over parsed entries, catching a whole-file `SkipEntry`/`ParseError`/`EntryError`/bug from the generator itself), `import_entry` (one entry: handle, convert, store inside its own savepoint), `get_result` (builds the `ImportResult`, now setting `format_name=self.name` unconditionally — D25), and `entry_created`/`entry_skipped`/`entry_failed` helpers. **No `@final`, no `__init_subclass__` guard, no abstractmethod-completeness check on the workflow methods** — exactly the maintainer's instruction. The per-entry `except` stays outside the `transaction.atomic()` block (research.md R2), unchanged from `runner.py`. Deleted `literature/importers/runner.py`.

Replaced `TestFormatHasNoRouteToBuildingAnItem` (asserted the class's public surface was exactly `{parse, to_csl_json, handle_for}` — now false by design) with `TestBibFormatRequiresOnlyTwoStages`, asserting `BibFormat.__abstractmethods__ == {"parse", "to_csl_json"}` and that the workflow methods are present, callable, and not abstract.

Merged `tests/test_importers/test_runner.py` into `test_base.py` and deleted it — Article X requires the test tree mirror the source tree (D23's precedent, applied to the same move: the workflow's tests follow the workflow). All ~45 `import_file(file, format_expr[, dry_run=True])` call sites mechanically rewritten to `format_expr().import_file(file[, dry_run=True])` (a small parenthesis-matching script, not hand-edited, to avoid transcription slips across that many sites); every assertion is untouched. Fixed the one behaviour-adjacent reference: `caplog.at_level(..., logger="literature.importers.runner")` → `"literature.importers.base"`, since that's where the workflow's logger now lives.

Minimally patched `test_registry.py` and `test_smoke.py` to stop importing the deleted `literature.importers.runner.import_file` — `test_registry.py`'s `TestImportByName` now calls `get_format("echo")().import_file(...)`, and dropped `test_result_format_name_is_none_when_a_class_was_passed_directly` (D25: the distinction it tested no longer exists). Both files are still using the old `register()`-based registry; T027/T028 replace that mechanism next, at which point `test_registry.py` is deleted outright per its own task brief.

`literature/importers/__init__.py`: dropped `import_file` from the module's re-exports (it is no longer a module-level name — D24), rewrote the module docstring's example to `get_format("bibtex")().import_file(handle)`.

**Deviation**: D24 records that there is deliberately no module-level `import_file` convenience function alongside the method — the maintainer's language ("moved onto the class," "runner.py is gone") reads as a replacement of that call shape, not an addition alongside it.

**Verified**: `poetry run pytest tests/test_importers/ -q --no-cov` → 147 passed (T025's 6 previously-red tests now green). `poetry run pytest -q --no-cov` → 504 passed (495 baseline + 6 T025 tests + 2 replacement tests in `TestBibFormatRequiresOnlyTwoStages` − 1 dropped registry test − the old 1-test `TestFormatHasNoRouteToBuildingAnItem`, net +9). `ruff check literature tests` clean. `ruff format` reformatted `test_base.py` once (blank-line spacing at the merge point), clean after. `mypy` → no issues in 13 source files (one fewer than before — `runner.py` is gone).

**Next**: T027/T028 — settings-declared formats, replacing `registry.py` with `literature/importers/config.py`.

**Watch**: `test_registry.py` and `test_smoke.py`'s registration-based tests are a known-temporary patch, not the final shape — they still call `register()` against the old in-process registry, which T028 deletes. Confirmed decisions.md D24 and D25 read correctly against the merged `test_base.py` before moving on.

## 2026-08-04T14:05:00Z · Implementer · T027 (`tests/test_importers/test_config.py`)

**Did**: Tests for settings-declared formats, written against `literature.importers.config` which does not exist yet. `TestAvailableFormats` (a configured format is enumerated; an unset setting yields the empty shipped default; the mapping is read-only; the resolved mapping is cached across calls and invalidated when the setting changes — using the `settings` fixture throughout rather than raw mutation, so `setting_changed` fires both directions). `TestImportByName` (a configured name resolves and imports; an unconfigured name fails naming what is configured, both with and without anything configured). `TestAMisconfiguredEntryFailsAtFirstRead` (a path that does not import, a path that is not a `BibFormat` subclass, and a `BibFormat` subclass missing its two required stages each fail at `available_formats()`, naming the offending entry). Three fixture formats (`ConfiguredFormat`, `NotABibFormat`, `IncompleteFormat`) live at module level rather than behind `conftest.py`'s factories, because settings resolution needs a real dotted import path and a closure-built class has none.

**Verified**: `poetry run pytest tests/test_importers/test_config.py -q --no-cov` → collection error, `ModuleNotFoundError: No module named 'literature.importers.config'` (right reason — the module doesn't exist until T028). `ruff check` auto-fixed one import-order issue (an unresolvable-yet import sorted into the third-party group instead of first-party); reordered by hand to the shape it will settle into once `config.py` exists, `ruff format --check` clean.

**Next**: T028 — implement `literature/importers/config.py`, delete `registry.py` and `test_registry.py`, and update `conftest.py`/`test_smoke.py` off the old registration mechanism.

**Watch**: the four fixture-format dotted paths (`CONFIGURED_PATH` etc.) all point into this test module itself (`tests.test_importers.test_config.*`) — `import_string` needs `tests` importable as a real package, which it already is (`pythonpath = [".", "tests"]` in pyproject.toml, `tests/__init__.py` and `tests/test_importers/__init__.py` both present since T001).

## 2026-08-04T14:20:00Z · Implementer · T028 (`literature/importers/config.py`)

**Did**: `literature/importers/config.py` replacing `registry.py` — `_resolve()` reads `LITERATURE["BIB_FORMATS"]` (defaulting to `()`, an empty tuple — Article X, no configuration needed for the built-in, currently-empty, behaviour), `import_string`s each path, and validates in order: imports cleanly → is a `BibFormat` subclass → has no outstanding `__abstractmethods__` (D26, porting D21's check across the redesign) → has a non-empty `name`. Any failure raises `ImproperlyConfigured` naming the offending path. `available_formats()` caches the resolved `MappingProxyType` (not just the underlying dict — first attempt returned a fresh proxy per call, which broke identity-based caching tests; fixed by caching the proxy itself) and `get_format(name)` raises `UnknownFormat` on a miss, same as before. A `setting_changed` receiver drops the cache when `setting == "LITERATURE"`, so `override_settings`/the `settings` fixture behave and nothing leaks between tests. Deleted `literature/importers/registry.py`, `FormatAlreadyRegistered` (exceptions.py), and `tests/test_importers/test_registry.py`.

Removed the autouse `isolated_registry` fixture from `conftest.py` — there is no more module-level mutable registry to snapshot/restore; `setting_changed` plus pytest-django's `settings` fixture now does that job. Rewired `test_smoke.py`'s `smoke_format` fixture from `register(LineFormat)` to `settings.LITERATURE = {"BIB_FORMATS": ["tests.test_importers.test_smoke.LineFormat"]}` — needs `LineFormat` reachable by dotted path, which it already is (a real module-level class, not a closure factory). Updated `test_smoke.py`'s `PUBLIC_SURFACE` dict (`get_format`/`available_formats` now point at `literature.importers.config`; `register`/`FormatAlreadyRegistered` entries removed) and `literature/importers/__init__.py`'s re-exports and module docstring to match. `UnknownFormat`'s message wording changed from "registered"/"Registered formats" to "configured"/"Configured formats" (exceptions.py), matching FR-019's already-rewritten spec wording; `test_exceptions.py` updated to match (no test asserted the literal old wording, so nothing was weakened — confirmed by reading each assertion before editing).

**Deviations**: D26 (kept the abstractmethod-completeness check across the registration→settings redesign — the defect it fixes did not go away) and D27 (a settings entry naming collision is not detected; last one wins, undetected, unlike the old registry's refusal — the mutable-shared-state hazard that justified refusing collisions does not exist when one project owns the whole list).

**Verified**: `poetry run pytest tests/test_importers/ -q --no-cov` → 138 passed. `poetry run pytest -q --no-cov` → 493 passed (504 after T026, minus the 12 tests in the deleted `test_registry.py`, plus 1 net from `TestAvailableFormats`/`TestAMisconfiguredEntryFailsAtFirstRead` sizing — exact accounting not required, every deletion is accounted for by name above). `ruff check literature tests` clean. `ruff format` reformatted `config.py` once (line-length wrapping in `_resolve`'s first raise), clean after. `mypy` → no issues in 13 source files. `grep -rln "importers\.registry\|FormatAlreadyRegistered\|isolated_registry" literature tests` → no hits.

**Next**: T029 — rewrite ADR-0006 and ADR-0007, whose "every format inherits the guarantee, none can weaken it" claim the overridable workflow makes false.

**Watch**: `contracts/importers.md` and `data-model.md` still have sections titled "The registry" describing the deleted `register()`/`get_format()`/`available_formats()` trio — T030 rewrites both for the settings-based mechanism; `config.py`'s own docstring references them by their old section title deliberately, to be updated in the same pass.

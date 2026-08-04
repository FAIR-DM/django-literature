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

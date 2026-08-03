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

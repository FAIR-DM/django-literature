# Implementation Plan: A Standard Contract for Importing Bibliographic Files

**Branch**: `003-import-contract` | **Date**: 2026-08-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-import-contract/spec.md`

## Summary

Add `literature.importers`: one calling contract for reading a bibliographic file into the
catalogue, with the format-specific parts underneath and out of the caller's way. The workflow is
fixed at four stages, of which a format supplies only the first two, and the fourth reuses the
package's existing CSL JSON conversion untouched.

The technical core is smaller than the feature sounds. A `Format` supplies an iterator of entries
and a per-entry conversion to CSL JSON. A runner drives that iterator, wraps each entry in its own
savepoint, calls `from_csl_json`, and records one outcome per entry. A dry run is the same code
path inside an outer transaction that is rolled back at the end, so rehearsed outcomes are
observed rather than predicted. A small registry maps names to formats so a caller can ask what is
available without knowing what is on the list.

## Technical Context

**Language/Version**: Python 3.12–3.13 (package floor 3.11), per `pyproject.toml`

**Primary Dependencies**: Django 5.2 and 6.0. **No new runtime dependency.** Parsing libraries
arrive with the formats that need them (#22, #23), not here.

**Storage**: Django ORM. PostgreSQL is the reference, SQLite is used for tests. No new models, no
migration.

**Testing**: pytest + pytest-django. Test modules mirror the `literature/` tree with `test_`
prefixes, per the architecture constraints.

**Target Platform**: Reusable Django app, embedded in a host project.

**Project Type**: Single library package.

**Performance Goals**: None set, by decision D6. The one behavioural constraint is FR-024, that
entries are consumed one at a time rather than the file being converted up front.

**Constraints**: A format supplies only the parse and convert stages (FR-003). The existing
`from_csl_json` behaviour is unchanged for direct callers (FR-004). Every human-readable string is
translatable (FR-022). Untrusted file content cannot cause an unhandled error (FR-023).

**Scale/Scope**: Five new modules under `literature/importers/`, no models, no migration, no
change to any existing module except `CONTEXT.md` and the docs.

## Constitution Check

*Checked before Phase 0 and re-checked after Phase 1 design. Both passes clean.*

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I — Test-First | Every task pairs a test with its behaviour; the contract is exercised through a test-only format | Pass |
| II — Simplicity | No new dependency, no models, no migration, no settings key. Five modules, each with one job | Pass |
| III — Anti-Abstraction | The one real risk, addressed below | Pass, with reasoning |
| IV — Integration-First | The contract *is* the integration point, and is designed and tested before any format exists to use it | Pass |
| V — Security & data-safety | FR-023: file content is untrusted. No `eval`, no path handling beyond the file handed in, no unhandled error escaping | Pass |
| VI — Documentation | README + CHANGELOG in the same PR; `CONTEXT.md` gains the new vocabulary (FR-025) | Pass |
| VII — Dependency discipline | Nothing added | Pass |
| VIII — i18n (non-negotiable) | Every failure reason and error message wrapped in `gettext_lazy`, matching the existing model and converter strings | Pass |
| IX — CSL JSON as lingua franca | CSL JSON is the intermediate representation, which is the feature's central design choice | Pass |
| X — Embeddable package | Public surface at `literature.importers`, namespaced, no host changes, nothing added to `INSTALLED_APPS` behaviour | Pass |
| XI — Data integrity | Per-entry atomicity exists precisely to serve this; no migration, so no upgrade path needed | Pass |
| XII — Living demo | No demo-visible surface yet, since no format ships. Returns with #22 | Not applicable |

**Article III, examined properly.** This feature adds an abstraction whose only implementation at
merge is a test double, which is the shape the article exists to catch. It passes for a reason
specific to this case rather than by exemption: the workflow is four stages and only the first two
are new. Converting CSL JSON into an `Item` is existing code with real callers today, so the
contract is a seam drawn through a live pipeline rather than a wrapper around an empty one. Two
concrete formats follow immediately behind it (#22, #23), and R5 requires the second precisely so
the seam is proven in the right place. The full reasoning, and the alternative that was rejected,
are in [decisions.md](decisions.md) D1.

## Project Structure

### Documentation (this feature)

```text
specs/003-import-contract/
├── spec.md              # what and why
├── decisions.md         # D1-D10, the reasoning behind the shape
├── research.md          # Phase 0: five questions, answered against the code
├── plan.md              # this file
├── data-model.md        # Phase 1: the objects and their fields
├── contracts/
│   └── importers.md     # Phase 1: the public surface, signature by signature
├── quickstart.md        # Phase 1: what using it looks like
├── checklists/
│   └── requirements.md  # spec quality checklist
├── progress.md          # append-only run record
└── tasks.md             # Phase 2
```

### Source code (repository root)

```text
literature/
├── converters.py          # UNCHANGED. from_csl_json is called, not modified
├── models.py              # UNCHANGED. no new models, no migration
└── importers/             # NEW — the whole feature
    ├── __init__.py        # the public surface, re-exported
    ├── exceptions.py      # the format-to-runner vocabulary  (shared)
    ├── results.py         # Outcome, EntryResult, ImportResult  (shared)
    ├── base.py            # Format, Entry            (US-1)
    ├── runner.py          # import_file — drives the workflow   (US-1, US-2)
    └── registry.py        # register, get_format, available_formats  (US-3)

tests/
└── test_importers/        # mirrors the source tree
    ├── __init__.py
    ├── conftest.py        # the test-only format, in its several shapes
    ├── test_exceptions.py
    ├── test_results.py
    ├── test_base.py
    ├── test_runner.py
    ├── test_dry_run.py
    ├── test_registry.py
    └── test_smoke.py
```

**Structure Decision.** A package rather than a single module, because #22 and #23 each add a
module beside these and a flat `literature/importing.py` would become the pile of loosely related
functions the intake discussion explicitly wanted to avoid. Each module has one job, and they line
up with the stories: `base` + `runner` carry US-1 and US-2, `registry` carries US-3, which is what
makes the stories independently implementable. `exceptions` and `results` are shared by all three,
and are separate from `base` so that `registry` does not have to import the `Format` base class
merely to raise an error.

## Design in brief

The detail is in [contracts/importers.md](contracts/importers.md) and
[data-model.md](data-model.md). The three decisions worth stating up front:

1. **The savepoint is per entry, and the dry run is an outer rollback.** Verified against this
   package's models rather than assumed — see research.md R2. Each entry runs in
   `transaction.atomic()`, the failure is caught outside that block, and the run continues. A dry
   run wraps the whole file in one more `atomic()` and calls `set_rollback(True)` at the end, so
   every stage really executes and reported outcomes are observed rather than predicted.
2. **The atomic block lives in the runner, not in `from_csl_json`.** That keeps FR-004 literally
   true: the existing function and every existing caller are untouched. It also puts the guarantee
   where it is promised.
3. **A dry run's entry results carry no stored `Item`.** The rows exist inside the transaction and
   are gone after it, so exposing a rolled-back instance would hand the caller an object that
   looks saved and is not. Outcomes match between a dry run and a real run; item references do
   not, and the acceptance scenario is written against outcomes for that reason.

## Complexity Tracking

No constitution violations to justify. Nothing on this table.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

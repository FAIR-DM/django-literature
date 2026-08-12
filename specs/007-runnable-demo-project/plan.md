# Implementation Plan: A Runnable Demo That Serves the Front End Over Real References

**Branch**: `007-runnable-demo-project` | **Date**: 2026-08-12 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `specs/007-runnable-demo-project/spec.md`

## Summary

Grow the repository's existing `demo/` project — today a settings module, a URL configuration
mounting only the admin, and nothing else — into a project that installs the front end the way the
README documents, loads a curated catalogue of real references from CSL JSON through the package's
own converter, and starts with one command. Then point a CI workflow at that same project: start
it for real, walk every page the front end serves over HTTP, and fail when a page does not render
or renders without the seeded content in it.

The design rests on one idea: the guard and the demo must be the *same* wiring. Anything the guard
sets up for itself is wiring the evaluator does not get, and the drift this feature exists to catch
would hide in exactly that gap.

## Technical Context

**Language/Version**: Python 3.12+ for anything touching the front end (the `ui` extra carries a
`python_version >= '3.12'` marker); the package's own floor stays 3.11 and is unaffected.

**Primary Dependencies**: Django 5.2 / 6.0, django-mvp via the `ui` extra (which brings
django-cotton, easy-icons, flex-menus, crispy-forms and crispy-tailwind).

**Storage**: SQLite, built on start and never committed. The constitution names PostgreSQL as the
reference and SQLite as supported for development — a demo is development.

**Testing**: pytest and pytest-django for the assertions that live in the suite (packaging,
seed-content invariants); the CI guard is not a pytest run, by design (D-4).

**Target Platform**: a developer's machine, and ubuntu-latest in Actions.

**Project Type**: a reusable Django app plus a demo project inside the same repository.

**Performance Goals**: none stated. The start command should finish in seconds; the guard should
add well under a minute to CI.

**Constraints**: the demo must not enter the published distribution, must add no runtime dependency
to the package, and must not require the test suite's settings to run.

**Scale/Scope**: 28 to 30 seeded references (the list paginates at 24, so the count has to clear
that), four pages walked by the guard, one new workflow.

## Constitution Check

*Checked before Phase 0 and re-checked after the design below.*

| Article | Bearing | Verdict |
|---|---|---|
| I — Test-First | Assertions that live in the suite are written before the thing they check. The guard itself is a workflow, not a test, and D-8 covers how it is proven. | Pass |
| II — Simplicity / III — Anti-Abstraction | Two management commands and one workflow. No seeding framework, no abstraction over the loader, no plugin surface. | Pass |
| IV — Integration-First | The whole feature is an integration check. | Pass |
| V — Security & data-safety | The demo ships a throwaway secret key and `DEBUG = True`, which is correct for a demo and stated as such in its documentation (FR-008). No credential is created and nothing is exposed beyond localhost. | Pass |
| VI — Documentation | FR-008 puts the command in the documentation. The README's front-end install steps are the demo's own configuration, so a gap found while wiring the demo is fixed in the README (research R2). | Pass |
| VII — Dependency discipline | No new dependency, runtime or dev. The guard uses the standard library and Django itself. | Pass |
| VIII — i18n | The demo's own strings are operator-facing command output, not package strings. No new translatable package surface. | Pass |
| IX — CSL JSON as lingua franca | The seed is CSL JSON, loaded through `from_csl_json_list`. This is the article working in the feature's favour rather than constraining it. | Pass |
| X — Embeddable package | The demo consumes the package as a host project would. Nothing here adds to the package's public surface. | Pass |
| XI — Data integrity | No migration, no model change. | Pass |
| XII — Living Demo & Reference App | **Partial, deliberately.** The article's end state is a demo covering installation, item types, import/export, citation rendering, and CRUD/admin. This feature delivers the browse slice and the CI guarantee the article's third clause names verbatim. CRUD arrives with #47 and #48, import through the interface with #50, citation rendering with R7. Each of those extends the demo as part of its own work, which `spec.md` states as an assumption. | Partial — tracked, not a violation |
| XIII — Data-model conventions | No model. | N/A |
| XIV — Test structure & fixtures | New test modules mirror their subject or are declared under `[tool.forge.conformance]`. D-9 covers the two that cannot mirror. | Pass |
| XV — Cohesion | Two small commands, each with one job. | Pass |
| Quality bar — demo app | "Migrates cleanly and its core pages render without import errors" is exactly what this feature makes machine-checked for the first time. | Pass |

No entries for Complexity Tracking: nothing here needs justifying against a simpler alternative
that was rejected for capability reasons.

## Design decisions

### D-1 — The seed is CSL JSON, loaded through the package's own converter

`demo/seed/catalogue.json` holds a CSL JSON array of real published references, loaded with
`literature.converters.from_csl_json_list`. Research R3 carries the reasoning: the file is the real
interchange format so each reference can be sourced from a DOI rather than invented, a Django
fixture would encode primary keys and break on schema change, and loading through the converter
means the demo exercises an import path every time it starts.

### D-2 — Two commands, not one

- `python manage.py seed_demo` — clears the catalogue and loads `demo/seed/catalogue.json`.
  Idempotent by construction: it deletes every `Item` and every `Name` first, so loading twice
  leaves one catalogue (FR-016), and running it against a database in any state returns the seeded
  state (FR-004). Deletion is scoped to the package's own models. `Name` has to be named
  explicitly — it is shared between items, so it is not reachable from `Item`'s cascade, and the
  converter reuses rows with `get_or_create`, which would leave every contributor ever loaded
  behind. It fails non-zero when fewer items load than the file holds, because
  `from_csl_json_list` skips an invalid entry with a warning and returns the survivors, and a
  half-loaded catalogue that reports success defeats the whole guard (FR-020).
- `python manage.py demo` — the documented one command (FR-003). Runs `migrate`, calls
  `seed_demo`, then `runserver` with the autoreloader off. The reloader relaunches `manage.py demo`
  verbatim in a child process, so leaving it on re-runs the destructive seed at every start and
  every file save.

The split exists because the guard has to seed without starting a server. A guard that instead
reached inside the human-facing command would break every time that command changed, which inverts
what a guard is for.

Both live in `demo/management/commands/`, which requires adding `demo` to the demo project's
`INSTALLED_APPS`. That is ordinary Django project structure and touches nothing in the package.

### D-3 — The demo's settings are the README's install steps

`demo/settings.py` gains exactly what the README documents at lines 93–220 — the ten app entries
in the stated order, `SITE_ID`, `CurrentSiteMiddleware`, the `mvp.context_processors.mvp_config`
context processor, the URL include — plus `STATIC_URL`, `EASY_ICONS` and `FLEX_MENUS`, each of
which a front-end page genuinely needs (research R2). It also reads its SQLite path from an
environment variable, defaulting to the current fixed path, so the demo's own tests can run against
a scratch file rather than deleting the developer's demo data. Where
the demo needs something the README does not tell a host to set, the README is corrected in this
PR. That is what makes SC-010 a check rather than a hope.

`demo/urls.py` includes `literature.ui.urls` under `catalogue/` and keeps the admin mount it
already has (decisions D5).

### D-4 — The guard starts a real server and speaks HTTP

A new workflow, `.github/workflows/demo.yml`, installs with `--extras ui`, starts the demo by
running `python manage.py demo` in the background, and runs a smoke script that requests each page
and asserts on its content.

It starts the demo through the documented command rather than composing `migrate` and `seed_demo`
itself, because that command is the artefact FR-003, SC-001 and SC-002 are about: composing its
steps in the workflow would leave a regression in it caught by nothing. `seed_demo` remains a
separate command — the split in D-2 exists so the guard *can* seed without a server, and it stays
the subject of the demo's command tests.

The job runs the pull request head's own code, which the repository's other workflows do not, so it
declares `permissions: contents: read`, inherits no secrets, and triggers on `pull_request` rather
than `pull_request_target`.

Real HTTP rather than Django's test client, because FR-021 makes the guard's subject the project an
evaluator actually runs and the test client stops short of the server starting and static files
being served. Research R5 has the trade-off in full. Readiness is a bounded poll, never a sleep.

The workflow filters paths on `push` and does not on `pull_request` (FR-022), matching `tests.yml`
and `build.yml` and the reason recorded in their comments.

### D-5 — The smoke path browses, it does not reverse detail URLs

The smoke script knows one address: the catalogue list. From there it follows a link to a reference
page, and from that page a link to a contributor page — the way a reader reaches them. It tries the
list's references in order until one yields a contributor link, because the list is ordered
`-created` and FR-014 requires one reference in the seed with no contributors at all; assuming the
first reference has one would make the guard fail on a healthy demo depending on the seed file's
order.

The obvious alternative is to boot Django, reverse `literature:item-detail` and
`literature:contributor-detail`, and look up primary keys. It is rejected because SC-003 requires
every page to be reachable *by browsing*, "with no address typed by hand", and a script that
constructs its own URLs passes happily over a catalogue whose links are broken. Following links
tests the navigation FS-006 built as well as the pages, needs no primary-key lookup at all, and
keeps the script honest about FS-006's D2 ruling that these pages are addressed by primary key —
it never has to know that.

Every page is asserted on content drawn from the seed, never on the status code alone: an empty
catalogue renders a successful empty-state page, so a status-only check passes over exactly the
failure this guard exists to catch (`decisions.md` D3, FR-019). The pages walked are the catalogue
list, its second page, one reference page, and one contributor page.

A failure reports the URL, the status code and a bounded excerpt of the body rather than the whole
response. The demo runs with `DEBUG = True` by design (FR-008), so an unbounded body would put
Django's technical-500 page — settings, installed apps, local variables, request environment — into
a public CI log on every red run.

### D-6 — Curating the catalogue is a task with stated criteria, not a judgement call in code

Research R8 turns each of FR-010 through FR-015 into a shape the catalogue must contain. The seed
file is authored against that table, and a test asserts the table holds — so "the spread is right"
is checkable rather than a reviewer's impression, and stays true when someone edits the file later.

### D-7 — The distribution guarantee becomes a check

`packages = [{ include = "literature" }]` already keeps the demo out of the built distribution and
the built sdist confirms it (research R7). US-4's work is to assert it, in
`tests/test_ui/test_packaging.py`, which already exists for assertions whose subject is
`pyproject.toml` and is already declared as a non-mirror path.

A second assertion, that no SQLite file is tracked by git under `demo/`, was planned and dropped at
the design review: its subject is not `pyproject.toml`, it needs a git index to run, and
`.gitignore` covers the pattern at any depth already.

### D-8 — The guard is proven by reinstating the defect

SC-007 requires the guard to catch a class of breakage the test suite cannot. That is demonstrated
once, deliberately: break the demo's own wiring, observe the guard fail and the suite pass, revert.
The evidence is recorded in the PR rather than left as a claim, because a gate that has never been
seen to fail is a gate nobody has tested.

### D-9 — The demo's test directory is declared once, and honestly

`tests/test_demo/` is declared as a single `non-mirror-paths` prefix under
`[tool.forge.conformance]`, with the commit that creates it, following the pattern the four
existing entries set.

The reason stated is the true one: its subject is the demo project, which lives outside the
`literature/` tree the mirror rule is defined against. Declaring the two files separately on the
usual ground — that no source module exists to mirror — would be false for `test_commands.py`,
whose subject *is* two Python modules this feature creates, and constitution Article XIV makes that
declaration a review failure in its own right.

### D-10 — How the demo's own tests run, given that pytest is bound to the suite's settings

`pyproject.toml` sets `DJANGO_SETTINGS_MODULE = "tests.settings"` for the whole pytest session, and
`demo` is not in that module's `INSTALLED_APPS`. Adding it there would be the obvious fix and is the
wrong one: it would put the demo's app registry inside the suite's wiring, which is the exact
coupling FR-021 forbids and the drift this feature exists to catch.

Two mechanisms instead, chosen per subject:

- **The seed catalogue's content is checked without Django at all.** `test_seed.py` reads
  `demo/seed/catalogue.json` as JSON and asserts research R8's table against it — item-type spread,
  contributor shapes, date precisions, identifier types, the sparse reference, and a count above the
  list's `paginate_by` of 24. No app registry, no database, no settings. This is both simpler and a
  better test: it holds when someone edits the file, which is when it will actually be needed.
- **Command behaviour is checked in a subprocess under `demo.settings`.** `test_commands.py` follows
  the precedent already set by `tests/test_ui/test_smoke.py`, which spawns a fresh interpreter for
  exactly this reason — `django.setup()` runs once per process and the pytest session has already
  populated the registry from `tests.settings`. The subprocess sets `DJANGO_SETTINGS_MODULE` with
  `os.environ[...] = ` rather than `setdefault`, because pytest-django exports the suite's value
  into the environment and a child inherits it. That comment is in the existing file and the same
  trap applies here verbatim.

## Project Structure

### Documentation (this feature)

```text
specs/007-runnable-demo-project/
├── spec.md
├── decisions.md
├── research.md
├── plan.md
├── progress.md
└── tasks.md
```

### Source code (repository root)

```text
demo/
├── __init__.py
├── settings.py                      # front end wired per the README (D-3)
├── urls.py                          # catalogue include + existing admin mount
├── seed/
│   └── catalogue.json               # CSL JSON, 28–30 real references (D-1, D-6)
├── smoke.py                         # assertion helpers for the guard (D-5)
└── management/
    ├── __init__.py
    └── commands/
        ├── __init__.py
        ├── demo.py                  # migrate + seed + runserver (D-2)
        └── seed_demo.py             # idempotent catalogue load (D-2)

.github/workflows/
└── demo.yml                         # the guard (D-4)

tests/
├── test_demo/
│   ├── __init__.py
│   ├── test_seed.py                 # the spread the seed must hold (D-6, D-10)
│   └── test_commands.py             # command behaviour, in a subprocess (D-10)
└── test_ui/
    └── test_packaging.py            # extended: demo absent from the build (D-7)

README.md                            # demo section; front-end install gaps fixed (D-3, FR-008)
```

**Structure Decision**: the demo stays where it is, at the repository root beside `manage.py`, which
already points at it. Nothing moves, and the package tree is untouched.

## Phases

**Phase 1 — Foundational (sequential, blocks everything).** Wire `demo/settings.py` and
`demo/urls.py` to the documented install path, add `demo` to `INSTALLED_APPS`, and correct any gap
the wiring exposes in the README's front-end steps. Until this lands, no page renders and no other
story can be verified.

**Phase 2 — US-1 (P1).** The two management commands. `seed_demo` against a minimal placeholder
catalogue so the command is testable before curation lands; `demo` composing migrate, seed and
runserver. Documentation of the command.

**Phase 3 — US-2 (P2).** Curate the real catalogue against research R8's table and replace the
placeholder. Add the test that holds the spread.

**Phase 4 — US-3 (P3).** The smoke script, the workflow, and the D-8 demonstration.

**Phase 5 — US-4 (P4).** The packaging assertion.

Phases 2 and 3 are ordered rather than parallel: the curated file replaces the placeholder the
commands were built against, and splitting them across worktrees would put two authors in the same
file for no gain. Phase 4 depends on both. Phase 5 is independent of 2–4 and can run alongside.

## Complexity Tracking

No entries. The Constitution Check records one deliberate partial (Article XII), which is a scope
boundary the specification already states rather than a complexity to justify.

# Tasks: A Runnable Demo That Serves the Front End Over Real References

**Input**: `spec.md`, `plan.md`, `research.md`, `decisions.md` in `specs/007-runnable-demo-project/`

**Format**: `[ID] [P?] [Story] Description` — `[P]` marks a task that can run in parallel with the
one before it (different files, no dependency).

Tests are written before the code they check, per constitution Article I.

---

## Phase 1: Foundational (blocking — no story can be verified until this lands)

**Purpose**: the demo project installs and serves the front end. Nothing renders before this.

- [ ] T001 Add `"demo"` to `INSTALLED_APPS` in `demo/settings.py`, and wire the front end exactly as `README.md` documents it at lines 93–220: the nine app entries in the stated order (`literature`, `django.contrib.sites`, `django.contrib.staticfiles`, `django_cotton`, `easy_icons`, `flex_menu`, `mvp`, `crispy_forms`, `crispy_tailwind`, `literature.ui`), `SITE_ID`, and `django.contrib.sites.middleware.CurrentSiteMiddleware`.
- [ ] T002 Add the three settings a front-end page needs that the README's prose does not spell out, each with the failure it prevents as a comment, copying the reasoning already recorded in `tests/settings.py`: `STATIC_URL`, `EASY_ICONS` with a `default` renderer over `mvp.utils.BS5_ICONS`, and `FLEX_MENUS` declaring the `sidebar` and `dock` renderers.
- [ ] T003 Include `literature.ui.urls` under `catalogue/` in `demo/urls.py`, keeping the existing admin mount untouched.
- [ ] T004 Correct `README.md`'s front-end install steps for anything T001–T003 showed to be missing or wrong, so the documented path and the demo's wiring agree (SC-010). If nothing was missing, record that in the task notes rather than editing the README.
- [ ] T005 Verify by hand: `poetry install --extras ui`, `python manage.py migrate`, `python manage.py runserver`, and confirm the catalogue list renders its empty state at `/catalogue/`. Capture the outcome in the story report — this is the first time the front end has ever been served from a real project.

**Checkpoint**: the demo serves an empty catalogue.

---

## Phase 2: US-1 — Start the demo and browse real references (P1)

**Goal**: one documented command takes a clone to a served front end over a loaded catalogue.

- [ ] T006 [US1] Write `tests/test_demo/test_commands.py` (and `tests/test_demo/__init__.py`), failing: `seed_demo` loads the catalogue file, running it twice leaves the same number of items rather than double, and running it against a catalogue holding unrelated items leaves only the seeded ones. Each test runs in a subprocess under `DJANGO_SETTINGS_MODULE=demo.settings`, set with `os.environ[...] =` and never `setdefault` — follow the mechanism and the comments in `tests/test_ui/test_smoke.py`, which exists for the same reason (plan D-10).
- [ ] T007 [US1] Create `demo/seed/catalogue.json` as a placeholder holding three or four real references in CSL JSON, enough for T006 to pass. Curation is T012's job, not this one.
- [ ] T008 [US1] Write `demo/management/commands/seed_demo.py` (with `demo/management/__init__.py` and `demo/management/commands/__init__.py`): delete every `Item`, then load `demo/seed/catalogue.json` through `literature.converters.from_csl_json_list`, and report how many references were loaded. Make T006 pass.
- [ ] T009 [US1] Write `demo/management/commands/demo.py`: call `migrate`, then `seed_demo`, then `runserver`, printing the address to open. It must fail with a plain message naming the missing extra when `literature.ui` is not installed, rather than dying inside Django's app loading (spec edge case).
- [ ] T010 [US1] Document the demo in `README.md`: the one command, what it does, what to expect on screen, and a plain statement that the demo is not a production configuration — debug on, a local file database, a throwaway key (FR-008).

**Checkpoint**: `python manage.py demo` serves a populated catalogue from a fresh clone.

---

## Phase 3: US-2 — A catalogue worth looking at (P2)

**Goal**: the seeded references are real, and between them they show what the store holds.

- [ ] T011 [US2] Write `tests/test_demo/test_seed.py`, failing: read `demo/seed/catalogue.json` as plain JSON — no Django, no database (plan D-10) — and assert research R8's table. At least ten distinct item types; a reference with eight or more contributors and one with two; a contributor credited on at least two references under at least two different roles; a year-only date, a full date, and a range; identifiers of at least two types with at least one DOI; exactly one reference carrying no contributors, no dates and no identifiers; and a total above 24, which is the list's `paginate_by`.
- [ ] T012 [US2] Curate `demo/seed/catalogue.json`: 28 to 30 genuine published references in CSL JSON, replacing the placeholder, chosen to satisfy T011. Every entry must be a real work with a resolvable identifier where it has one — sourced CSL JSON, not invented records. Spread the item types across what a research literature collection actually holds rather than covering all 45.
- [ ] T013 [US2] Confirm by hand that the reference page, the contributor page and the list's second page each render over the curated catalogue, and that the sparse reference renders without the sections it has nothing for.

**Checkpoint**: the demo shows the store's range on its face.

---

## Phase 4: US-3 — A broken demo is caught before anyone tries it (P3)

**Goal**: CI starts the demo through its own wiring and fails when it has broken.

- [ ] T014 [US3] Write `demo/smoke.py`: starting from the catalogue list — the only address it knows — request each page over HTTP against a running server by **following links**, never by constructing detail URLs (plan D-5). Walk the list, its second page, a reference page reached from the list, and a contributor page reached from that reference. Each check asserts on content that can only be present if the seed loaded, never on the status code alone (FR-019, decisions D3), and the walk itself is what proves SC-003's "reachable by browsing, with no address typed by hand". Exit non-zero naming the page and the reason on any failure.
- [ ] T015 [US3] Assert in `demo/smoke.py` that no page in the walk redirects to a login and that the run creates no user, so the demo's openness (FR-005) is checked rather than assumed. The whole walk is unauthenticated, which is the check.
- [ ] T016 [US3] Add `.github/workflows/demo.yml`: install with `--extras ui`, run `migrate` and `seed_demo`, start the demo's server, poll a bounded readiness check rather than sleeping, run `demo/smoke.py`, and stop the server. Filter paths on `push`; do **not** filter on `pull_request`, and carry the comment explaining why, as `tests.yml` and `build.yml` do (FR-022).
- [ ] T017 [US3] Prove the guard against the defect it exists to catch (plan D-8, SC-007): break the demo's own wiring — remove `EASY_ICONS` from `demo/settings.py` is the cheapest real example — then confirm the demo check fails while the full test suite still passes. Revert the break. Record both outcomes in the story report with the failing output, because a gate nobody has seen fail is a gate nobody has tested.
- [ ] T018 [US3] Add `tests/test_demo/test_seed.py` and `tests/test_demo/test_commands.py` to `[tool.forge.conformance]` `non-mirror-paths` in `pyproject.toml`, each with a comment naming its subject, following the four entries already there (plan D-9).

**Checkpoint**: a broken demo is a red check on the change that broke it.

---

## Phase 5: US-4 — The demo stays out of what is published (P4)

**Goal**: the guarantee that holds today by construction becomes a checked one.

- [ ] T019 [P] [US4] Extend `tests/test_ui/test_packaging.py`, failing first: assert that `pyproject.toml`'s `packages` declaration includes only `literature`, so neither the demo project nor its seed catalogue can enter the built distribution, and that no dependency existing only for the demo appears in the package's runtime dependencies or the `ui` extra.
- [ ] T020 [P] [US4] In the same module, assert that no SQLite database file is tracked by git anywhere under `demo/`, so FR-007's "the data is the source, the database is built from it" cannot be undone by someone committing a working database. `.gitignore` already covers the pattern; this makes the guarantee checked rather than conventional.

**Checkpoint**: installing the package resolves nothing that exists only for the demo.

---

## Dependencies

- Phase 1 blocks everything. Nothing renders until the front end is wired.
- Phase 2 depends on Phase 1. Phase 3 depends on Phase 2 (T012 replaces the placeholder T007 created).
- Phase 4 depends on Phases 2 and 3 — the smoke path needs both the commands and a catalogue with a contributor credited on more than one reference.
- Phase 5 is independent of Phases 2–4 and may run alongside them.
- T018 is grouped with Phase 4 for convenience but only requires that T006 and T011 have created their files.

## Verification at story completion

Every story runs `forge verify` (the full suite, lint, type and dependency checks) before it is
reported. Per-task test scope is the class or module the task touches; the full suite runs once, at
the report.

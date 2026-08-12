# Progress — 007 A Runnable Demo That Serves the Front End Over Real References

Append-only. Each entry is dated, states what happened, and never rewrites an earlier one.

## 2026-08-12 — S0 INTAKE

Grilled from issue #46. Two questions, both confirmed without correction: the guard's subject is the
demo project's own settings and wiring rather than a second rendering of what the test suite already
covers, and the catalogue is a small fixed curated set of genuine published references rather than
volume. Issue labelled `accepted`.

## 2026-08-12 — S1 SPECIFY

`spec.md` written: 4 user stories (P1–P4), 25 functional requirements, 10 success criteria.
Clarification scan resolved six ambiguities from intake context without escalation; each is recorded
in `spec.md` under `## Clarifications` and reasoned out in `decisions.md` as D1–D6. Spec lint green:
every requirement maps to a story, every story carries acceptance scenarios, the spec cites G6, no
unresolved markers.

## 2026-08-12 — S2 SETUP

Branch `007-runnable-demo-project` pushed as the repository bot. Issue #46 promoted to epic in place
(retitled `FS-007: …`, body grown, intake paragraph preserved). Story sub-issues #59–#62 created
with no labels and linked under the epic. Draft PR #63 opened bot-authored, titled verbatim from the
epic, milestone `v1.0.0`, description carrying one `Closes` line per issue in the graph.
`check-issue-titles` green.

## 2026-08-12 — GATE_SPEC: APPROVED

Approved by Sam in session, without changes. Brief posted as a bot comment on the epic
(issue #46, comment 5264831385) covering the summary, goal link, story list, the six self-resolved
ambiguities and two risks. Recorded here at the moment of approval, before S3 creates the ledger.

## 2026-08-12 — S3R DESIGN REVIEW: CHANGES APPLIED

One reviewer, three lenses, one round. Verdicts: spec-compliance `request_changes` (high),
security `approve` (low), architecture `request_changes` (medium). Thirteen findings — two high,
eight medium, three low. Craft-skill receipts matched the registry in all three files. Every
remedy was applied to `plan.md` and `tasks.md`, and both blocking findings were verified against
the repository before the edit rather than accepted on the reviewer's word.

**SPEC-001 (high, verified).** Nothing in the plan ever ran `manage.py demo`. The workflow composed
`migrate` + `seed_demo` + a server start itself and the only command test covered `seed_demo`, so
the single documented command — the whole subject of FR-003, SC-001 and SC-002 — was checked by
nothing. T016 now starts the demo by running that command, which removes steps from the workflow
rather than adding them.

**SPEC-002 (high, verified).** `literature/converters.py:525-541` catches `ValidationError` per
entry, logs a warning and returns the survivors, so a rejected seed entry vanished silently: T008
reported a count and compared it to nothing, and T011 asserted the spread against the JSON file
rather than the loaded catalogue. A half-loaded catalogue would have passed every check with
SC-004 false in the running demo. T008 now fails when the loaded count does not match the file.

Also applied: `Name` rows are deleted on re-seed (they are shared between items and survive
`Item`'s cascade); `runserver` runs with the autoreloader off, which was re-running the destructive
seed on every file save and is also what makes the backgrounded command in CI a single process;
the demo carries the README's `mvp_config` context processor (SC-010); `demo/settings.py` reads its
SQLite path from an environment variable so the suite stops deleting the developer's demo database;
the smoke walk tries references in order until one has a contributor, rather than assuming the
first does; failures report a bounded excerpt, not a full `DEBUG` traceback page, into a public CI
log; the workflow takes `permissions: contents: read` and no secrets, being the first job here to
run the pull request head's own code; `tests/test_demo/` is declared once as a non-mirror path with
its real reason; and T020 was dropped as work to remove.

Ledger and `forge stage-exit --stage S3R` green.

## 2026-08-12T10:30Z · Implementer US1 · T001

Did: Added `"demo"` to `INSTALLED_APPS` in `demo/settings.py`, wired the README's ten front-end
app entries in stated order (`literature`, `django.contrib.sites`, `django.contrib.staticfiles`,
`django_cotton`, `easy_icons`, `flex_menu`, `mvp`, `crispy_forms`, `crispy_tailwind`,
`literature.ui`), set `SITE_ID = 1`, added `django.contrib.sites.middleware.CurrentSiteMiddleware`
to `MIDDLEWARE`, and made the SQLite path read `DEMO_DB_PATH` from the environment, defaulting to
`BASE_DIR / "demo" / "db.sqlite3"`.
Verified: `python3 -c "import demo.settings as s; ..."` — confirmed `INSTALLED_APPS` order,
`SITE_ID == 1`, `CurrentSiteMiddleware` present, default DB path unchanged with no env var set, and
`DEMO_DB_PATH=/tmp/scratch.sqlite3` overrides it. `poetry run ruff check demo/settings.py` — All
checks passed.
Next: T002 (EASY_ICONS, FLEX_MENUS, mvp_config context processor).
Watch: no automated pytest exists for `demo/settings.py` in this story — `demo` is deliberately not
in `tests.settings.INSTALLED_APPS` (plan.md D-10), so Phase 1 wiring is verified by manual import
checks here and by T005's manual server run, not a committed test file.

## 2026-08-12T10:35Z · Implementer US1 · T002

Did: Added `EASY_ICONS` (default renderer over `mvp.utils.BS5_ICONS`), `FLEX_MENUS` (`sidebar` and
`dock` renderers) and `mvp.context_processors.mvp_config` to
`TEMPLATES[0]["OPTIONS"]["context_processors"]` in `demo/settings.py`, each with a comment naming
the failure it prevents, copied from `tests/settings.py`'s reasoning. `STATIC_URL` already existed
from the original demo project; added the same explanatory comment.
Verified: `python3 -c "import demo.settings as s; ..."` — confirmed `EASY_ICONS`, `FLEX_MENUS` and
the context processor list. `poetry run ruff check demo/settings.py` — All checks passed.
Next: T003 (urls.py).
Watch: none.

## 2026-08-12T10:40Z · Implementer US1 · T003

Did: Added `path("catalogue/", include("literature.ui.urls"))` to `demo/urls.py`, keeping the
existing `admin/` mount.
Verified: `DEMO_DB_PATH=/tmp/scratch2.sqlite3 DJANGO_SETTINGS_MODULE=demo.settings poetry run
python3 -c "django.setup(); print([str(p.pattern) for p in get_resolver().url_patterns])"` →
`['admin/', 'catalogue/']`, proving the full settings+urls wiring boots and resolves in a fresh
interpreter. `poetry run ruff check demo/urls.py` — All checks passed.
Next: T004 (README comparison).
Watch: none.

## 2026-08-12T10:42Z · Implementer US1 · T004

Did: Compared README.md lines 93-220 against the wiring T001-T003 produced: the ten
`INSTALLED_APPS` entries and their order, `mvp` before `crispy_tailwind`, `STATIC_URL`,
`EASY_ICONS`, `FLEX_MENUS`, `TEMPLATES` context processor, `SITE_ID`, `CurrentSiteMiddleware`, and
the `catalogue/` URL include all match the README exactly. Nothing was missing or wrong.
Verified: manual line-by-line comparison of `demo/settings.py` and `demo/urls.py` against
README.md:93-220; no diff found.
Next: T005 (manual server run).
Watch: none — no README edit made, per the task's own "if nothing was missing, say so" branch.

## 2026-08-12T10:50Z · Implementer US1 · T005 (manual verification)

Did: `mkdir -p /tmp/dl-demo-t005 && DEMO_DB_PATH=/tmp/dl-demo-t005/db.sqlite3
DJANGO_SETTINGS_MODULE=demo.settings poetry run python manage.py migrate --noinput` — applied
admin, auth, contenttypes, literature (2 migrations), sessions, sites cleanly, no errors. Then
`poetry run python manage.py runserver 127.0.0.1:8765 --noreload` in the background and
`curl -s -o catalogue.html -w "HTTP %{http_code}"  http://127.0.0.1:8765/catalogue/` → `HTTP 200`.
The response body renders the packaged empty state: "Nothing in the catalogue yet" / "References
imported or created will appear here.", page title "Items | example.com" (confirming SITE_ID +
mvp_config wiring), no traceback. `curl` against `/admin/login/` also returned `HTTP 200`. Server
process killed and the scratch database directory removed afterward; no `.sqlite3` file is tracked
by git (`git status` clean).
Verified: first real serve of the front end from a project — `poetry install --extras ui` had
already been run for the worktree; `migrate` then `runserver` then `/catalogue/` all succeeded as
above.
Next: T006 (failing test for seed_demo).
Watch (concerns, not fixed — outside T001-T003's documented scope): the server log printed
`Could not reverse URL for view 'home' in menu item 'home' / Reverse for 'home' not found` on every
request. The page still rendered correctly (200, correct content), so this did not block T005, but
it suggests django-mvp's default navigation expects a URL named `home` that neither the README's
front-end install steps nor `demo/urls.py` provide. Recorded in the completion report's `concerns`.

## 2026-08-12T11:00Z · Implementer US1 · T006

Did: Created `tests/test_demo/__init__.py` and `tests/test_demo/test_commands.py`, following
`tests/test_ui/test_smoke.py`'s subprocess mechanism (plan.md D-10): `DJANGO_SETTINGS_MODULE` and
`DEMO_DB_PATH` are set with `os.environ[...] =`, never `setdefault`, inside a script run via
`subprocess.run([sys.executable, "-c", script], ...)`. `DEMO_DB_PATH` points at `tmp_path` so the
suite never touches the developer's demo database; `migrate` runs before `seed_demo` in the same
subprocess. Three tests: loads the catalogue, running twice leaves the same count, reseeding
against different content leaves only the new items. The third test needed control over which
catalogue file `seed_demo` reads without mutating the tracked `demo/seed/catalogue.json`, so I
introduced `DEMO_SEED_PATH` (recorded as decisions.md D7, mirrors T001's `DEMO_DB_PATH`).
Verified: `poetry run pytest tests/test_demo/test_commands.py -q` → 3 failed, all with
`CommandError: Unknown command: 'seed_demo'` — the right reason (RED, per craft-tdd). `poetry run
ruff check tests/test_demo/` — All checks passed.
Next: T007 (seed catalogue).
Watch: none.

## 2026-08-12T11:10Z · Implementer US1 · T007

Did: Created `demo/seed/catalogue.json` — 4 real, verifiable references in CSL JSON (Shannon 1948,
Watson & Crick 1953, Darwin 1859, Vaswani et al. 2017), covering `article-journal`, `book` and
`paper-conference` types. Placeholder only, per the task's own limit — full curation is T012.
Verified: ran `literature.converters.from_csl_json_list` against the file in a scratch pytest test
(not committed) — all 4 entries loaded, citation keys
`['Shannon1948', 'WatsonCrick1953', 'Darwin1859', 'Vaswani2017']`.
Next: T008 (seed_demo command).
Watch: none.

## 2026-08-12T11:25Z · Implementer US1 · T008

Did: Created `demo/management/__init__.py`, `demo/management/commands/__init__.py` and
`demo/management/commands/seed_demo.py`: deletes every `Item` and every `Name` first, reads the
catalogue path from `DEMO_SEED_PATH` (default `demo/seed/catalogue.json`, decisions.md D7), loads it
through `literature.converters.from_csl_json_list`, and raises `CommandError` naming any entries
whose citation key isn't among the loaded items when the loaded count doesn't match the file's
entry count. `help` states the deletion outright. Also added a fourth test,
`test_fails_non_zero_and_names_entries_when_fewer_load_than_the_file_holds`, to
`tests/test_demo/test_commands.py` for this failure-mode behaviour — it's in the brief's T008
acceptance criteria but not enumerated among T006's three named scenarios, so I wrote it test-first
as part of this task rather than skip it.
Verified: `poetry run pytest tests/test_demo/test_commands.py::TestSeedDemo::test_fails_non_zero_and_names_entries_when_fewer_load_than_the_file_holds -q` →
1 failed with `Unknown command: 'seed_demo'` (RED, right reason) before the command existed. After
implementing: `poetry run pytest tests/test_demo/test_commands.py -q` → 4 passed. `DEMO_DB_PATH=/tmp/dl-demo-t008.sqlite3
poetry run python manage.py help seed_demo` → help text states "Delete every Item and every Name...
Destructive: anything entered through the admin is lost." `poetry run ruff check demo/management/
tests/test_demo/` — All checks passed.
Next: T009 (demo command).
Watch: none.

## 2026-08-12T11:45Z · Implementer US1 · T009

Did: Created `demo/management/commands/demo.py`: calls `migrate`, then `seed_demo`, prints the
address to open, then `runserver` with `use_reloader=False`. Also added a guard in
`demo/settings.py` (`try: import mvp / except ImportError: sys.stderr.write(...); sys.exit(1)`) —
`django.setup()` imports every `INSTALLED_APPS` entry before any management command's `handle()`
runs (verified by reading `django/core/management/__init__.py:353-417` in the installed Django 5.2
source), so a missing `ui`-extra dependency can only be caught this early, not inside `demo.py`.
Recorded as decisions.md D8.
Verified: wrote a failing test first
(`TestDemoCommand::test_fails_with_a_plain_message_when_the_ui_extra_is_missing`, shadows the real
`mvp` package with a stub via `PYTHONPATH` and runs `manage.py demo` as a real subprocess) — RED
with a full Python traceback ending in the stub's `ImportError` before the guard existed. After
implementing: `poetry run pytest tests/test_demo/test_commands.py -q` → 5 passed. Manual happy-path
check: `DEMO_DB_PATH=/tmp/dl-demo-t009/db.sqlite3 poetry run python manage.py demo` (backgrounded)
→ migrate applied all app migrations, `curl http://127.0.0.1:8000/catalogue/` → `HTTP 200` with
"Shannon", "Watson", "Darwin" and "Vaswani" all present in the body — the seed loaded and served.
Process killed and scratch DB directory removed afterward; `git status` clean, no `.sqlite3`
tracked. `poetry run ruff check demo/settings.py demo/management/commands/demo.py` — All checks
passed.
Next: T010 (README documentation).
Watch: the `Could not reverse URL for view 'home'` warning noted at T005 also appears here — same
pre-existing concern, not new to this task.

## 2026-08-12T11:50Z · Implementer US1 · T010

Did: Added a "Try it: the demo project" subsection to README.md, right after the front-end install
steps and before "Quick Start": the one command (`python manage.py demo`), what it does (creates
the database, migrates, loads the seed, starts the server), what to expect (the address to open and
that the three page kinds are live and populated), that re-running returns the demo to the seeded
state, and a plain statement that the demo is not a production configuration (DEBUG on, SQLite file,
throwaway secret key) — FR-008.
Verified: read the new section back against T009's actual behaviour (migrate, seed_demo, runserver,
printed address) and against `demo/settings.py`'s `DEBUG`/`SECRET_KEY`/`DATABASES` values — all
match what is documented.
Next: full suite, pre-commit, completion report.
Watch: none.

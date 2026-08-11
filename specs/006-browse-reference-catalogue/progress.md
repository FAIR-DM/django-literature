# Progress — 006 Browse the Reference Catalogue in an Opt-In Front End

Append-only. Each entry records a stage transition or a gate outcome at the moment it happened.

## 2026-08-11 — S0 INTAKE

Grilled from issue #45, its five R6 siblings (#46–#50), roadmap item R6, `GOALS.md`, `README.md`
and `memory/constitution.md`. Four questions asked and answered:

1. `literature.ui` inherits django-accounts-center's composition rule — django-mvp built-ins by
   default, a custom component raised before it is built, a local fill only as a bridge until an
   upstream release carries the component.
2. The catalogue list ships paginated here, in one fixed order. Search, facets and reader-chosen
   ordering stay with #49.
3. The reference page shows the whole record, not just contributors, dates and identifiers.
4. The pages are open by default. Gating is a later specification.

Feature statement confirmed. `accepted` added to #45 alongside the permanent `feature-request`
label.

## 2026-08-11 — S1 SPECIFY

`specs/006-browse-reference-catalogue/` created on branch `006-browse-reference-catalogue`.
`spec.md` drafted, clarification scan run in full: five ambiguities resolved from intake context
without escalating, recorded under `## Clarifications` and in `decisions.md` (D1–D6). Spec lint
green: every FR covered by a story, no unresolved markers, goal id cited.

## 2026-08-11 — S2 SETUP

Branch pushed as `fairdm-bot`. Issue #45 promoted in place to the epic
(`FS-006: Browse the reference catalogue in an opt-in front end`), intake body preserved under
`## Original request`. Three story sub-issues created with no lifecycle labels: #52 (P1), #53 (P2),
#54 (P3). Draft PR #55 opened bot-authored, milestone `v1.0.0`, `Closes` block seeded with one line
per issue. `forge check-issue-titles` green.

## 2026-08-11 — Spec gate, revision

Sam asked for a dedicated contributor-centred page at the gate, reversing the clarification scan's
D4. Added as User Story 4 at P4, with FR-032 through FR-038 and SC-010 through SC-012. D4 rewritten
with the original decision struck through rather than removed; D7 added for the non-merging of
identical stored names. Story #56 created and linked, epic body and PR description re-synced,
`forge check-issue-titles` green again. Revised gate brief posted to the epic as the bot.

## 2026-08-11 — Spec gate APPROVED

Sam approved the revised specification. Four stories in flight. State advances to S3 PLAN.

## 2026-08-11T14:26:43Z · Implementer US0 · T001

Did: added `[project.optional-dependencies].ui = ["django-mvp (>=0.17,<1.0) ;
python_version >= '3.12'"]` to `pyproject.toml` (placed after the full `[project]` table —
a table header interleaved before `classifiers` silently swallowed it into
`[project.optional-dependencies]`, corrupting `poetry lock`; caught by running `poetry lock`
immediately). Regenerated `poetry.lock`. Allowlisted `DEP002` for `django-mvp` in
`[tool.deptry.per_rule_ignores]`, since nothing in the foundational phase imports it in Python
(only in templates, `{% extends "mvp/base.html" %}`, and `INSTALLED_APPS` strings — neither is
visible to deptry's import scan).

Verified: `poetry lock` exit 0; `poetry run deptry .` exit 0 ("Success! No dependency issues
found."); `poetry check` exit 0; `grep 'name = "django-mvp"' poetry.lock` shows
`optional = true`, `markers = "python_version >= \"3.12\" and extra == \"ui\""`.

Next: T002, the app package. Watch: the `DEP002` ignore becomes redundant (not harmful) once
US-1's `views.py` imports `mvp` directly — a cleanup, not a defect.

## 2026-08-11T14:26:43Z · Implementer US0 · T002

Did: `literature/ui/__init__.py` (docstring only) and `literature/ui/apps.py`
(`LiteratureUIConfig`, `name = "literature.ui"`, `label = "literature_ui"`, translated
`verbose_name`, no `default_auto_field` — the app has no models). Created
`tests/test_ui/__init__.py` (needed by this task's own test collection; Article XIV also assigns
it to T004, which finds it already present).

Test-first: `tests/test_ui/test_apps.py` — `TestLiteratureUIConfig` boots Django in a subprocess
with only `literature` + `literature.ui` installed and asserts no `AppRegistryNotReady`;
`TestLiteratureUIInit` parses `__init__.py` with `ast` and asserts its body is exactly one
docstring `Expr`. Ran red first (`ModuleNotFoundError: No module named 'literature.ui'` /
`FileNotFoundError`), then green after the implementation.

Verified: `poetry run pytest tests/test_ui/test_apps.py -v` — 2 passed. `pre-commit run --files
literature/ui/__init__.py literature/ui/apps.py tests/test_ui/__init__.py
tests/test_ui/test_apps.py` — all green (one `# noqa: S603` added on the subprocess call — fixed
interpreter, literal script, no user input).

Next: T003, the base template.

## 2026-08-11T14:26:43Z · Implementer US0 · T003

Did: `literature/ui/templates/literature/ui/base.html` — extends `mvp/base.html` directly,
recomposes the `<c-page class="{{ page.class }}">` wrapper and the breadcrumbs region
(`<c-toolbar><c-breadcrumbs :items="page.breadcrumbs" .../></c-toolbar>`) that D-1's snippet
omits, on top of the `<c-container>` / `<c-page.content>` / `<c-page.title>` chain D-1 gives.
Exposes `{% block page.content %}` for pages to fill.

Test-first: `tests/test_ui/test_templates.py` (`TestBaseTemplate`) reads the shipped template
source and asserts it extends `mvp/base.html`, contains none of `page_view.html`,
`list_view.html`, `detail_view.html` or a bare `"base.html"` reference, and renders both
recomposed regions. Ran red (`FileNotFoundError`) before the template existed, green after.

This test's subject is a template, not a Python module, so `check_mirror` has no
`literature/ui/templates.py` to match it against — confirmed by temporarily removing the
declaration and re-running `forge verify --steps conformance`, which failed with exactly that
delta. Declared `tests/test_ui/test_templates.py` under `[tool.forge.conformance]
non-mirror-paths` in `pyproject.toml`; T025 (Phase 5, not this story) extends the same list with
its own two files when it lands.

Verified: `poetry run pytest tests/test_ui/test_templates.py -v` — 5 passed.
`forge verify --steps conformance` — passed (and independently confirmed to fail without the
declaration). `pre-commit run --files literature/ui/templates/literature/ui/base.html
tests/test_ui/test_templates.py` — green.

Next: T006 (URLs) ahead of T004 (test wiring) — T004's "mount the app in tests/urls.py" step
needs `literature/ui/urls.py` to exist first; see `decisions.md`.

## 2026-08-11T14:26:43Z · Implementer US0 · T006

Did: `literature/ui/urls.py` — `app_name = "literature"`, three routes (`item-list`,
`item-detail`, `contributor-detail`) bound to `django.views.generic.View` placeholders rather
than `literature.ui.views` (which US-1/US-2/US-4 create — see `decisions.md`). Executed before
T004 in this session: T004's "mount the app in tests/urls.py" needs this file to exist, and
brief-listed order is not a hard sequencing constraint within one story's own tasks (both are
mine). T006's own test does not depend on T004's mount either way — it builds its own throwaway
`ROOT_URLCONF` via `override_settings`, the same pattern django-mvp's `test_views/test_extra.py`
uses.

Test-first: `tests/test_ui/test_urls.py` (`TestURLs`) — parametrised reverse() under a mounted
prefix for all three route names; an `ast`-based check that importing `urls.py` never names
`literature` in an import statement. Ran red (`ModuleNotFoundError` / `FileNotFoundError`) with
the file moved aside, green restored.

Verified: `poetry run pytest tests/test_ui/test_urls.py -v` — 4 passed. `forge verify --steps
conformance` — passed. `pre-commit run --files literature/ui/urls.py tests/test_ui/test_urls.py`
— green.

Next: T004, test wiring — now unblocked.

## 2026-08-11T14:26:43Z · Implementer US0 · T004

Did: `git mv tests/settings.py tests/settings_core.py` and gave it its own
`ROOT_URLCONF = "tests.urls_core"` (new file, empty `urlpatterns`) — the base, not a copy, per D-4.
New `tests/settings.py`: `from tests.settings_core import *  # noqa: F403` plus appends
`django.contrib.sites`, `django.contrib.staticfiles`, `django_cotton`, `easy_icons`, `flex_menu`,
`mvp`, `literature.ui` to `INSTALLED_APPS`, the `mvp.context_processors.mvp_config` context
processor, `SITE_ID = 1`, `ROOT_URLCONF = "tests.urls"`. No crispy app or setting added. Mounted
the app in `tests/urls.py`: `path("catalogue/", include("literature.ui.urls"))` — matches the
prefix `test_urls.py` (T006) already assumed. `tests/test_ui/conftest.py`: one `populated_item`
fixture (see D-12; `tests/test_ui/__init__.py` already existed from T002).

Test-first: `tests/test_ui/test_smoke.py` — `TestSettingsCore` boots `tests.settings_core` in a
subprocess (forcing `DJANGO_SETTINGS_MODULE`, not `setdefault`: pytest-django already exports it
into the environment as `tests.settings`, and a plain `setdefault` silently inherited that instead
of overriding it — caught by the first run, not guessed at) and asserts no UI app and an empty
urlconf; `TestSettings` asserts in-process (this *is* the session's real settings module) that the
UI stack, context processor, `SITE_ID`, `ROOT_URLCONF` and the crispy-absence all hold. Ran red
first — `tests.settings.py` existed only as the bare `from tests.settings_core import *` line, so
every `TestSettings` assertion failed for the missing content, not a collection error — then green
after the appends and the `tests/urls.py` mount.

Verified: `poetry run pytest tests/test_ui/ -v` — 18 passed (all four foundational test modules
together). `poetry run python3 -c "... get_template('literature/ui/base.html') ..."` — loads
without `TemplateDoesNotExist`, confirming `mvp`/`django_cotton` are genuinely wired, not just
declared. `forge verify --steps conformance` — passed. `poetry run deptry .` — exit 0. `pre-commit
run --files tests/settings_core.py tests/settings.py tests/urls_core.py tests/urls.py
tests/test_ui/test_smoke.py tests/test_ui/conftest.py` — green: `F403` on the star-import, `F405`
on each of the three `INSTALLED_APPS`/`TEMPLATES` star-import references in `tests/settings.py`.

Next: T005, wire the `ui` extra into CI. Watch: `populated_item`/`client` fixture sufficiency is
D-12's open question for US-1/US-2/US-4 to confirm — flagged in the completion report's concerns.

## 2026-08-11T14:26:43Z · Implementer US0 · T005

Did: `.github/workflows/tests.yml` — `poetry-install-args: '--extras ui'` (was `''`). The reusable
workflow's `python-versions` default (`["3.12", "3.13"]`) is left as-is and already satisfies the
extra's `python_version >= '3.12'` marker, so no other input needs changing.

No pytest scope for a workflow-call argument. Verified instead: YAML parses
(`python3 -c "import yaml; yaml.safe_load(...)"`, `pre-commit run check-yaml`) and the exact
command the reusable workflow's `setup-poetry` action runs —
`poetry install --no-interaction --no-root --extras ui` — succeeds locally against this
worktree's lock file (exit 0, "No dependencies to install or update", the extra already present
from T001's `poetry install --extras ui`).

Concern: T005's own acceptance ("confirm on the pull request that the UI tests actually appear in
the run") needs a real CI run against this branch's PR, which this story cannot produce or observe
— no `gh`, no network beyond the package registry, no tokens. Flagged for Forge to confirm once the
PR is open.

Next: T001–T006 complete. Full verify, then the completion report.

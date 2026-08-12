# Research — 007 A Runnable Demo That Serves the Front End Over Real References

Phase 0. Each entry states the unknown, what was found in the codebase or the documentation, and
the resolution the plan builds on. Nothing here is speculative: every claim names the file it came
from.

## R1 — What the demo project is today

`demo/` already exists and is tracked: `demo/__init__.py`, `demo/settings.py`, `demo/urls.py`. Its
settings install the core `literature` app and nothing else — no `literature.ui`, no django-mvp, no
`django.contrib.sites`. Its URL configuration mounts Django's admin and nothing else.
`manage.py` at the repository root already defaults `DJANGO_SETTINGS_MODULE` to `demo.settings`, so
the entry point exists and works today. `demo/db.sqlite3` is present locally and untracked
(`.gitignore` lines 63–67 cover `db.sqlite3` and `/*.sqlite3`).

**Resolution**: this feature grows the existing project rather than creating one. The gap is
everything above the admin: the front end is not installed, no data is loaded, and no command
starts it.

## R2 — What the demo's settings must contain

The README documents the complete install path for the front end at lines 93–220: the `ui` extra,
nine `INSTALLED_APPS` entries in a stated order (`mvp` before `crispy_tailwind`, because django-mvp
overrides a crispy-tailwind template and first-declared wins), `django.contrib.sites` with a
`SITE_ID`, `CurrentSiteMiddleware`, and a namespaced URL include. `tests/settings.py` is a working
instance of the same wiring and additionally documents three things the README's prose covers less
directly, each with the failure it prevents:

- `STATIC_URL` must be set: `mvp/base.html` loads its stylesheet with `{% static %}`
  unconditionally, and `django.contrib.staticfiles` being installed is not enough on its own.
- `EASY_ICONS` must configure a `default` renderer with `mvp.utils.BS5_ICONS`, or any page using
  `<c-icon>` — which `mvp/base.html` does — raises `ImproperlyConfigured`.
- `FLEX_MENUS` must declare the `sidebar` and `dock` renderers, or `mvp/base.html`'s chrome raises
  `ValueError` at render time.

**Resolution**: FR-002 requires the demo to wire the front end the way the documentation tells a
host to. The demo's settings follow the README's steps, and the three items above are part of what
a working install needs. Where the demo needs something the README does not state, the README is
the thing that is wrong — the discrepancy is fixed there rather than papered over in the demo, which
is what makes SC-010 checkable rather than aspirational.

## R3 — How the seed catalogue is loaded

`literature/converters.py` exposes `from_csl_json(data: dict) -> Item` (line 404) and
`from_csl_json_list(data: list[dict]) -> list[Item]` (line 525), the package's own CSL JSON entry
points. The constitution's Article IX makes CSL JSON 1.0.2 the canonical interchange format and the
authoritative reference for item types, name variables and date variables.

The alternative is a Django fixture loaded with `loaddata`.

**Resolution**: the seed catalogue is a CSL JSON file loaded through `from_csl_json_list`. Three
reasons, in order of weight:

1. A CSL JSON file is the real thing. A DOI resolver hands out CSL JSON directly, so each seeded
   reference can be sourced rather than invented, which is what FR-009's "genuine published works"
   asks for and what a fixture would quietly make impossible to verify.
2. A fixture encodes primary keys, content-type ids and the exact current field set. It breaks on
   schema change in a way that looks like a demo failure rather than a stale fixture, and keeping it
   current is manual work at every migration. CSL JSON is defined by an external standard the
   package already tracks.
3. Loading through the package's own converter means the demo exercises an import path on every
   start, so the guard covers more of the package for free. Article XII asks the demo to demonstrate
   import as well as browsing, and this is the cheapest honest version of that.

The cost is real and worth stating: an importer bug now breaks the demo. For a regression guard that
is the desired direction.

## R4 — What the one command does, mechanically

The repository has no task runner. There is no `tasks.py`, no `Makefile`, and `pyproject.toml`
declares no script entry points — only `manage.py`, which already points at `demo.settings`.

**Resolution**: the one command is a Django management command, `python manage.py demo`, which
migrates, loads the seed and starts the server. It requires adding `demo` to the demo project's own
`INSTALLED_APPS` so Django discovers `demo/management/commands/`, which is ordinary Django project
structure and changes nothing about the package.

The loading half is split out as its own command, `seed_demo`, for one reason that matters: the
guard needs to seed without starting a server, and a guard that reaches into the internals of a
command built for humans is a guard that breaks when the human-facing command changes. Two commands,
one of which calls the other.

## R5 — How the guard starts the demo and what it asserts

Two candidate mechanisms:

- **Django's test client under `demo.settings`.** Reliable, fast, no ports. It does not exercise
  static file serving, WSGI handling, or the server actually starting — which is a meaningful part
  of what "the demo still starts" means, and precisely the layer `tests/settings.py` already covers
  from a different angle.
- **A real server plus real HTTP requests.** Exercises the whole path an evaluator walks. Costs a
  readiness poll and carries some flake risk.

**Resolution**: real HTTP against a real server. FR-021 is explicit that the guard's subject is the
project someone actually runs, and the test client stops one layer short of that. Article XII
independently asks CI to verify "the demo app migrates cleanly and its pages render". Flake is
managed by polling a readiness endpoint with a bounded timeout rather than sleeping.

Page addresses are reversed rather than hardcoded. `literature/ui/urls.py` namespaces its routes as
`literature` with names `item-list`, `item-detail` and `contributor-detail`, and both detail routes
take a primary key. FS-006's D2 settled that a reference page is addressed by primary key and never
by citation key, so the smoke path has to discover the keys of seeded records rather than assume
them.

Assertions come from the seed. Requesting a page and checking for a 200 is not enough: FS-006's
US-1 requires an empty catalogue to render an empty-state page successfully, so an unloaded seed
produces a green check over an empty demo. Each page is checked for content that can only be there
if the seed loaded — decided in `decisions.md` D3 and required by FR-019.

## R6 — Where the check is wired

All five of the repository's CI workflows are thin callers of the shared family workflows at
`django-mvp/shared@v0.2.0` (`build.yml`, `tests.yml`, `docs.yml`, plus the release pair). There is
no shared demo workflow to call, and the demo is specific to this package rather than a family
concern, so this is the repository's first workflow carrying its own job.

Two constraints carry over from the existing files:

- `tests.yml` and `build.yml` both filter by path on `push` and deliberately do **not** on
  `pull_request`, with a comment recording why: a path-filtered required check never reports on an
  out-of-scope pull request, and a required check that never reports blocks the merge. FR-022 puts
  the demo check under the same rule.
- `tests.yml` passes `poetry-install-args: '--extras ui'`, without which every `literature.ui` test
  is silently skipped. The demo job needs the same extra for the same reason, and here the failure
  would be louder — the front end simply would not install.

**Resolution**: a new repository-local workflow. Arming it as a required check in ruleset 19620991
is a repository-settings action and is recorded in `spec.md` as the maintainer's, not this branch's.

## R7 — Whether the demo is already excluded from the distribution

`pyproject.toml` line 5 declares `packages = [{ include = "literature" }]`. Inspecting the built
sdist at `dist/django_literature-0.1.8.tar.gz` confirms its top level holds `LICENSE`, `PKG-INFO`,
`README.md`, `literature` and `pyproject.toml`, with nothing under `demo`.

**Resolution**: US-4's guarantee holds today by construction. The work is to make it checked rather
than incidental, so that a later change — a demo dependency added to the wrong group, a packaging
key edited — cannot quietly break it. `tests/test_ui/test_packaging.py` already exists as the home
for assertions whose subject is `pyproject.toml`, and it is already declared as a non-mirror path
under `[tool.forge.conformance]`.

## R8 — What the seed catalogue has to contain

`literature/choices.py` declares 45 CSL item types, 26 name roles, 6 date slots and 6 known
identifier types. `decisions.md` D1 settles that the seed covers a representative range rather than
one of each, and that exhaustive per-type rendering stays with FS-006's SC-008 in the test suite.

The store's shapes the seed must exercise, each traceable to a requirement:

| Shape | Requirement | Where it shows |
|---|---|---|
| A spread of item types | FR-010 | list and reference pages |
| Many contributors, and few | FR-011 | reference page |
| One contributor on several references, in different roles | FR-011 | contributor page |
| Year-only, full date, and a range | FR-012 | reference page |
| Identifiers of more than one type, one resolvable | FR-013 | reference page |
| A reference with no contributors, dates or identifiers | FR-014 | reference page's empty sections |
| Enough references to paginate | FR-015 | list page |

The list page's default order is the model's `-created`, which FS-006's D1 settled deliberately, so
the seeded order is load order. That matters for the smoke path only in that it must not assume a
particular reference is first.

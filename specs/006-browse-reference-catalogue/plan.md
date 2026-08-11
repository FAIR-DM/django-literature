# Implementation Plan: Browse the Reference Catalogue in an Opt-In Front End

**Branch**: `006-browse-reference-catalogue` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-browse-reference-catalogue/spec.md`

## Summary

Add `literature.ui`, an opt-in Django app shipping three read-only pages — a paginated catalogue
list, a reference page showing an item's whole record, and a contributor page listing everything one
name is credited on. Every page is composed from django-mvp's published components with no
stylesheet and no components of our own. django-mvp arrives through a PEP 621 optional extra, so a
core-only install resolves nothing extra, and a static architecture test keeps it that way.

The one design decision that shapes everything else: the app's templates extend `mvp/base.html`
through a namespaced base of their own, rather than inheriting django-mvp's packaged
`list_view.html` / `detail_view.html` chain, because that chain requires a project-level `base.html`
the host may not have written (research R2).

## Technical Context

**Language/Version**: Python 3.12+ for the extra (django-mvp's floor); the core keeps its own 3.11 floor

**Primary Dependencies**: django-mvp ≥ 0.17, < 1.0 — optional, extra `ui`. It transitively brings django-cotton, django-easy-icons, django-flex-menus, django-crispy-forms, crispy-tailwind, mergedeep

**Storage**: no new models, no migrations — this feature reads the existing schema

**Testing**: pytest + pytest-django; `tests/test_ui/` mirroring `literature/ui/`; factories already exist per model

**Target Platform**: any Django ≥ 5.2 project that installs the extra; the core stays on Django ≥ 4.2

**Project Type**: reusable Django package with an opt-in sub-app

**Performance Goals**: a page's queries do not grow with catalogue size — pagination bounds the rows, and each page issues a constant number of queries regardless of how many objects it renders

**Constraints**: no stylesheet, no cotton components of our own, and only utility classes named in django-mvp's allowlist (research R4). No write path anywhere. No authentication or permission check.

**Scale/Scope**: three page types, four user stories, no schema change

## Constitution Check

Read against `memory/constitution.md` v3.0.0.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I–IV (org core) | Ordinary code standards, tests, review | Pass — nothing unusual |
| V (untrusted input) | Path parameters are integers; no file or user text is parsed | Pass |
| VI (ubiquitous language) | FR-031 adds *UI app* and *catalogue* to `CONTEXT.md` in the same change | Pass, tracked as a task |
| VII (documented public surface) | The app's URLs, settings and install steps go in the README | Pass, tracked as a task |
| VIII (i18n) | Every string in a view or template is wrapped; identifier-type acronyms stay exempt as `choices.py` already records | Pass, FR-007 |
| IX (CSL JSON as lingua franca) | The pages display CSL vocabulary as stored and rename nothing | Pass |
| X (embeddable Django package) | The whole feature is the article: opt-in app, namespaced optional URLs, no mandatory host change, `LITERATURE` settings key if any setting is needed | Pass — and FR-002's extra strengthens it |
| XI (data integrity) | Read-only; no migration, no schema change | Pass, vacuously |
| XII (living demo) | The article requires the demo to stay current with the package. This feature adds pages the demo does not serve — issue #46 is the feature that wires them up, and it depends on this one | **Watch item**, see Risks |
| Architecture: "server-rendered Django templates by default. No third-party form/table/filter/JS packages are prescribed yet; adopting one is a constitutional amendment" | django-mvp is a third-party UI package. Adopting it here is not a quiet choice: GOALS.md G4 names it, the README's scope section names it, and roadmap R6 names it | Pass — but the constitution's architecture section is stale and must be updated in this PR to record django-mvp as the adopted UI layer, or the next reader finds the article contradicting the shipped code |

**Consequence**: one constitution amendment lands in this PR, recorded as a task. It documents what
GOALS.md and the README already committed to, rather than deciding anything new.

## Project Structure

### Documentation (this feature)

```text
specs/006-browse-reference-catalogue/
├── spec.md
├── decisions.md
├── research.md
├── plan.md
├── tasks.md
├── progress.md
└── feature-state.json
```

No `data-model.md` — this feature adds no model. No `contracts/` — it has no API surface; its
contract is its URL names and template names, recorded below.

### Source code

```text
literature/
├── utils/
│   └── fields.py                 # NEW — iterate an item's non-empty scalar fields (research R6)
└── ui/                           # NEW — the whole opt-in app
    ├── __init__.py               # curated re-exports, mirroring importers/__init__.py
    ├── apps.py                   # LiteratureUIConfig, label "literature_ui"
    ├── urls.py                   # app_name = "literature", three routes
    ├── views.py                  # ItemListView, ItemDetailView, ContributorDetailView
    └── templates/
        └── literature/
            └── ui/
                ├── base.html            # extends mvp/base.html, recomposes page chrome
                ├── item_list.html
                ├── item_list_item.html  # one row of the catalogue
                ├── item_detail.html
                ├── contributor_detail.html
                └── contributor_item.html # one row of a contributor's credits

tests/
├── settings.py                   # EDITED — UI apps added so view tests can run
├── urls.py                       # EDITED — mounts literature.ui.urls
└── test_ui/                      # NEW — mirrors literature/ui/
    ├── conftest.py
    ├── test_architecture.py      # the US-3 boundary proof
    ├── test_packaging.py         # the US-3 dependency proof
    ├── test_urls.py
    ├── test_item_list.py
    ├── test_item_detail.py
    ├── test_contributor_detail.py
    └── test_templates.py         # utility-class allowlist + i18n wrapping
```

**Structure Decision**: `literature/ui/` as a sub-package of the shipped `literature` package.
Poetry's `packages = [{ include = "literature" }]` already ships nested sub-packages, so no
packaging change is needed to distribute it — only the extra that makes its dependency installable.
The sub-package mirrors `literature/importers/`, the repo's existing sub-app precedent, including a
curated `__init__.py` rather than an empty one.

## Design

### D-1 — Templates extend `mvp/base.html` through our own base, never `base.html`

Established in research R2. `literature/ui/templates/literature/ui/base.html` extends
`mvp/base.html` and fills `{% block content %}` with the chrome the packaged `page_view.html` would
have supplied, composed from published components:

```django
{% extends "mvp/base.html" %}
{% block content %}
  <c-container>
    <c-page.content gap="4" class="py-4">
      <c-page.title :attrs="page" />
      {% block page.content %}{% endblock %}
    </c-page.content>
  </c-container>
{% endblock %}
```

Every page template extends this and fills `page.content`. Nothing in the app references
`base.html`, `list_view.html`, `detail_view.html`, or `page_view.html`.

**Why not the packaged chain**: it would make the app fail with `TemplateDoesNotExist` in any host
that has not written its own `base.html`, which contradicts FR-004. **Why not ship our own
top-level `base.html`**: it would become the fallback shell for the host's own pages.

### D-2 — Views subclass django-mvp's, with search and the create action switched off

`ItemListView(MVPListView)` and `ItemDetailView(MVPDetailView)`, both with `template_name` set
explicitly so `BaseTemplateNameMixin`'s fallback never reaches the packaged templates.

`MVPListView` supplies exactly what FR-014 and FR-017 need — `paginate_by` (default 24), the
`page_obj` that `<c-pagination>` consumes, the `page` context dict `<c-page.title>` reads, breadcrumbs,
and the empty-state strings FR-018 needs. It also carries `SearchMixin`, `OrderMixin` and
`CRUDDirectoryMixin`, all of which are out of scope here (FR-029):

- `search_fields = None` is a documented no-op — the mixin returns the queryset unmodified.
- `order_by = None` likewise.
- `directory = []` suppresses the create-URL injection, so no create control can render.

Our own template renders no search box and no create button regardless, but the attributes are set
explicitly rather than left to the template, so a later template change cannot resurrect a control
this feature excluded.

**Why subclass at all**, when plain `ListView` plus twenty lines would do: issue #49 adds search,
filtering and ordering to this same page, and `MVPListView` is where those arrive by configuration.
Building on `ListView` now would make #49 a rewrite of the view layer rather than three attributes.

`ContributorDetailView` is an `MVPDetailView` on `Name` that paginates a related queryset itself —
`MVPDetailView` has no pagination, so the view builds a `Paginator` over the contributor's items and
puts `page_obj` in context under the same name `<c-pagination>` expects.

### D-3 — Queries

**Catalogue list.** `Item.objects.all()` in the model's declared order, with
`.prefetch_related("item_names__name", "item_dates")` so a page of 24 rows costs a constant number
of queries rather than one per row per relation. FR-013's row needs the title, type, contributors,
issued date and citation key; type and citation key are columns on `Item`.

**Reference page.** `Item.objects.prefetch_related("item_names__name", "item_dates", "item_identifiers")`.
`ItemName.Meta.ordering` already yields role-then-position, so the template groups by role with
`{% regroup %}` and needs no ordering logic (research R6).

**Contributor page.** The items a name is credited on:

```python
Item.objects.filter(item_names__name=self.object).distinct()
```

`.distinct()` is load-bearing: `ItemName` is unique on `(item, role, name)`, so a contributor holding
two roles on one item has two rows, and without it the item would appear twice — which FR-035
forbids. The roles for each item come from one further query over
`ItemName.objects.filter(name=self.object, item__in=<page's items>)`, grouped in Python into
`{item_id: [role, …]}`. One query per page, not one per row.

Both `ItemName` indexes this relies on already exist.

### D-4 — How US-3 is proved

`tests/settings.py` must install the UI apps for any view test to run, so "the existing suite passes
with the app absent" stops being literally observable in the default suite. US-3 is proved by three
tests that are stronger than the literal reading, because they fail on the *cause* rather than on a
symptom:

1. **`test_architecture.py`** — walk every module under `literature/` outside `literature/ui/`, parse
   it, and assert no `import`/`from` statement names `mvp`, `django_cotton`, `crispy_forms`,
   `easy_icons`, `flex_menu`, or `literature.ui`. This is FR-006 as a test, and it is the failure
   mode that actually happens: someone adds a convenience import to a core module.
2. **`test_packaging.py`** — parse `pyproject.toml` and assert `django-mvp` appears in
   `[project.optional-dependencies].ui` and in no other dependency list. This is FR-002 as a test.
3. **A core-only boot test** — a subprocess running `django.setup()` and `manage.py check` against a
   core-only settings module (`tests/settings_core.py`, the current settings unchanged), then
   importing every core module. It proves the core still boots with nothing UI installed, which is
   the part of SC-009 a static scan cannot reach.

Test 3 is one subprocess in the whole suite, so its cost is negligible and it catches the case the
other two cannot: a runtime rather than import-time dependency.

### D-5 — No `get_absolute_url` on the core models

`<c-data-field>` auto-links a value that has `get_absolute_url()`, which would be convenient for
contributor names on the reference page. Adding it to `Item` or `Name` is rejected: the method would
have to reverse a URL that only exists when the UI app is installed and its URLs are included, so it
would raise `NoReverseMatch` in a core-only project. That breaks FR-006 — the core must behave
exactly as it does today with the app absent — and it does so at runtime, in the host's code, which
is the worst place to find it.

The UI builds its own links with `{% url 'literature:…' %}`, and `<c-data-field>` receives plain
values.

### D-6 — Scalar-field iteration is extracted, existing callers are not touched

`literature/utils/fields.py` gains one function returning `(verbose_name, value)` pairs for an item's
non-empty concrete fields, excluding relations, primary key, and the housekeeping columns `created`
and `modified` — with the skip set a parameter so a caller states its own. The three existing
in-line copies (`converters.py`, two test modules) are left alone: rewriting working code that no
requirement touches would put the diff into the tamper guard and widen review for no gain. Recorded
as a follow-up, not done here.

### D-7 — Utility classes are allowlisted, and the allowlist is a test

Per research R4, a class outside django-mvp's published list renders unstyled and silently forces a
Tailwind build. `test_templates.py` scans every template the app ships, extracts every `class="…"`
token, and asserts each is either a daisyUI component class used by a packaged component or a
utility named in django-mvp's `utility-classes.md`. Arbitrary values (`w-[37px]`), opacity modifiers
(`text-base-content/60`), and the `sm:` and `2xl:` prefixes fail.

This is the only mechanical guard that FR-008 is actually held, and django-accounts-center's two
shipped workaround rules are the evidence that it is needed.

## Story boundaries

| Story | Builds | Depends on |
|---|---|---|
| **Foundational** (not a story) | `literature/ui/` package, `apps.py`, the extra in `pyproject.toml`, `base.html`, test settings and URL wiring | — |
| **US-1** (P1) | `ItemListView`, `item_list.html`, `item_list_item.html`, pagination, empty state | Foundational |
| **US-2** (P2) | `ItemDetailView`, `item_detail.html`, `literature/utils/fields.py` | Foundational |
| **US-3** (P3) | The three proofs in D-4; the extra is already declared by Foundational | Foundational |
| **US-4** (P4) | `ContributorDetailView`, `contributor_detail.html`, `contributor_item.html`, the link from US-2's page | US-2 for the link |

The foundational phase is sequential and lands first. US-1, US-2 and US-3 are then independent of
each other. US-4 needs US-2's template to add the link, so it runs after it.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| A base template of our own rather than django-mvp's packaged view templates | The packaged chain requires a host-supplied `base.html` (research R2) | Extending `list_view.html` fails with `TemplateDoesNotExist` in any host that has not written one, breaking FR-004. Shipping our own top-level `base.html` hijacks the host's shell |
| Subclassing `MVPListView` when three of its four mixins are out of scope | #49 adds search, filter and ordering to this exact page, where they are configuration on this class | Plain `ListView` makes #49 a view-layer rewrite instead of three attributes |

## Risks

- **The demo does not exercise these pages.** Constitution Article XII requires the demo to stay
  current, and issue #46 is the feature that serves the front end from it. Until #46 lands, every
  claim here rests on tests. This is the ordering the roadmap chose (#46 depends on #45), so it is
  accepted rather than resolved — but it means a rendering fault that tests do not model survives
  this PR. Mitigation: the template tests assert rendered output, not just a 200 response.
- **The extra narrows the supported floor.** django-mvp needs Python ≥ 3.12 and Django ≥ 5.2; the
  core supports 3.11 and Django ≥ 4.2. A project on the older floor cannot install the extra. This is
  correct behaviour for an optional dependency and is documented in the README rather than fixed.
- **CI does not test the extra.** The reusable workflow installs main + dev + docs groups. Unless the
  `ui` extra is installed in CI, no UI test runs there and the suite silently shrinks to the core.
  The install argument must be set on the workflow call, and a task covers it.
- **`deptry` sees a new optional dependency.** It runs in the build job and fails on a dependency it
  cannot account for. The extra must be declared in a form it recognises.

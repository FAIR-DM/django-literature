# Progress — 010 Find a reference in a large catalogue

Append-only. Each entry is written at the moment the thing it records happened.

## 2026-08-20 — intake

Grilled against issue #49, its dependency #45, the sibling issues citing R6, and the front end as
it stands after FS-009. Six questions, all answered in session. Accepted; the issue carries its
decision label.

## 2026-08-20 — specification

`spec.md` and `decisions.md` written and pushed as the bot. Five user stories, thirty-six
functional requirements, nine success criteria, ten recorded decisions. No unresolved markers.

## 2026-08-20 — setup

Issue #49 promoted to the epic in place, five story sub-issues created (#91–#95) and linked,
draft pull request #96 opened by the bot with a closing line for the epic, every story, and #88.
Title lint and the stage's exit checks green. Specification gate brief posted to the epic.

**Awaiting: specification sign-off.**

## 2026-08-20 — indexing withdrawn at the gate

The requirement to index the searched fields is dropped. An ordinary index cannot serve a
fragment search, and the alternative that can is a database-specific facility whose adoption is a
separate decision. The feature now ships no index and no migration. Specification, decisions,
requirements, success criteria, the epic and the first story updated; recorded on the issue
thread.

## 2026-08-20 — specification gate: approved

Signed off in session, with the indexing requirement withdrawn as recorded above. Planning begins.

## 2026-08-20 — planning

`research.md` (eleven findings), `plan.md` (twelve decisions) and `tasks.md` (thirty tasks across a
foundational phase and five stories) authored; ledger created and schema-valid.

The upstream surface was mapped by reading django-mvp at v0.19.1 directly. Search and filtering are
both adopted rather than written: the search mixin needs only a field list, and the filter
integration is reached by composing the documented mixin with django-filter's own view. Two findings
change the shape of the work — the filter form drops a chosen sort when it submits (raised upstream,
carried in our own form if that can be done without touching an upstream template), and no demo seed
reference carries a language, so the language filter would render empty.

## 2026-08-20 — design review: changes requested, all applied

One reviewer carrying compliance, security and simplicity lenses over the five specification
artefacts, with the upstream research re-verified against django-mvp at v0.19.1 and django-filter's
own source. Six findings, one of them high, plus six notes. Every one applied; no round two.

The high finding is the only one that changed the design. The plan held the contributor page's
controls off by leaving its filterset unset, and that does not disable filtering — django-filter
defaults to generating a filterset over every field of the model, which raises on this model's JSON
fields, so the contributor page would have returned a server error on every request. The page
therefore stops inheriting the catalogue: what the two share moves into a mixin, the catalogue adds
the filtered base class and the shared definition on top, and the contributor page keeps the plain
list view it has always behaved like.

The rest tightened the tasks rather than the design. One test case demanded behaviour the adopted
components cannot produce and does not need to (an address carrying an undefined filter key is
ignored, not rejected); the sort-preservation measure would have reported the sort as an applied
filter, which is now an assertion and a second abort condition on that task; one functional
requirement — clearing the search — had no task and now has one; the stories are recorded as
sequential, since four of the five edit the same two files; and the search's cost scaling with query
length is written into the decisions as a watch item rather than work. Requirement citations that
had drifted past the end of the specification's numbering are corrected.

## 2026-08-20 · Implementer US0 · T001

Did: raised the `ui` extra's floor (django-mvp `>=0.19.1,<1.0`, carrying
django-mvp/django-mvp#270's pagination-link fix) and added `django-filter
(>=26.1,<27)` — 26 is the current major on the package index today, not the
25 the tasks draft assumed, so pinned to what actually resolves. Moved the
packaging test's exact-list assertion with it. Added a
`[tool.deptry.package_module_name_map]` entry for django-filter: uninstalled,
deptry's guess is `django_filter` (singular) while the real import is
`django_filters` (plural) — confirmed directly against
`deptry.dependency.Dependency` rather than assumed.

Verified: `poetry run pytest -q tests/test_ui/test_packaging.py` — 7 passed.

Next: T002 (lock and install for real).

## 2026-08-20 · Implementer US0 · T002

Did: `poetry lock` then `poetry install --extras ui`. Resolved versions:
**django-mvp 0.19.1** (up from the 0.19.0 the lock pinned before this story;
requires `django>=5.2`) and **django-filter 26.1** (new; requires
`django>=5.2`), both consistent with the demo/test environment's Django
5.2.13.

Watch: this floor rise carries the pagination-link fix, so
`tests/test_ui/test_views.py::TestCatalogueOrdering::test_sort_survives_following_the_rendered_link_to_page_2`
(currently `xfail`, tracking #88) may now `XPASS`. `pyproject.toml` sets no
`xfail_strict`, so an XPASS does not fail the suite — confirmed by running
the full baseline after this task (see T007's entry). That test and its
xfail marker are outside this story's scope (US-3/D-10 owns the pagination
assertion moves) and were not touched.

Verified: `poetry run pytest -q tests/test_ui/test_packaging.py` — 7 passed
(unaffected by the lock/install alone; scope carried over from T001).

Next: T003 (settings + architecture guard).

## 2026-08-20 · Implementer US0 · T003

Did: added `django_filters` to `INSTALLED_APPS` in `tests/settings.py` and
`demo/settings.py` (unconditional, alongside `django_tables2`), to the
installation documentation's `INSTALLED_APPS` block in README.md, and to
`FORBIDDEN_ROOTS` in `test_architecture.py`'s core-purity scan.

Before wiring it in, proved the new `FORBIDDEN_ROOTS` entry actually catches
a real import: temporarily appended `import django_filters` to
`literature/choices.py`, ran
`TestCoreImportsNothingFromTheUIStack::test_module_imports_no_ui_dependency[choices.py]`,
watched it fail for exactly that reason (`imports forbidden module(s):
{'django_filters'}`), then reverted the probe with `git checkout --` before
touching anything else — no core module carries that import now.

Verified: `poetry run pytest -q tests/test_ui/test_architecture.py
tests/test_ui/test_smoke.py` — 28 passed.

Next: T004 (`SEARCH_FIELDS` in a new `literature/ui/filters.py`).

## 2026-08-20 · Implementer US0 · T004

Did: created `literature/ui/filters.py` with `SEARCH_FIELDS` — the eight ORM
paths from plan D-3 — and nothing else. `tests/test_ui/test_filters.py`
asserts the list's exact contents and, parametrized per path, that
`Item.objects.filter(**{f"{path}__icontains": "x"})` builds without raising:
Django resolves a lookup path into fields at `.filter()`-call time, before
any database access, so a renamed field fails here rather than as a silently
empty search. Watched the test fail first with `ModuleNotFoundError` (the
module did not exist yet), then created the module.

Verified: `poetry run pytest -q tests/test_ui/test_filters.py` — 9 passed.
`poetry run ruff check literature/ui/filters.py tests/test_ui/test_filters.py`
— clean.

Next: T005 (`ItemFilterSet`: item type, contributor, language).

## 2026-08-20 · Implementer US0 · T005

Did: added `ItemFilterSet` to `literature/ui/filters.py` with `type`
(`ChoiceFilter` over `ItemType.choices`, exact match on the stored value),
`contributor` (`CharFilter` with a `method`, `Q`-OR across
`item_names__name__family/given/literal`, no role restriction — matching is
"in any role" simply by never filtering on role) and `language` (a new
`LanguageFilter(ChoiceFilter)` subclassing the same idiom as django-filter's
own `AllValuesFilter`, but excluding the empty string the free-text
`language` column holds on most references today). `Meta.fields = []`
pins the "no auto-generated filters, only what is declared" rule the module's
own docstring now states — the exact default the brief warned against.

`self.model` needed by `LanguageFilter.field` is assigned by
`BaseFilterSet.__init__` on every filter instance (confirmed by reading
`django_filters/filterset.py`) — recomputed fresh per `ItemFilterSet`
instantiation, i.e. per request, not cached at import time.

One test needed correcting mid-task: asserting `"" not in field.choices`
against the *built form field* failed, because `ChoiceField` itself prepends
its own `("", empty_label)` "any" option — a UI affordance, not the language
column's blank value, and exactly the "own 'any' option" the task text
already named. Reworked the language tests to assert against
`extra["choices"]` — the raw list `LanguageFilter.field` computes — which is
what T005 actually specifies.

Verified: `poetry run pytest -q tests/test_ui/test_filters.py` — 19 passed.
`poetry run ruff check` and `poetry run mypy literature/ui/filters.py` —
clean (one `Meta.fields: list[str] = []` annotation added for mypy).
`poetry run deptry .` — clean (was `DEP002 'django-filter' … not used` before
this task; the import now exists).

Next: T006 (distinct queryset).

## 2026-08-20 · Implementer US0 · T006

Did: added `ItemFilterSet.filter_queryset()`, calling the parent
implementation then `.distinct()` — one place (plan D-4), not restated per
view. Two tests written first and watched fail (2 items instead of 1) before
the override existed: a contributor credited in two roles on the same item,
and two different `item_names` rows on one item both matching the same
`contributor` fragment — the second is the case the task text calls out
directly ("a multi-value filter matching two related rows").

Per the task's own instruction, also ran the table's existing sort tests as
a regression check — `poetry run pytest -q tests/test_ui/test_tables.py -k
"sort or order or Order or Sort"`, 22 passed, unaffected (this story has not
touched `tables.py` or `views.py`).

**Concern, not a blocker — recorded as decisions.md D11.** Running
`test_views.py` more broadly than that one check (both its ordering-relevant
classes) turned up two pre-existing, unrelated test failures caused by the
django-mvp floor bump in T001/T002:
`TestItemListView::test_page_holds_no_more_than_paginate_by_items_whatever_the_catalogue_size[literature:item-list]`
and `TestItemTableView::test_paging_to_the_next_page_renders_the_next_rows_under_the_same_headings`.
0.19.1 changes more than research R6 found — `MVPTableView.paginate_queryset()`
now returns the queryset unsliced, so `response.context["object_list"]` on
the table route is the full catalogue rather than one page of it. What
actually renders is still correctly paginated (confirmed: the position-line
and `page=2`-link test for the same route still passes) — only that one
context variable's meaning changed. Confirmed the cause by pinning
django-mvp to 0.19.0 (`pip install "django-mvp==0.19.0"`) and back: both
failures disappear and reappear with the version alone. Left both tests and
`literature/ui/views.py` untouched — out of this story's scope — and wrote
up the finding in decisions.md D11 for whichever story next touches
`ItemTableView` (US-1/T008 is the likely one) to inherit knowingly rather
than rediscover blind.

Verified: `poetry run pytest -q tests/test_ui/test_filters.py` — 21 passed.
`poetry run ruff check`, `ruff format --check` and `mypy
literature/ui/filters.py` — clean.

Next: T007 (the shared `issued` annotation and the year filter).

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

## 2026-08-20 · Implementer US0 · T007

Did: added `annotate_issued()` (FS-009's `Subquery` over `ItemDate`, moved
here from where `ItemTableView.get_queryset()` and `test_tables.py` each
currently write it inline — neither touched; that consolidation is the
consuming story's job, not this one's) and the `issued_year` filter, both on
`ItemFilterSet`. `filter_queryset()` now calls `annotate_issued()`
unconditionally, before `super().filter_queryset()` and `.distinct()`, so a
consumer sorting on `issued` (`ItemTable.order_issued`) gets the column
whether or not a year was requested.

Two write-ups worth keeping, both found by running the real thing rather
than assuming:

1. **`issued__year` needs the annotation's output field stated explicitly.**
   `ItemDate.begin` is a `PartialDateField` (`django-partial-date`), whose
   `get_internal_type()` reports `"DateTimeField"` for the database column
   but which does not itself carry Django's `year` transform — that is
   registered on `DateField`/`DateTimeField` specifically, and
   `PartialDateField` subclasses plain `models.Field`. Inferred from the
   subquery's source, the annotation carried `PartialDateField` as its
   output field, and `issued__year=value` raised `FieldError: Unsupported
   lookup 'year' for PartialDateField`. Tried a `gte`/`lt` half-open range
   next — lookups every field carries — and that compiled but returned
   wrong rows: `PartialDateField` encodes its precision (year/month/day) in
   the stored value's *seconds* component, so a year-only date and a
   full-date range boundary for the same calendar year compare unequal at
   that resolution, sometimes including the wrong item, sometimes excluding
   the right one (both reproduced). The fix that actually works: state
   `output_field=DateTimeField()` explicitly on the `Subquery` — the SQL
   column is unaffected, but the lookup now resolves against Django's own
   `DateTimeField`, whose `year` transform extracts the year component in
   SQL and is correctly indifferent to the seconds-encoded precision.
   Confirmed via `manage.py shell` before writing it into the module.
2. Every acceptance scenario in the task text has a test — year-only,
   range-beginning, range-ending (a negative case beyond what the text
   named, since "qualifies for the year it begins in" implies it must *not*
   qualify for the year it ends in), no issued row, and no date row at all.
   The first version of the two positive tests would have passed with no
   filtering applied at all (only one item existed in each), so both gained
   a same-shape decoy item in a different year before being trusted as red.

Verified: `poetry run pytest -q tests/test_ui/test_filters.py` — 27 passed.
`poetry run pytest -q tests/test_ui/test_tables.py -k "sort or order or Order
or Sort or issued or Issued"` — 29 passed (this story's own regression check,
per the task text). `poetry run ruff check`, `ruff format --check`, `mypy
literature/ui/filters.py` and `poetry run deptry .` — all clean.

This is the last task in the brief (T001–T007). Full-suite verification and
the completion report follow.

## 2026-08-20 — US-1/T008 blocked

Implemented T008 exactly as specced — `ItemTableView(MVPTableViewMixin, FilterView)`,
`search_fields = SEARCH_FIELDS`, `filterset_class = ItemFilterSet`, the `actions` override dropped
so the mixin's default `["search", "filter", "create"]` applies — and ran the full suite against
it. Beyond the two D14-named failures, two more went red in `TestItemTableView`, both pre-existing,
neither authored this story: `test_carries_no_search_box_filter_control_or_column_chooser` (FS-009's
lock on search/filter being off — exactly what D-3 reverses) and
`test_column_headers_appear_in_the_required_order` (the filter modal's own "Type" field label now
precedes the table's "Type" column header in the rendered page). Full detail and the concrete
evidence for both are in decisions.md D15.

Reverted the production change (`git checkout -- literature/ui/views.py`) rather than land a red,
untouchable pre-existing test, and reported T008 blocked. T009–T012 depend on T008's composition to
be meaningfully written against, so none were attempted this run.

## 2026-08-20 — US-1/T008 blocked again, on D16's resolution

Resumed per `briefs/us1-search-resume.json`, authority decisions.md D16. Loaded `craft-tdd` and
`craft-increments` by name, read D15/D16 and this story's `tasks.md`/`plan.md` sections, confirmed the
baseline was red on exactly the two D14 tests and nothing else, then implemented T008 exactly as
D16 resolves it: `ItemTableView(MVPTableViewMixin, FilterView)`, `search_fields = SEARCH_FIELDS`,
`filterset_class = ItemFilterSet`, `actions = ["search", "filter", "create"]`, the two `#49` comments
removed, `test_carries_no_search_box_filter_control_or_column_chooser` rewritten to
`test_carries_search_and_filter_but_no_column_chooser` and `test_column_headers_appear_in_the_required_order`
rescoped to the table's own `<thead>`, per D16's own text.

Making the composition actually work required two changes plan D-5 already calls for but no task
states explicitly: removing the view's own inline `issued` `Subquery` (it now double-annotates
against `ItemFilterSet.filter_queryset()`'s own `annotate_issued()`), and overriding
`get_filterset_kwargs()` so the filterset binds on a bare, param-less request too — `FilterMixin`'s
own default (`self.request.GET or None`) leaves an empty `QueryDict` unbound, and an unbound
`FilterSet.qs` never calls `filter_queryset()` at all, silently dropping the `issued` annotation D-5
says must be present "regardless of whether a year was requested".

With all of that in place and the full T008 diff green against every test D14 and D16 name, one
further pre-existing test — untouched, unnamed by either — turned red:
`test_the_queryset_annotates_issued_matching_the_items_own_issued_date`. Full root cause and evidence
in decisions.md D17: routing the view through the shared `annotate_issued()` (as D-5 requires) is
what first exposes that D12's already-committed `output_field=DateTimeField()` typing and this test's
`PartialDate`-equality assumption disagree — a conflict invisible until a consumer other than
`test_filters.py`'s own direct `FilterSet(...)` instantiation actually reads `.issued` back.

Reverted the production change and the D16-authorized test rewrites
(`git checkout -- literature/ui/views.py tests/test_ui/test_views.py`) rather than land this third
red, untouchable pre-existing test, and reported T008 blocked again. T009–T012 depend on T008's
composition to be meaningfully written against, so none were attempted this run.

## 2026-08-20 — US-1/T008 done, on D18's ruling

Resumed per `briefs/us1-search-resume-2.json`, authority decisions.md D16 and D18. Loaded
`craft-tdd` and `craft-increments` by name, read D15–D18 and this story's `tasks.md`/`plan.md`
sections and `literature/ui/filters.py` in full, confirmed the baseline was red on exactly the two
D14 tests and nothing else, then rebuilt T008 directly from D17's description rather than
rediscovering it: `ItemTableView(MVPTableViewMixin, FilterView)`, `search_fields = SEARCH_FIELDS`,
`filterset_class = ItemFilterSet`, the mixin's own `actions` default applying unchanged, the view's
inline `issued` `Subquery` dropped from `get_queryset()`, and `get_filterset_kwargs()` overridden to
bind with `self.request.GET` unconditionally — both production changes D18 states are in scope,
neither a task of its own.

Five pre-existing tests went red against that composition, all five named in D14, D16 or D18's
`amendment.now_in_scope`, and none beyond them:

- `TestItemListView::test_page_holds_no_more_than_paginate_by_items_whatever_the_catalogue_size[literature:item-list]`
  and `TestItemTableView::test_paging_to_the_next_page_renders_the_next_rows_under_the_same_headings`
  (D14) — reinstrumented onto `response.context["table"].page.object_list"` on the table route; the
  card-list parametrisation of the first test keeps reading `object_list`, unchanged.
- `test_carries_no_search_box_filter_control_or_column_chooser` (D16) — rewritten to
  `test_carries_search_and_filter_but_no_column_chooser`, asserting `table_actions == ["search",
  "filter", "create"]` exactly, `name="q"` present, `filterModal` present, closed in both directions.
- `test_column_headers_appear_in_the_required_order` (D16) — instrument moved from the whole
  rendered page to the table's own `<thead>...</thead>` (new helper `table_header_row()`); all six
  headers, same required order.
- `test_the_queryset_annotates_issued_matching_the_items_own_issued_date` (D18) — instrument moved
  from `annotated_item.issued == issued_date.begin` (a `PartialDate` comparison) to
  `annotated_item.issued.date() == issued_date.begin.date` (a calendar-date comparison against the
  raw `DateTimeField` annotation D12 types it as). Still discriminating against the reference's own
  `accessed` date.

Also added one new test of this task's own, `test_the_search_box_submits_through_the_filter_form`
(tasks.md T008, research R4): asserts the literal `name="q" form="filterForm"` and `id="filterForm"`
markup, since R4 records that the search input only submits anywhere once a filterset puts
`filterForm` in context — the acceptance criterion this brief calls "its submit reaches the view".

Verified: `poetry run pytest -q tests/test_ui/test_views.py tests/test_ui/test_filters.py
tests/test_ui/test_tables.py tests/test_ui/test_contributors.py` — 267 passed, 1 xfailed (the
standing D-14/#88 xfail, untouched). `poetry run ruff check`, `ruff format --check` and `mypy
literature/ui/views.py` — all clean. Committed as `T008: ...`.

T009 starts from here.

## 2026-08-20 — US-1/T009 done

New `TestCatalogueSearch` class in `tests/test_ui/test_views.py`, following `TestCatalogueOrdering`'s
own cross-cutting shape rather than nesting inside `TestItemTableView`: one parametrized test over
the five scalar `SEARCH_FIELDS` paths (`citation_key`, `title`, `title_short`, `original_title`,
`container_title`), one test each for the three contributor `Name` paths (family, given, an
organizational `literal`), case-insensitivity with a negative control, a fragment living only in
`abstract` or `keyword` (neither in `SEARCH_FIELDS`) finding nothing, and one reference matching
three searched paths at once still appearing once (FR-005, plan D-4).

No production change — T008 already wired `search_fields = SEARCH_FIELDS`; this task is proving
that wiring end to end. Sanity-checked the suite's power before trusting it: temporarily set
`search_fields = None` on `ItemTableView` and reran — 9 of 11 tests failed for the expected reason
(the two that still passed, case-insensitivity and the once-only assertion, do so because their own
positive assertion holds trivially with no filtering at all; both also carry a same-shape control
elsewhere in the class that does fail unfiltered). Reverted with `git checkout --
literature/ui/views.py` before continuing.

Verified: `poetry run pytest -q tests/test_ui/test_views.py` — 173 passed, 1 xfailed (the standing
D-14/#88 xfail). `poetry run ruff check`, `ruff format --check` and `mypy literature/ui/views.py` —
all clean. Committed as `T009: ...`.

T010 starts from here.

## 2026-08-20 — US-1/T010 done

Four more methods on `TestCatalogueSearch` (FR-006, spec *Edge Cases*): a one-character fragment
matches literally; a term of only spaces is a no-op — the upstream mixin strips and checks
truthiness before filtering, so it falls out of the same path as FR-008's empty-`q` no-op rather
than needing its own; and one test each for `%` and `_`, the database's own multi- and
single-character wildcards.

For the wildcard tests, confirmed the discrimination directly before writing them: an unescaped raw
`LIKE` query against this database (`Item.objects` bypassed, a bare cursor and an unescaped pattern)
matches both the literal reference and a decoy that should not match, while Django's ORM-level
`icontains` — which is what the upstream search mixin actually issues — matches only the literal
one. Django escapes the lookup value before wrapping it in wildcards, so the naive failure mode this
task asks the test to catch is real, and the ORM path already avoids it; the test is the guard that
it goes on doing so, per tasks.md T010's own instruction.

Verified: `poetry run pytest -q tests/test_ui/test_views.py` — 177 passed, 1 xfailed (the standing
D-14/#88 xfail). `poetry run ruff check` and `ruff format --check` — clean. Committed as `T010: ...`.

T011 starts from here.

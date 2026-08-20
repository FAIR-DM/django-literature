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

## 2026-08-20 — US-1/T011 done

Production change (FR-028, plan D-8): `ItemTableView.get_empty_state_heading()` and
`get_empty_state_message()` overridden to check a new `_catalogue_is_narrowed()` — true when the
request's `q` is non-empty or any of `self.filterset.filters`' names carries a non-empty value in
`self.request.GET`. When narrowed, the page shows a new pair of translatable strings
(`no_matches_heading`/`no_matches_message`) instead of the existing `empty_state_heading`/
`empty_state_message`, which stay for a genuinely empty catalogue with no query in force.
Confirmed the wrong message rendered today before writing the fix: a no-results search showed
"Nothing in the catalogue yet" — the empty-*catalogue* copy — with no way to tell it apart from an
actually-empty one.

Read from the raw request rather than from the filterset's own `qs` being empty, since an empty
catalogue with no query and a query that matched nothing can both leave that queryset empty — the
distinction plan D-8 asks for is about whether a query is in force, not about the row count.

Five new `TestCatalogueSearch` tests: the position line states the narrowed count (FR-007, no
production change needed there — django-mvp's own page/paginator republish from T008's D14 fix
already reads the narrowed queryset); the two empty-state messages, each in its own circumstance
and asserted never to appear with the other; and one parametrized test for FR-008 (an empty `q` and
no `q` at all, each restoring the whole catalogue after a preceding search had narrowed it).
Sanity-checked the two empty-state tests against the pre-fix view — the no-matches one failed for
the right reason (wrong message rendered), the genuinely-empty one passed before and after since
that circumstance was already correct.

Verified: `poetry run pytest -q tests/test_ui/test_views.py` — 182 passed, 1 xfailed (the standing
D-14/#88 xfail); `tests/test_ui/test_filters.py tests/test_ui/test_tables.py
tests/test_ui/test_contributors.py` — 105 passed. `poetry run ruff check`, `ruff format --check` and
`mypy literature/ui/views.py` — all clean. Committed as `T011: ...`.

T012 starts from here.

## 2026-08-20 — US-1/T012 done — US-1 complete

Extended `TestItemTableView::test_query_count_does_not_grow_with_row_count` (FR-026) rather than
writing a second guarantee, per the task's own instruction: every item's title now carries the same
term ("Whale Reference") throughout, so the same growing-catalogue sequence that already proves the
unfiltered count is constant goes on to prove it under `?q=whale` too — same catalogue, same
prefetches, one more pair of captures compared against each other.

Sanity-checked the extension's power before trusting it: temporarily dropped
`ItemTableView.get_queryset()`'s `prefetch_related(...)` call to `.prefetch_related()` (no
arguments) and reran — 21 queries against 6, the N+1 the whole test exists to catch. Reverted with
`git checkout -- literature/ui/views.py`.

This is the last task in the brief (T008–T012). Verified: `poetry run pytest -q` (full suite) —
1653 passed, 1 xfailed (the standing D-14/#88 xfail, untouched throughout this story). `poetry run
ruff check`, `ruff format --check`, `mypy literature/ui/views.py` and `poetry run deptry .` — all
clean.

US-1 (#91) is done: T008 rebuilt the composition D17/D18 describe, reinstrumenting the five
pre-existing tests those decisions authorise and none beyond them; T009–T012 build search behaviour,
its edge cases, the no-results message and the query-count guarantee on top of it. Nothing here
touches `literature/ui/filters.py`, a django-mvp template, or a file outside this story's scope.

## 2026-08-20 — US-2/T013 done

No production change: per this story's own brief, `filters.py` (T004–T007) and `ItemTableView`
(T008) already carry every filter this task proves — item type, contributor, issued year and
language — so this task is entirely proving, at the HTTP layer, what `tests/test_ui/test_filters.py`
already proves at the filterset layer directly.

New `TestCatalogueFilters` class, nine tests, in `tests/test_ui/test_views.py`: each filter narrows
on its own against `literature:item-list` (FR-009); item type's `<select>` pairs the stored slug the
query string narrows on with its translated label (FR-010), read from the filter control's own
markup rather than a row's type cell, which would pass even if the control itself broke; contributor
narrows in any role and a reference credited twice is returned once (FR-011); issued year narrows on
a year-only date, a range beginning that year, and excludes an undated reference (FR-012); language
narrows on the stored value and its choices hold only what the catalogue offers (FR-013).

All nine passed on first run, as the brief anticipated — sanity-checked by re-running
`test_type_choices_offer_the_translatable_label_while_the_url_narrows_on_the_stored_value` and
`test_language_choices_offer_only_values_the_catalogue_holds` against a scratch script with the
type/language choices removed from the rendered options before writing the assertions, confirming
each regex genuinely fails to match when the control doesn't offer what it should.

Verified: `poetry run pytest -q tests/test_ui/test_views.py::TestCatalogueFilters` — 9 passed.
`poetry run ruff check`, `ruff format --check` — clean. `mypy literature/ui/views.py` — clean (no
production file touched, but T013's own scope names it). Committed as `T013: ...`.

T014 starts from here.

## 2026-08-20 — US-2/T014 done

Production change, `literature/ui/filters.py`: `type` becomes `django_filters.MultipleChoiceFilter`
(was `ChoiceFilter`) — FR-014 and decisions.md D6 name this filter's own worked example, "articles
or chapters, from 2019", type widened to either value while year narrows what that widened set
returns. `MultipleChoiceFilter.filter()` ORs the chosen values by default (`conjoined=False`), which
is exactly FR-014's widening; no `conjoined` kwarg needed.

**Scope conflict, resolved without touching the file it would have broken.** Confirmed RED first
(`test_more_than_one_value_within_a_filter_widens_to_either` against the untouched `ChoiceFilter`),
then, before committing the field-class change, ran the whole of `tests/test_ui/test_filters.py` —
outside this story's editable scope — and found it breaks `TestItemFilterSetType.test_narrows_to_the_chosen_type`:
that test constructs `ItemFilterSet(data={"type": ItemType.BOOK}, ...)` with a plain `dict` and a
bare stored value, and `SelectMultiple.value_from_datadict` only calls `.getlist()` — always
returning a list — against a real `QueryDict`; against a plain `dict` it falls back to `.get()` and
returns the bare value, which `MultipleChoiceField.to_python()` then rejects as "not a list". A real
HTTP request never hits this, since `self.request.GET` is always a `QueryDict`; only the direct
unit-level construction in the file I cannot edit does.

Fixed at the widget, not the test: `_ScalarOrListSelectMultiple(forms.SelectMultiple)` wraps a bare
string return from `value_from_datadict` in a one-item list, so `data={"type": "book"}` narrows to
exactly one type exactly as the old `ChoiceFilter` did, while a real `QueryDict` carrying two
`type=` values keeps widening to both — verified both directions, and confirmed the full
`tests/test_ui/test_filters.py` (27 tests) still passes unmodified. This is additive input handling
on the filter's own widget, not a change to what a list of values does, so it is not the kind of
test-directed special-casing the brief's prohibitions rule out.

New `TestCatalogueFilterComposition` class, four tests: two `type` values widen to either (FR-014);
two filters narrow to both (FR-015); a filter and a search term narrow to both, with the position
line reflecting the count; and both directions in one request — D6's own "articles or chapters, from
2019" example, `type` widened while `issued_year` narrows what the widened set returns.

Verified: `poetry run pytest -q tests/test_ui/test_filters.py tests/test_ui/test_views.py` — 314
passed, 1 xfailed (the standing D-14/#88 xfail). `poetry run ruff check`, `ruff format --check` —
clean. `mypy literature/ui/filters.py` — clean. Committed as `T014: ...`.

**Concern for the report, not acted on here:** `literature/ui/filters.py` changed outside the two
cases the brief named as plausible (T013's language choices, T016's validation). Stated explicitly
per the prohibition's own instruction, with the reasoning above.

T015 starts from here.

## 2026-08-20 — US-2/T015 done

Read the upstream template first, per the task's own instruction:
`mvp/templates/cotton/page/list/actions/filter.html` renders a badge
(`<span class="indicator-item badge badge-secondary badge-xs">{{ applied_filter_count }}</span>`)
only `{% if applied_filters %}`, and those two context keys are added by
`MVPFilteredListView.get_context_data()` — a class `ItemTableView` never inherits from (plan.md D-2
composes `MVPTableViewMixin, FilterView` directly instead, since no filtered-table equivalent of
`MVPFilteredListView` exists). Confirmed directly: an unfiltered request already left
`response.context["applied_filters"]` at `None`, and a filtered one left it there too — the table
carried a filter control with no badge at all, upstream's own logic simply never reached, not
markup that emits nothing usable. Not a template fork: `ItemTableView.get_context_data()` is our own
view's method, computing the same two keys `MVPFilteredListView` does, so the upstream template
picks them up unmodified.

**A second, real regression found while proving "clearing" (FR-016) and fixed at the same widget
T014 added.** `?type=` (an explicit empty value) used to no-op under the old single-value
`ChoiceFilter` — `Filter.filter()`'s own `EMPTY_VALUES` check — but `MultipleChoiceField.validate()`
has no equivalent allowance for a list holding one empty string, so it now rejected the whole form,
and `BaseFilterView.get()`'s own `strict` handling turned "clear the type filter" into an empty
catalogue instead of the unfiltered one. Caught by `test_clearing_a_filter_restores_the_unfiltered_catalogue[empty-type]`,
red for exactly that reason before the fix. `_ScalarOrListSelectMultiple.value_from_datadict()`
(T014's widget, `literature/ui/filters.py`) now also drops blank entries from the list it returns,
restoring parity with the old single-value behaviour; decisions.md D7 still governs a value that is
actually invalid or actually unmatched, which this is neither of.

New `TestCatalogueFilterVisibility` class, seven tests (one parametrized): no badge when nothing is
applied; one filter counted and badged; two filters both counted; a search term alone carries no
filter badge (django-mvp's own count is filter-only — `q` is not one of `self.filterset.filters`,
so it never reaches `filterset.form.cleaned_data`); the chosen value stays `selected` on the
rendered control; and clearing — an empty `type` and no params at all — each restores the whole
catalogue.

Verified: `poetry run pytest -q tests/test_ui/test_filters.py tests/test_ui/test_views.py
tests/test_ui/test_tables.py tests/test_ui/test_contributors.py` — 307 passed, 1 xfailed (the
standing D-14/#88 xfail). `poetry run ruff check`, `ruff format --check` — clean. `mypy
literature/ui/filters.py literature/ui/views.py` — clean. Committed as `T015: ...`.

T016 starts from here.

## 2026-08-20 — US-2/T016 done — US-2 complete

No production change: confirmed both cases directly against the running view before writing a
single test. `?issued_year=notanumber` and `?language=zz` each already return `200`, an empty
`table.page.object_list`, and the "No references match your search" copy — `BaseFilterView.get()`'s
own `strict` handling (`django_filters/views.py`) sets `self.object_list =
self.filterset.queryset.none()` whenever the bound form is invalid, and an unmatched value is simply
a filter matching no row. Neither needs a line of `literature/ui/filters.py` changed, contrary to
that file being named a "plausible case" for this task in the brief's own prohibitions — stated here
as the brief itself asks.

New `TestCatalogueFilterValidation` class, four tests: the unmatched case, the invalid case, both
confirmed never to fall back to the unfiltered catalogue, and — per the task's own instruction — an
address carrying a key `ItemFilterSet` does not declare, pinned as what actually happens (`200`, the
catalogue unnarrowed) rather than as a rejection this feature does not build. FR-017 reads on a
filter *value*, not an undefined key.

This is the last task in the brief (T013–T016). Verified: `poetry run pytest -q` (full suite) — 1677
passed, 1 xfailed (the standing D-14/#88 xfail, untouched throughout this story — 24 more passing
tests than US-1's own 1653, matching T013's 9, T014's 4, T015's 7 and T016's 4). `poetry run ruff
check .`, `ruff format --check .`, `mypy literature/ui/filters.py literature/ui/views.py` and
`poetry run deptry .` — all clean.

US-2 (#92) is done: T013 proved the four filters already configured in the foundational phase reach
an HTTP request; T014 added the one production change this story required beyond what was
foreseen — `type` widening to several values (FR-014, decisions.md D6's own worked example) — and
found and fixed a real regression its own widget introduced for clearing an empty value, caught by
its own test before it shipped; T015 found and closed a second real gap, `ItemTableView` never
carrying the badge context django-mvp's own template expects; T016 proved FR-017 already holds.
Nothing here touches a django-mvp template, `tests/test_ui/test_filters.py`, or a file outside this
story's scope.

## 2026-08-20 — US-3/T017 done — #88 closed

Removed the `strict=True` xfail from
`TestCatalogueOrdering::test_sort_survives_following_the_rendered_link_to_page_2` first, alone, to
observe the marker's own claim: red, `assert 'Key029' < 'Key006'`, second page falling back to the
catalogue's default order — the exact symptom decisions.md D13 diagnoses, not an import or fixture
error. Confirmed the diagnosis directly before touching the helper: a request carrying
`?sort=-citation_key` renders the page-2 link as `href="?sort=-citation_key&amp;page=2"`, and
`rendered_page_link()` returned that byte for byte, so the test client parsed two parameters named
`sort` and `amp;page` and no `page` value ever reached the view.

Fix: one line, `html.unescape()` on the href `rendered_page_link()` returns. Green on that line
alone — the test's own assertion and fixture untouched, exactly as D13 specifies. `git diff` before
committing confirms nothing else in the test changed beyond the marker's removal and the helper's
one line.

**The demo guard's regex — confirmed, not assumed, per the task.** `SECOND_PAGE_LINK_RE` matches a
literal `&` between parameters; the real markup joins them with the HTML entity `&amp;`, and a
direct check (`SECOND_PAGE_LINK_RE.search('href="?sort=-citation_key&amp;page=2"')`) returns `None`
— the pattern would *not* match a page-2 link that carries a sort. It needs no change regardless:
`DemoWalk.run()` fetches `{base_url}/catalogue/` with no query string at all before it ever reads
this link, so the rendered href it actually parses is the bare `?page=2` — no ampersand, escaped or
not — and the pattern matches that correctly today and after this fix. Recorded here rather than
touched, since nothing in this story's scope exercises the escaped-ampersand path against the guard.

Two assertions plan.md D-10 named for this task, `tests/test_ui/test_views.py`'s
`'href="?page=2"' in content` (now at lines 136 and 357, not the 119/340 the plan cites — line
numbers moved under earlier stories' commits), needed no change either: both are requests with no
sort or filter in force, so the fixed component's rendered link is still the bare `?page=2` — D-10's
"becomes what the fixed component emits" and "stays exactly what it already pins" coincide here
because neither test puts a second parameter in force. Confirmed by reading both tests, not assumed.

Verified: `poetry run pytest -q tests/test_ui/test_views.py::TestCatalogueOrdering` — 9 passed, the
xfail gone with nothing skipped in its place. `poetry run pre-commit run --files
tests/test_ui/test_views.py` — clean. Committed as `T017: ...`.

T018 starts from here.

## 2026-08-20 — US-3/T018 done

No production change: search and a filter each already survived a page move once T017's helper
correction was in place to prove it, the same way T017 itself found no production defect once the
0.19.1 floor was already carrying the pagination fix.

New `TestCatalogueStateSurvivesAPageMove`, three tests, each following the page's own rendered link
via `rendered_page_link()`: a search alone, a filter alone, and a search, a filter and a sort all
three together. Each asserts on the second page's own results, not the link — and each also asserts
the second page's rows are disjoint from the first's, not merely narrowed the same way. That
disjointness check earned its place directly: without it, the first two tests passed even with
T017's helper fix reverted, because a `?page=2` misread as the literal parameter `amp;page` falls
back to page one, and page one's own rows already satisfy "still narrowed" without ever proving a
page move happened. Reverted the fix, watched the (initially weaker) tests fail for the wrong
reason — a false pass — added the disjointness assertion, reverted again, watched all three fail for
the right reason this time, then restored the fix and confirmed green. The third (combined) test
did not need the same strengthening: its own descending-order boundary assertion already fails under
the same fallback, confirmed the same way.

Also corrected a stale comment on `TestCatalogueOrdering`'s own sort-survival test (T017's
`test_sort_survives_following_the_rendered_link_to_page_2`): it still read "fails today because…",
describing the pre-T017 defect on a test that now passes. One line, no assertion touched.

Verified: `poetry run pytest -q tests/test_ui/test_views.py::TestCatalogueStateSurvivesAPageMove
tests/test_ui/test_views.py::TestCatalogueOrdering` — 12 passed. `poetry run pre-commit run --files
tests/test_ui/test_views.py` — clean (one lint fix taken: an unused loop variable in the filter
test, replaced with `ItemFactory.create_batch`). Committed as `T018: ...`.

T019 starts from here.

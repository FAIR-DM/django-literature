# Tasks — 010 Find a reference in a large catalogue

**Branch**: `010-search-and-filter-catalogue` · **Spec**: [`spec.md`](spec.md) · **Plan**: [`plan.md`](plan.md)

Test-first throughout (Article I): each task writes its test, watches it fail for the right reason,
then makes it pass. A task's test scope is one class or one file; the full suite runs once per story,
at the story's last task.

`[P]` marks tasks that may run in parallel with the others carrying the same marker in the same
phase — different files, no shared state.

---

## Phase 1 — Foundational (blocking; nothing else starts until this is green)

- [ ] **T001** Raise the `ui` extra in `pyproject.toml`: django-mvp `>=0.19.1,<1.0` (from `>=0.19`,
  research R6) and add `django-filter (>=25.1,<26)` — confirm the current major on the package index
  before pinning — both under the existing `python_version >= '3.12'` marker. Update the exact-list
  assertion in `tests/test_ui/test_packaging.py::test_the_ui_extra_is_exactly_the_front_end_packages`
  in the same commit; it pins the extra's contents by design (research R7). Leave
  `project.dependencies` untouched: the core gains nothing. Confirm `deptry` needs no entry in
  `[tool.deptry.package_module_name_map]` — the distribution is `django-filter` and the module is
  `django_filters`, which is exactly the mismatch that map exists for, so check rather than assume.
  *Test scope:* `tests/test_ui/test_packaging.py`.

- [ ] **T002** `poetry lock` and install. The lock pins django-mvp 0.19.0 today, so this is a real
  resolution, not a formality. Record the resolved django-mvp and django-filter versions in
  `progress.md`.

- [ ] **T003** Add `"django_filters"` to `INSTALLED_APPS` in `tests/settings.py` and
  `demo/settings.py`, unconditional in both, and to the installation documentation alongside
  `django_tables2`. Add `django_filters` to `FORBIDDEN_ROOTS` in `tests/test_ui/test_architecture.py`
  so the core is provably free of it, and confirm the AST scan still passes.
  *Test scope:* `tests/test_ui/test_architecture.py`, `tests/test_ui/test_smoke.py`.

- [ ] **T004** Create `literature/ui/filters.py` with `SEARCH_FIELDS` — the eight ORM paths from
  plan D-3 — and nothing else yet. Add `tests/test_ui/test_filters.py` asserting the list's contents
  and that every path resolves against the model, so a renamed field fails here rather than as a
  silently empty search.
  *Test scope:* `tests/test_ui/test_filters.py`.

- [ ] **T005** Add `ItemFilterSet` to `literature/ui/filters.py`: item type, contributor, issued year
  and language (FR-009 to FR-013). Item type offers translatable labels and narrows on the stored
  value; language offers the distinct values the catalogue holds, computed per request, and offers
  none that no reference carries; contributor matches family, given or literal in any role; the year
  filter is added in T007. Every label translatable (Article VIII).

  `language` is free text and blank for most references today, so the distinct-values query returns
  the empty string as one of its values. The empty string is not a language the catalogue holds:
  exclude it, so the filter never offers a blank choice beside its own "any" option, and assert that.
  *Test scope:* `tests/test_ui/test_filters.py`.

- [ ] **T006** Make the filtered queryset return each reference once (plan D-4, FR-005, FR-011).
  The search path is already deduplicated upstream — the mixin's own query ends in `.distinct()` — so
  this task's subject is the filter path, and the search side of it is a guard that upstream goes on
  doing what it does. Assert the single occurrence directly — a reference credited to one contributor
  in two roles, and a
  multi-value filter matching two related rows — never that `.distinct()` was called. Run the table's
  existing sort tests as part of this task's check: distinct combined with an ordering on an
  annotation is where this breaks quietly.
  *Test scope:* `tests/test_ui/test_filters.py`, plus the existing table sort tests.

- [ ] **T007** Move FS-009's `issued` subquery annotation into the shared definition and add the year
  filter on it (plan D-5, FR-012). A year-only stored date qualifies, a range qualifies for the year
  it begins in, and a reference with no `issued` row is excluded. The annotation lives in
  `literature/ui/filters.py` and is applied from there — one place, not restated in each view's
  `get_queryset()` — and the table's existing sort on `issued` must still pass.
  *Test scope:* `tests/test_ui/test_filters.py`.

## Phase 2 — US-1 #91 · Search the catalogue for a reference

- [ ] **T008** `ItemTableView` becomes `MVPTableViewMixin, FilterView` (plan D-2), takes
  `search_fields = SEARCH_FIELDS` and `filterset_class = ItemFilterSet`, and its `actions` regain
  `"search"` and `"filter"` beside `"create"` (plan D-3). Delete the two comments naming this issue as
  the reason they were switched off. Assert the search box renders and, because the filterset is now
  configured, that its submit actually reaches the view (research R4).
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T009** Search behaviour against the table, one assertion per searched field: title, short
  title, original title, container title, citation key, a contributor's family name, a contributor's
  given name, and an organizational literal name (FR-002). Case-insensitive (FR-003). A fragment
  living only in an abstract or a keyword finds nothing (FR-004). A reference matching in several
  fields at once appears once (FR-005).
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T010** Edge cases of the search term (spec *Edge Cases*, FR-006): a one-character fragment, a
  term of only spaces, and a term containing the characters the database treats as pattern syntax —
  matched as literal text, not as wildcards. Write the wildcard test to fail against a naive
  implementation before confirming the upstream mixin already handles it: if it does, the test stays
  as the guard that it goes on doing so.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T011** The result count and the no-results message (FR-007, FR-028, FR-030, plan D-8). The
  count states how many references matched; a search matching nothing says so, keeps the search box
  and the filters on the page, and does not show the empty-catalogue message. Assert both messages
  appear in their own circumstance and never together. Translatable strings.

  Also FR-008, which no other task covers: clearing the search restores the unnarrowed catalogue.
  Assert that a request carrying an empty `q`, and a request carrying no `q` at all, each return the
  whole catalogue where the preceding search had narrowed it. Upstream's search mixin already no-ops
  on an empty term, so this is a guard on behaviour that should already hold — which is exactly what
  it is for.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T012** The query-count guarantee under search (FR-026): a page of results costs a constant
  number of queries regardless of how many results there are. Extend the existing guarantee rather
  than writing a second one. Run the full suite — last task of the story.
  *Test scope:* `tests/test_ui/test_views.py`, then the whole suite.

## Phase 3 — US-2 #92 · Narrow the catalogue

- [ ] **T013** Each filter on its own against the table (FR-009 to FR-013): item type narrows to that
  type; contributor narrows to references crediting them in any role; issued year behaves as T007
  specified; language narrows on the stored value and its choices are only values the catalogue holds.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T014** Composition (FR-014, FR-015): two values within one filter widen to either; two
  filters narrow to both; a filter and a search term narrow to both, and the count reflects it.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T015** What is in force is visible on the page and clearable from it (FR-016). django-mvp
  supplies `applied_filters` and `applied_filter_count` for the badge; clearing is ours to confirm
  reaches the unfiltered catalogue.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T016** Invalid and unmatched filter values (FR-017, plan D-1), which is two cases and only
  two: an unmatched value of a declared filter (`?language=zz`), and an invalid value of a declared
  filter (`?year=notanumber`). Each reports no matches — never an error, never a fall back to the
  unfiltered catalogue. Both work through the adopted components: an unmatched value narrows to
  nothing, and an invalid one fails the filterset form's validation, which under `strict` returns an
  empty queryset.

  **An address carrying a key the filterset does not define is not one of these cases.** A Django
  form ignores data it has no field for, so such an address is simply ignored and the catalogue comes
  back unnarrowed. FR-017 reads on a filter *value*, not an undefined key, and making an unknown key
  fail would mean building a rejection mechanism nothing asks for and then allowlisting `q`, `page`
  and the sort back through it. If it is worth pinning at all, pin what actually happens — the page
  returns 200 and does not raise — and say so.

  Run the full suite — last task of the story.
  *Test scope:* `tests/test_ui/test_views.py`, then the whole suite.

## Phase 4 — US-3 #93 · State survives a page move

- [ ] **T017** With the floor raised in T001, move the two assertions pinning `href="?page=2"` exactly
  (`tests/test_ui/test_views.py` lines 119 and 340) to what the fixed component emits (plan D-10,
  research R6). The demo guard's regex needs no change — confirm that rather than assuming it.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T018** Survival across a page move (FR-018): a search, a filter and a sort each survive
  individually, and all three survive together. These are the tests that close #88, so they assert the
  state is still in force on the second page, not merely that a link changed shape.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T019** A search and filters survive a change of sort, and the sort applies to what they
  narrowed (FR-019). This is the direction that works today; pin it before T020 touches the form.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T020** The sort survives a change of filter (plan D-7, research R5). Carry the sort as a
  hidden field on `ItemFilterSet`'s own form, populated from the request, so it is rendered from
  `filter.form` and no upstream template is touched. **Do not file an upstream issue for this** —
  that component is already being worked on upstream (Sam, 2026-08-20).

  **Assert that an active sort does not get reported as a filter.** django-mvp counts every non-empty
  entry in the filterset form's cleaned data as an applied filter and badges the Filter button with
  the count, so a hidden sort field lands there unless the view's applied-filter reporting drops the
  sort key. The test is that the badge and the list of what is in force are identical with and
  without a sort in force — otherwise the measure misstates both halves of FR-016.

  **Abort conditions, and they are not negotiable:** if either the hidden field or the
  applied-filter correction cannot be done without overriding an upstream template or block, stop,
  spend no further time on it, and document the limitation in the README instead. Nothing in the
  specification requires this, so abandoning it is a clean outcome, not a failure. Report which of
  the two happened.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T021** A narrowed catalogue can be bookmarked and reopened to the same result (FR-022,
  SC-004). Run the full suite — last task of the story.
  *Test scope:* `tests/test_ui/test_views.py`, then the whole suite.

## Phase 5 — US-4 #94 · The card list too

- [ ] **T022** `ItemListView` becomes `MVPFilteredListView` (plan D-2) with the same
  `search_fields` and `filterset_class`. Delete its two comments naming this issue.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T023** The contributor page keeps neither control (plan D-6, FR-025). It subclasses the card
  list, so T022 would otherwise hand it a search box and four filters.

  **Overriding the attributes back off is not the mechanism, and does not work.** Leaving
  `filterset_class` unset on a subclass of a filtered view does not disable filtering — `FilterMixin`
  defaults `filterset_fields` to every field, so `get_filterset_class()` generates a filterset over
  the whole of `Item`, which raises on its `JSONField`s and 500s the page. Do not reach for it.

  What this task does instead is move the inheritance: extract the card-list configuration
  `ItemListView` and `ContributorDetailView` share — `list_item_template`, `get_queryset`'s
  prefetching, `get_model_info`, the `contributor_groups` annotation in `get_context_data`, and the
  directory and CRUD wiring — into one mixin carrying no base class of its own. `ItemListView`
  becomes that mixin plus `MVPFilteredListView` (T022); `ContributorDetailView` becomes that mixin
  plus the plain `MVPListView`. Each of the two keeps every attribute it declares for itself today.

  Assert behaviour, not structure: the contributor page returns 200, renders neither the search box
  nor the Filter button, and every existing contributor-page test passes unchanged. A task of its own
  so it cannot be lost inside T022.
  *Test scope:* `tests/test_ui/test_contributors.py`.

- [ ] **T024** The two presentations agree (FR-024, SC-005): the same search term and the same filters
  return the same references from both. Parametrise over both routes rather than writing it twice.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T025** One definition, asserted structurally (FR-023, plan D-1): both views read
  `SEARCH_FIELDS` and `ItemFilterSet` from `literature.ui.filters` rather than declaring their own.
  A search or filter surviving a page move on the card list (FR-018 on this presentation). Run the
  full suite — last task of the story.
  *Test scope:* `tests/test_ui/test_architecture.py`, `tests/test_ui/test_views.py`, then the whole suite.

## Phase 6 — US-5 #95 · The demo, and the documentation

- [ ] **T026** Seed language values across several distinct languages in
  `demo/seed/catalogue.json` (plan D-11, research R8) — not one of the 28 entries carries one today,
  so the language filter would render an empty control. Keep every existing entry valid; the seed
  command fails loudly on a partial load, and `tests/test_demo/test_seed.py` guards the count.
  *Test scope:* `tests/test_demo/test_seed.py`.

- [ ] **T027** Settle how the guard reaches a second page of a narrowed result at a page size of 24
  over 28 references (plan D-11): either the narrowing is broad enough to leave more than 24, or the
  seed grows. State which in `decisions.md`.
  *Test scope:* `tests/test_demo/test_smoke.py`.

- [ ] **T028** The guard walks a search, a filter, and a page move over a narrowed result
  (FR-033), asserting on what came back each time rather than on a status code. Break each of
  the three in turn and confirm the guard fails — a guard that cannot fail is not a guard.
  *Test scope:* `tests/test_demo/test_smoke.py`, `demo/smoke.py`.

- [ ] **T029** README (FR-034, plan D-12): the front-end section gains what the search matches, what
  it deliberately does not, what each filter narrows on, and how the three compose with sorting and
  pagination. **Delete the paragraph describing the pagination limitation and pointing at #88** — this
  feature removes it, and a stale limitation is worse than no documentation. CHANGELOG entry in the
  same change. Humanize before commit; no internal handles.
  *Test scope:* `tests/test_documentation.py`.

- [ ] **T030** Full verification: whole suite, lint, type check, `deptry`, `makemessages` clean, the
  demo migrates and its pages render. Last task of the feature.
  *Test scope:* everything.

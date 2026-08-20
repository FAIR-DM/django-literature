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
  *Test scope:* `tests/test_ui/test_filters.py`.

- [ ] **T006** Make the filtered queryset return each reference once (plan D-4, FR-005, FR-011).
  Assert the single occurrence directly — a reference credited to one contributor in two roles, and a
  multi-value filter matching two related rows — never that `.distinct()` was called. Run the table's
  existing sort tests as part of this task's check: distinct combined with an ordering on an
  annotation is where this breaks quietly.
  *Test scope:* `tests/test_ui/test_filters.py`, plus the existing table sort tests.

- [ ] **T007** Move FS-009's `issued` subquery annotation into the shared definition and add the year
  filter on it (plan D-5, FR-012). A year-only stored date qualifies, a range qualifies for the year
  it begins in, and a reference with no `issued` row is excluded. Both views carry the annotation
  after this task; the table's existing sort on `issued` must still pass.
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

- [ ] **T011** The result count and the no-results message (FR-007, FR-030, plan D-8). The count
  states how many references matched; a search matching nothing says so, keeps the search box and the
  filters on the page, and does not show the empty-catalogue message. Assert both messages appear in
  their own circumstance and never together. Translatable strings.
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

- [ ] **T016** Invalid and unmatched filter values (FR-017, plan D-1): a value matching no reference,
  and a value that is not valid at all, each report no matches — never an error, never a fall back to
  the unfiltered catalogue. Include a hand-edited address carrying a filter key the filterset does not
  define. Run the full suite — last task of the story.
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
  that component is already being worked on upstream (Sam, 2026-08-20). **Abort condition, and it is
  not negotiable:** if this cannot be done without overriding an upstream template or block, stop,
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

- [ ] **T023** The contributor page holds the controls off (plan D-6, FR-025). It subclasses the card
  list, so it inherits them unless it says otherwise: set `search_fields = None` and no filterset, and
  assert the contributor page renders neither control and is otherwise unchanged. A task of its own so
  it cannot be lost inside T022.
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
  (FR-033, FR-035), asserting on what came back each time rather than on a status code. Break each of
  the three in turn and confirm the guard fails — a guard that cannot fail is not a guard.
  *Test scope:* `tests/test_demo/test_smoke.py`, `demo/smoke.py`.

- [ ] **T029** README (FR-036, plan D-12): the front-end section gains what the search matches, what
  it deliberately does not, what each filter narrows on, and how the three compose with sorting and
  pagination. **Delete the paragraph describing the pagination limitation and pointing at #88** — this
  feature removes it, and a stale limitation is worse than no documentation. CHANGELOG entry in the
  same change. Humanize before commit; no internal handles.
  *Test scope:* `tests/test_documentation.py`.

- [ ] **T030** Full verification: whole suite, lint, type check, `deptry`, `makemessages` clean, the
  demo migrates and its pages render. Last task of the feature.
  *Test scope:* everything.

# Tasks — 009 A tabular catalogue view

**Branch**: `009-tabular-catalogue-view` · **Spec**: [`spec.md`](spec.md) · **Plan**: [`plan.md`](plan.md)

Test-first throughout (Article I): each task writes its test, watches it fail for the right reason,
then makes it pass. A task's test scope is one class or one file; the full suite runs once per story,
at the story's last task.

`[P]` marks tasks that may run in parallel with the others carrying the same marker in the same
phase — different files, no shared state.

---

## Phase 1 — Foundational (blocking; nothing else starts until this is green)

- [ ] **T000** Blocking, and it lives in django-mvp rather than here (plan D-14). The pagination
  component's page links replace the whole query string, so a chosen sort is discarded on every page
  move and FR-016 cannot be met. Fix it at its source — the component preserves the current query
  string and replaces only the page key — land it in that repository, and note the released version
  here. Everything else in this feature can proceed while it is in flight. T001 and T025 are the two
  tasks that cannot close without it.

- [ ] **T001** Raise the `ui` extra in `pyproject.toml`: django-mvp `>=<the T000 release>,<1.0` (from
  `>=0.17`) and django-tables2 `>=3.0,<4`, both under the existing `python_version >= '3.12'` marker.
  Update the two exact-list assertions in `tests/test_ui/test_packaging.py`
  (`TestNoDemoOnlyDependencyEntersTheBuild`) in the same commit — they pin the extra's contents by
  design. Rename `test_the_ui_extra_is_exactly_django_mvp`: it stops describing its own assertion
  once the extra holds two packages. Leave `project.dependencies` untouched: the core gains nothing.
  Confirm `deptry` needs no entry in `[tool.deptry.package_module_name_map]`.
  *Test scope:* `tests/test_ui/test_packaging.py`.

- [ ] **T002** `poetry lock` and install, so django-tables2 is resolvable. Record the resolved
  django-tables2 and django-mvp versions in `progress.md`.

- [ ] **T003** Add `"django_tables2"` to `INSTALLED_APPS` in `tests/settings.py` and
  `demo/settings.py`. Unconditional in both — the `ui` extra installs it. Add `django_tables2` to
  `FORBIDDEN_ROOTS` in `tests/test_ui/test_architecture.py` so the core is provably free of it, and
  confirm the existing AST scan still passes.
  *Test scope:* `tests/test_ui/test_architecture.py`, `tests/test_ui/test_smoke.py`.

---

## Phase 2 — US-1: Read the catalogue as a table (P1)

Delivers FR-001 through FR-012 and FR-021. At the end of this phase the catalogue is a table.

- [ ] **T004** Create `literature/ui/tables.py` with `ItemTable` and its `Meta`:
  `model = Item`, `template_name = "django_tables2/bootstrap5-mvp.html"`, `empty_text` set (a flag,
  not a displayed string — without it the mvp empty state never renders, research R5), `default` set
  to the translatable empty-value marker FR-010 asks for, **no `order_by`** (it would name a column
  that does not exist and be silently dropped; newest-first comes from `Item.Meta.ordering`, plan
  D-3), and no `fields` entry so every column is declared explicitly. Add the four plain columns —
  `citation_key`, `type`, `container_title` and a placeholder `title` — with `gettext_lazy` verbose
  names, the per-column width classes plan D-5 lists (the project-wide default is no-wrap with no
  maximum, so a long container title stretches the table sideways until a column says otherwise),
  and a class docstring naming the prefetch its rows require (plan D-3).
  *Test scope:* new `tests/test_ui/test_tables.py`, class `TestItemTableMeta` — including that the
  default order is newest-first through a rendered page rather than through the absent setting.

- [ ] **T005** The title column: `Column(empty_values=(), order_by="title", linkify=("literature:item-detail", {"pk": A("pk")}), attrs={"a": {"class": "link link-hover"}})` plus
  `render_title` returning the first of `title`, `title_short`, `original_title`, `volume_title`,
  `citation_key`. `empty_values=()` is mandatory or the renderer never runs on the empty title that
  the chain exists for (research R3). The cell must not truncate (D-5).
  *Test scope:* `tests/test_ui/test_tables.py`, class `TestTitleColumn` — one case per rung of the
  chain, plus the link target and its classes.

- [ ] **T006** The item-type column: `Column(order_by="type")` and nothing else. No renderer —
  django-tables2 resolves a choice field through `get_FOO_display()` before any renderer runs, so the
  translated label arrives on its own while ordering stays on the stored value (FR-005, FR-017).
  Record that in a comment so it is not re-added.
  *Test scope:* `tests/test_ui/test_tables.py`, class `TestTypeColumn` — the assertion is unchanged
  and still worth making; it pins behaviour the library provides.

- [ ] **T007** The credited-names column: `TemplateColumn` over a new
  `literature/ui/templates/literature/ui/_table_contributors.html`, with `empty_values=()` and
  `orderable=False`. `render_contributors` selects the values only — reading the `contributors`
  attribute the view's prefetch places, authors if any, else editors, first three, and the count of
  the rest — and the template builds the links. **No markup is built in Python and nothing is passed
  through `mark_safe`**: a contributor's name is free text from an open write page, and this is the
  package's default page (plan D-6, Article V). Never touch the manager (research R9). Suffix under
  `blocktrans count`; the no-contributors case renders the empty-value marker, since
  `empty_values=()` means the table's own marker is unreachable.
  *Test scope:* `tests/test_ui/test_tables.py`, class `TestContributorsColumn` — authors, the editor
  fallback, neither (asserting the marker), exactly three, more than three, the link targets, and a
  name containing markup rendering escaped.

- [ ] **T008** [P] The issued column: `_table_issued.html`, a thin wrapper that selects the `issued`
  slot off the record and includes `_date_value.html` under the `item_date` name the partial expects,
  plus a `TemplateColumn` over it. The rendering rule stays in the one shared partial (research R8).
  Ships `orderable=False` — the annotation and `order_issued` that make the sort resolvable do not
  land until T017/T018, and a header advertising a sort before then raises `FieldError` on the
  package's default page. T018 switches it on.
  *Test scope:* `tests/test_ui/test_tables.py`, class `TestIssuedColumn` — year only, year and month,
  a range, a literal date, and no issued date at all, which renders the empty-value marker.

- [ ] **T009** Add `ItemTableView` to `literature/ui/views.py` per plan D-2: `paginate_by = 24`
  explicitly (the mixin sets none, and without it the footer bar disappears — research R4),
  `actions = ["create"]`, `search_fields = None`, the create action, `crud_views = CRUD_VIEWS`, the
  page title and the empty-state strings, and a `get_queryset()` carrying **both** prefetches —
  `Prefetch(..., to_attr="contributors")` that T007 depends on, and `item_dates`, which T008's cell
  walks for the whole `ItemDate` row and which the annotation cannot supply. Omitting the second is
  one query per row and fails T012. No `order_by` — the mixin refuses one.
  *Test scope:* `tests/test_ui/test_views.py`, new class `TestItemTableView`.

- [ ] **T010** Point the `item-list` route at `ItemTableView` in `literature/ui/urls.py`. The route
  name does not change, so every breadcrumb, `success_url` and `crud_views` entry naming it keeps
  working. Extend `tests/test_ui/test_urls.py` to cover the new default and to keep asserting every
  shown action reverses.
  *Test scope:* `tests/test_ui/test_urls.py`.

- [ ] **T011** Re-point the card's tests rather than deleting them (plan D-11). Add a second route in
  `tests/urls.py` serving `ItemListView`, move `TestCatalogueListReadability` onto it unchanged, and
  split `TestItemListView` so that assertions both presentations owe — ordering, page size, the
  position line, the out-of-range 404, the empty state, the create action — are made against both.
  No assertion is loosened or removed.
  *Test scope:* `tests/test_ui/test_views.py`.

- [ ] **T012** The constant-query-count guarantee for the table (FR-012): assert the query count is
  identical for a small page and a full one, using `CaptureQueriesContext` as the existing card test
  does. This is what proves T007's prefetch is actually being read rather than the manager.
  *Test scope:* `tests/test_ui/test_views.py`, class `TestItemTableView`.

- [ ] **T013** Full suite, lint, type check, `deptry`, and the template guards
  (`tests/test_ui/test_templates.py` sweeps the two new partials automatically). Story exit.

---

## Phase 3 — US-2: Edit a reference without opening it (P2)

Delivers FR-019 and FR-020.

- [ ] **T014** `_table_actions.html`: the row's edit control, linking to `literature:item-update` for
  the record, with translatable text. Reuse the same control idiom the reference page uses; introduce
  no new styling.
  *Test scope:* covered by T015 and by the template guards.

- [ ] **T015** The actions column: `TemplateColumn(template_name="literature/ui/_table_actions.html", orderable=False, verbose_name="")`. `orderable=False` is what earns the column its centred
  alignment as well as what FR-015 asks for (research R6). Assert the control's target, that its
  visibility follows the same `show_update_action` mechanism the reference page uses, and that no
  permission check is introduced.
  *Test scope:* `tests/test_ui/test_tables.py`, class `TestActionsColumn`;
  `tests/test_ui/test_views.py` for the visibility flag.

- [ ] **T016** Full suite and gates. Story exit.

---

## Phase 4 — US-3: Order the catalogue by a column (P3)

Delivers FR-013 through FR-018.

- [ ] **T017** Annotate the issued date in `ItemTableView.get_queryset()` with a `Subquery` over
  `ItemDate` filtered to `date_type="issued"` — not a join filter, which risks row multiplication and
  interferes with the paginator's count (research R7).
  *Test scope:* `tests/test_ui/test_views.py`, class `TestItemTableView`.

- [ ] **T018** `order_issued(queryset, is_descending)` on `ItemTable`, returning `(queryset, True)`
  with `nulls_last=True` in both directions, `order_by="issued"` on the column, and the column's
  `orderable=False` from T008 removed now that the annotation exists. django-tables2 does nothing
  about NULLs, and SQLite and PostgreSQL place them differently, so FR-018 has to be stated in code
  (research R7).
  *Test scope:* `tests/test_ui/test_tables.py`, class `TestIssuedOrdering`.

- [ ] **T019** Sorting from an HTTP request: assert that `?sort=` reorders the whole catalogue rather
  than the current page, that the direction reverses on a second request, that the order survives
  moving to page 2 **by following the rendered page link rather than by constructing the address**
  (T000 is what makes that pass — a constructed URL would assert nothing about the link the reader
  clicks), and that `?sort=contributors` and `?sort=actions` are refused. Cover all five sortable
  columns.
  *Test scope:* `tests/test_ui/test_views.py`, class `TestCatalogueOrdering`.

- [ ] **T029** [P] Assert FR-025 rather than only configuring it: the rendered table page carries no
  search box, no filter control and no column chooser. The argument for naming those out in the view
  is that an upstream default could reintroduce one, which is an argument for a test.
  *Test scope:* `tests/test_ui/test_views.py`, class `TestItemTableView`.

- [ ] **T020** Full suite and gates. Story exit.

---

## Phase 5 — US-4: Keep the card list (P4)

Delivers FR-022, FR-023, FR-024 and FR-027.

- [ ] **T021** Assert the promise directly: `ItemListView` is importable from `literature.ui.views`,
  routing a URL at it renders cards with pagination, the empty state and the create action intact,
  and the contributor page still presents cards. Assert too that no template is copied out of the
  package to do it.
  *Test scope:* `tests/test_ui/test_views.py`, class `TestTheCardListStaysAvailable`.

- [ ] **T022** [P] README: extend the front-end section to name both presentations, say which is
  served by default, show the one-line routing change that selects the other, add `"django_tables2"`
  to the installation block a host copies verbatim (research R11), and state that ordering by item
  type follows the stored type rather than the translated label. FR-017 asks for that in the
  documentation, and the README is where a reader looking at the table will be — the CHANGELOG is
  not documentation.

- [ ] **T023** [P] CHANGELOG entry describing the change of default, the new dependency and the
  routing change that restores the previous page, plus the note that ordering by item type follows
  the stored type rather than the translated label (FR-017).

- [ ] **T024** Full suite and gates. Story exit.

---

## Phase 6 — US-5: The demo shows the table, and a broken one is caught (P5)

Delivers FR-028.

- [ ] **T025** Confirm the demo serves the table at `catalogue/` over its seed references. The
  item-link pattern survives untouched (research R4). The pagination pattern does not: `demo/smoke.py`
  pins the literal `href="?page=2"`, and T000's fix makes that link carry the rest of the query
  string, so the guard has to match a page link that is no longer bare. Repair it, and keep the
  guard's rule that it constructs no address of its own.
  *Test scope:* `tests/test_demo/test_smoke.py`.

- [ ] **T026** Extend `demo/smoke.py`: reach an edit form by following a row's own edit control on
  the list page, rather than only from the reference page. Keep the guard's rule that it constructs
  no address of its own. Add the matching unit coverage for the new pattern.
  *Test scope:* `tests/test_demo/test_smoke.py`.

- [ ] **T027** Run the guard against a live demo, both green and deliberately broken (a row whose
  link is removed), and confirm it fails with a message naming what it could not reach.

- [ ] **T028** Full suite, all gates, `makemessages` clean. Story exit.

---

## Dependencies

- T000 is in another repository and runs in parallel with everything. Only T001 and T025 wait on it.
- Phase 1 blocks everything.
- T004 blocks T005–T008. T007 depends on T009's prefetches, so T009 lands with or before T007's test
  turning green; take them as one unit if the ordering fights you. T008 depends on the same T009 for
  its `item_dates` prefetch.
- T010 breaks the card tests by design, so T011 is in the same commit as T010.
- Phase 4's T018 depends on T017's annotation and removes the `orderable=False` T008 shipped.
- Phase 6 depends on Phases 2 and 3 being complete.

## Out of scope, deliberately

Search, filtering and result ordering controls (#49). User-configurable columns and column order.
Any model change, field or migration. Any permission or access control. The contributor page
becoming a table.

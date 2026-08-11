# Tasks: Browse the Reference Catalogue in an Opt-In Front End

**Feature**: `006-browse-reference-catalogue` · **Spec**: `spec.md` · **Plan**: `plan.md`

Article I is Test-First: within every task the test is written and seen to fail before the code that
makes it pass. `[P]` marks tasks that may run in parallel with their siblings — different files, no
shared state.

## Phase 0 — Foundational (blocks every story)

- **T001** Declare the optional dependency. Add to `pyproject.toml`:
  `[project.optional-dependencies]` with `ui = ["django-mvp (>=0.17,<1.0)"]`, in the parenthesised
  PEP 508 form this family uses. One entry only — django-mvp brings django-cotton, easy-icons,
  flex-menus, crispy-forms and crispy-tailwind itself (research R1). Regenerate `poetry.lock`.
  Confirm `deptry` still passes, since it runs in the build job and fails on a dependency it cannot
  account for. **FR-002, FR-011**
- **T002** Create the app package. `literature/ui/__init__.py` (curated re-exports, mirroring
  `literature/importers/__init__.py`, not an empty file), and `literature/ui/apps.py` with
  `LiteratureUIConfig`: `name = "literature.ui"`, explicit `label = "literature_ui"`,
  translated `verbose_name`. No `ready()` hook and no signals. **FR-001, FR-005**
- **T003 [P]** The base template. `literature/ui/templates/literature/ui/base.html`, extending
  `mvp/base.html` and filling `{% block content %}` with `<c-container>`, `<c-page.content>` and
  `<c-page.title :attrs="page" />`, exposing a `{% block page.content %}` for pages to fill. It must
  not extend, include, or reference `base.html`, `page_view.html`, `list_view.html` or
  `detail_view.html` — a test asserts this by reading the shipped templates. **FR-004, FR-008, D-1**
- **T004** Test wiring. Copy the current `tests/settings.py` verbatim to `tests/settings_core.py`
  (the core-only settings T016 boots against, which must stay free of UI apps). Then add to
  `tests/settings.py`: `django.contrib.sites`, `django.contrib.staticfiles`, `django_cotton`,
  `easy_icons`, `flex_menu`, `mvp`, `crispy_forms`, `crispy_tailwind` in that order with `mvp` before
  `crispy_tailwind`; the `mvp.context_processors.mvp_config` context processor; `CRISPY_TEMPLATE_PACK`
  and `CRISPY_ALLOWED_TEMPLATE_PACKS`; `SITE_ID`; and `literature.ui`. Mount the app in
  `tests/urls.py` at a prefix. **Research R1, R7**
- **T005** Make CI install the extra. The reusable test workflow installs main, dev and docs groups
  only, so without this every UI test is silently skipped in CI and the suite shrinks to the core.
  Set the install argument on the `tests.yml` workflow call so the `ui` extra is installed, and
  confirm on the pull request that the UI tests actually appear in the run. **Plan risk 3**
- **T006** URLs. `literature/ui/urls.py` with `app_name = "literature"` and three routes: `""` →
  `item-list`, `"<int:pk>/"` → `item-detail`, `"contributors/<int:pk>/"` → `contributor-detail`.
  Nothing is mounted automatically; the host includes it. Test that each name reverses under the
  namespace and that importing `literature.ui.urls` has no import-time side effect on the core.
  **FR-003, FR-019, FR-032**

## Phase 1 — User Story 1: see what is in the catalogue (P1)

- **T007** `ItemListView` in `literature/ui/views.py`, subclassing `MVPListView` on `Item`, with
  `template_name` set explicitly so the packaged fallback templates are never reached. Set
  `search_fields = None`, `order_by = None` and `directory = []` explicitly — the first two are
  documented no-ops and the third suppresses the create-URL injection, so no out-of-scope control can
  render even if a template later changes. Keep the model's declared `-created` order rather than
  restating it. Prefetch `item_names__name` and `item_dates` so a page costs a constant number of
  queries. Set the empty-state heading and message. **FR-012, FR-014, FR-015, FR-018, FR-027, FR-029**
- **T008** The list templates. `item_list.html` extends the app base and fills `page.content` with a
  grid of rows and `<c-pagination :page_obj="page_obj" />`; `item_list_item.html` renders one row —
  title (falling back to the citation key when the item has none), item type as a `<c-badge>`,
  contributors in stored role and order, the issued date at its stored precision, and the citation
  key — with the title linking to the reference page. **FR-013, FR-016, FR-017, FR-018**
- **T009** Tests for the catalogue list (`tests/test_ui/test_item_list.py`). Assert against rendered
  output, not just a status code: items appear most recently added first; a page holds no more than
  `paginate_by` items whatever the catalogue size; the control states position and offers navigation;
  a page number past the end is a 404; an empty catalogue renders the stated empty result rather than
  an error; each row links to that item's page; an item with no title shows its citation key; a row
  carries the contributors, issued date and citation key it should. Add a query-count assertion so a
  regression to per-row queries fails. **FR-012 through FR-018**

## Phase 2 — User Story 2: read one reference in full (P2)

- **T010** `literature/utils/fields.py` — one function yielding `(verbose_name, value)` for an item's
  non-empty concrete fields, skipping relations, the primary key, and a caller-supplied skip set
  (`created` and `modified` by default). Follow the repo's established idiom: iterate
  `_meta.get_fields()` and use `hasattr(field, "attname")` to tell a concrete scalar from a relation.
  Do **not** rewrite the three existing in-line copies in `converters.py` and the two test modules —
  that is a refactor no requirement asks for, and it would put working code into the tamper guard.
  Unit-test the helper directly. **D-6, FR-020, FR-021**
- **T011** `ItemDetailView`, subclassing `MVPDetailView` on `Item`, `template_name` set explicitly,
  prefetching `item_names__name`, `item_dates` and `item_identifiers`. A missing item is Django's
  ordinary 404. **FR-019, FR-025, FR-027**
- **T012** `item_detail.html`. Scalar fields through `<c-data-field>` inside a `<c-grid>`, labels from
  each field's `verbose_name`, absent fields omitted entirely rather than rendered with a dash.
  Contributors in a `<c-section>`, grouped by role with `{% regroup %}` over the already-ordered
  `item_names` and shown in stored position; an unparsed or institutional name printed as held.
  Dates in a `<c-section>`, one per slot, at stored precision, a range shown as a range, and the
  stored fallback shown where there is one. Identifiers in a `<c-section>` with their type, including
  types the store does not recognise, and a value addressing a resolvable location rendered as a
  link. **FR-020 through FR-024, FR-026**
- **T013** Tests for the reference page (`tests/test_ui/test_item_detail.py`). Every field the item
  carries appears with its label and no field it does not carry appears at all; contributors appear
  grouped by role in stored order; a year-only date, a full date and a range each render at their own
  precision; identifiers show their type and an unknown type is not hidden; a missing item is a 404;
  an item with no contributors, dates or identifiers renders without those sections. Parametrise a
  render across every `ItemType` value, mirroring `test_models.py`'s existing
  `@pytest.mark.parametrize("item_type", ItemType.values)`. **FR-019 through FR-026**

## Phase 3 — User Story 3: install the store on its own and get nothing extra (P3)

- **T014 [P]** `tests/test_ui/test_architecture.py`. Walk every module under `literature/` outside
  `literature/ui/`, parse each with `ast`, and assert no import names `mvp`, `django_cotton`,
  `crispy_forms`, `easy_icons`, `flex_menu`, or `literature.ui`. Parse rather than grep, so a name
  inside a docstring or a comment does not fail the test and a real import cannot hide in one.
  **FR-006**
- **T015 [P]** `tests/test_ui/test_packaging.py`. Read `pyproject.toml` and assert `django-mvp`
  appears in `[project.optional-dependencies].ui` and in no other dependency list, so a future edit
  promoting it to a hard dependency fails here rather than in a consumer's install. **FR-002**
- **T016** The core-only boot test. One subprocess running `django.setup()` and the system check
  framework against `tests.settings_core`, then importing every module under `literature/` except
  `literature.ui`. It proves the core still boots with nothing UI installed — the part of the
  guarantee a static import scan cannot reach, because a runtime dependency has no import statement.
  **FR-006, SC-009**

## Phase 4 — User Story 4: follow a contributor to everything they worked on (P4)

- **T017** `ContributorDetailView`, an `MVPDetailView` on `Name`. `MVPDetailView` does not paginate,
  so the view builds a `Paginator` over `Item.objects.filter(item_names__name=self.object).distinct()`
  in the catalogue's order and puts it in context as `page_obj`, the name `<c-pagination>` expects.
  `.distinct()` is load-bearing: a contributor holding two roles on one item has two `ItemName` rows,
  and without it the item appears twice, which FR-035 forbids. Roles come from a single further query
  over `ItemName.objects.filter(name=self.object, item__in=<the page's items>)`, grouped in Python
  into `{item_id: [role, …]}` — one query per page, not one per row. **FR-032, FR-034, FR-035,
  FR-036, FR-037**
- **T018** `contributor_detail.html` and `contributor_item.html`. The name as the store holds it,
  including an unparsed or institutional name, then the paginated list of credits, each row carrying
  what a catalogue row carries plus the role or roles held on that item, linking to the reference
  page. A contributor credited on nothing renders the stated empty result. **FR-033 through FR-037**
- **T019** Link contributor names from the reference page. Each contributor's name in
  `item_detail.html` becomes a link to their page. This is the only change to a template built in
  Phase 2, and it is what makes the contributor page reachable by browsing. **FR-022**
- **T020** Tests for the contributor page (`tests/test_ui/test_contributor_detail.py`). The credits
  are listed with roles; a contributor holding two roles on one item sees that item once carrying
  both; the list paginates in the catalogue's order; an institutional name renders unsplit; a
  contributor with no credits renders the empty result; a missing contributor is a 404; two records
  with identical names keep separate pages showing their own credits. Assert query count so the role
  lookup cannot regress to one query per row. **FR-032 through FR-038**

## Phase 5 — Cross-cutting (after the stories, before convergence)

- **T021 [P]** `tests/test_ui/test_templates.py`. Two guards over every template the app ships.
  First, the utility-class allowlist: extract every `class` attribute token and assert each is either
  a daisyUI component class a packaged component uses or a utility named in django-mvp's
  `utility-classes.md`; arbitrary values such as `w-[37px]`, opacity modifiers such as
  `text-base-content/60`, and the `sm:` and `2xl:` prefixes all fail. This is the only mechanical
  proof that FR-008 holds, and django-accounts-center shipping two workaround CSS rules is the
  evidence it is needed. Second, i18n: assert every literal string rendered to a reader is wrapped
  for translation. **FR-007, FR-008, D-7**
- **T022 [P]** `CONTEXT.md`: add the *UI app* as the name for `literature.ui`, and the *catalogue* as
  the name for the stored items spoken about from the interface. **FR-031, Article VI**
- **T023 [P]** `README.md`: how to install the extra, which apps to add and in what order, the
  context processor and crispy settings django-mvp needs, how to include the URLs, and the note that
  the extra requires Python 3.12 and Django 5.2 while the core keeps its own lower floor. **FR-003,
  FR-004, Article VII**
- **T024** `memory/constitution.md`: the architecture section currently says no third-party UI
  package is prescribed and that adopting one is an amendment. GOALS.md G4, the README's scope
  section and roadmap R6 all already commit to django-mvp, so this records what was decided
  elsewhere rather than deciding anything. Amend the section to name django-mvp as the adopted UI
  layer for the opt-in app, and state that the core stays free of it. **Constitution Check**

## Requirement coverage

Every functional requirement is carried by at least one task:

- FR-001, FR-005 → T002 · FR-002 → T001, T015 · FR-003 → T006, T023 · FR-004 → T003, T023
- FR-006 → T014, T016 · FR-007 → T021 · FR-008 → T003, T021 · FR-009 → no task: the specification's
  *Component gaps* section is empty and research R4 found no gap that qualifies; the requirement's
  process applies if that changes during implementation
- FR-010 → T003 (the app never inherits a host shell) · FR-011 → T001
- FR-012 through FR-018 → T007, T008, T009 · FR-019 through FR-026 → T010–T013
- FR-027, FR-029 → T007, and by the absence of any write path in the diff
- FR-028 → satisfied by omission: no view declares a permission or login mixin, asserted in T009 and
  T013 by fetching every page as an anonymous client
- FR-030 → no task; the feature adds no admin
- FR-031 → T022 · FR-032 through FR-038 → T017–T020

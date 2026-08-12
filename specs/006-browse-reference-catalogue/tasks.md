# Tasks: Browse the Reference Catalogue in an Opt-In Front End

**Feature**: `006-browse-reference-catalogue` · **Spec**: `spec.md` · **Plan**: `plan.md`

Article I is Test-First: within every task the test is written and seen to fail before the code that
makes it pass. `[P]` marks tasks that may run in parallel with their siblings — different files, no
shared state.

## Phase 0 — Foundational (blocks every story)

- **T001** Declare the optional dependency. Add to `pyproject.toml`:
  `[project.optional-dependencies]` with
  `ui = ["django-mvp (>=0.17,<1.0) ; python_version >= '3.12'"]`, in the parenthesised PEP 508 form
  this family uses. **The marker is required, not decoration**: django-mvp declares
  `requires-python >=3.12` while this project declares `>=3.11,<4.0`, so without it `poetry lock`
  fails outright on the incompatible range — and raising `requires-python` to fix it would drop every
  core-only consumer on 3.11. `requires-python` stays at 3.11; the same pattern is already in the
  file, on the `mvp-shared` dev pin. One entry only — django-mvp brings django-cotton, easy-icons and
  flex-menus itself (research R1). Regenerate `poetry.lock`. Confirm `deptry` still passes, since it
  runs in the build job and fails on a dependency it cannot account for. **FR-002, FR-011**
- **T002** Create the app package. `literature/ui/__init__.py` carrying a **docstring and nothing
  else**, and `literature/ui/apps.py` with `LiteratureUIConfig`: `name = "literature.ui"`, explicit
  `label = "literature_ui"`, translated `verbose_name`. No `ready()` hook and no signals.

  Do **not** copy `literature/importers/__init__.py`'s curated re-exports. `importers` is a plain
  sub-package; `literature.ui` is an installed app, so Django imports this module during app-registry
  phase 1 and a re-export reaching `views.py` reaches `literature.models`, raising
  `AppRegistryNotReady` at `django.setup()` — every install fails at boot, this suite included.
  `literature/__init__.py` is empty for exactly this reason and says so. FR-005 is met regardless:
  `literature.ui.views.ItemListView` is inside the `literature` namespace. **FR-001, FR-005**
- **T003 [P]** The base template. `literature/ui/templates/literature/ui/base.html`, extending
  `mvp/base.html` and filling `{% block content %}` with `<c-container>`, `<c-page.content>` and
  `<c-page.title :attrs="page" />`, exposing a `{% block page.content %}` for pages to fill. It must
  not extend, include, or reference `base.html`, `page_view.html`, `list_view.html` or
  `detail_view.html` — a test asserts this by reading the shipped templates. Recompose the two
  regions `page_view.html` supplies that D-1's snippet omits: wrap in `<c-page class="{{ page.class }}">`
  so pages carry django-mvp's own `mvp-page` / `item-page` classes, and render the breadcrumbs region.
  **FR-004, FR-008, D-1**
- **T004** Test wiring. **Move** today's `tests/settings.py` to `tests/settings_core.py` and give it
  its own core-only `ROOT_URLCONF` pointing at an empty urlconf — this is the module T016 boots, and
  it must stay free of UI apps and UI URLs. Then make `tests/settings.py` import from it
  (`from tests.settings_core import *  # noqa`) and append: `django.contrib.sites`,
  `django.contrib.staticfiles`, `django_cotton`, `easy_icons`, `flex_menu`, `mvp` and `literature.ui`
  to `INSTALLED_APPS`; the `mvp.context_processors.mvp_config` context processor; `SITE_ID`; and
  `ROOT_URLCONF = "tests.urls"`. Mount the app in `tests/urls.py` at a prefix.

  Two things this task must not do. **Do not copy `settings.py` verbatim** — the copy keeps
  `ROOT_URLCONF = "tests.urls"`, which this same task wires to `literature.ui.urls`, and Django's
  check framework imports the root urlconf, so T016's core-only subprocess would load the whole UI
  stack and pass for a reason unrelated to what it asserts. **Do not add `crispy_forms`,
  `crispy_tailwind`, `CRISPY_TEMPLATE_PACK` or `CRISPY_ALLOWED_TEMPLATE_PACKS`**: research R1
  justified them by `list_view.html` loading `crispy_forms_tags`, and D-1 then ruled that nothing in
  this app touches `list_view.html`. In django-mvp, `crispy` appears only in `list_view.html`, two
  form components and a help-text partial — none in the `mvp/base.html` → `<c-app>` → `<c-page.*>` /
  `<c-pagination>` / `<c-data-field>` chain this app uses, and cotton resolves components lazily at
  render time. Every app dropped here is one the host does not have to install.

  Also add `tests/test_ui/__init__.py` (Article XIV) and `tests/test_ui/conftest.py` holding the
  client and item fixtures T009, T013 and T020 share, so no story owns them. **Research R1, R7,
  Article XIV**
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
  queries. Set `list_item_template` explicitly — `MVPListViewMixin` derives it as
  `literature/item_list_item.html`, not the app-namespaced path T008 ships. Set the empty-state
  heading and message. **FR-012, FR-014, FR-015, FR-018, FR-027, FR-029**
- **T008** The list templates. `item_list.html` extends the app base and fills `page.content` with a
  grid of rows and `<c-pagination :page_obj="page_obj" />`; `item_list_item.html` renders one row —
  title (falling back to the citation key when the item has none), item type as a `<c-badge>`,
  contributors in stored role and order, the issued date at its stored precision, and the citation
  key — with the title linking to the reference page. **FR-013, FR-016, FR-017, FR-018**
- **T009** Tests for the catalogue list — class `TestItemListView` in `tests/test_ui/test_views.py`
  (Article XIV: one source module, one test module, the split expressed with classes). Assert against rendered
  output, not just a status code: items appear most recently added first; a page holds no more than
  `paginate_by` items whatever the catalogue size; the control states position and offers navigation;
  a page number past the end is a 404; an empty catalogue renders the stated empty result rather than
  an error; each row links to that item's page; an item with no title shows its citation key; a row
  carries the contributors, issued date and citation key it should. Add a query-count assertion so a
  regression to per-row queries fails. **FR-012 through FR-018**

## Phase 2 — User Story 2: read one reference in full (P2)

- **T010** `literature/ui/fields.py` — one function yielding `(verbose_name, value)` for an item's
  non-empty concrete fields, skipping relations, the primary key, and a caller-supplied skip set
  defaulting to `{"created", "modified", "categories", "custom"}`. The two JSONFields are in the
  default set because `hasattr(field, "attname")` admits them while they are not scalars: they would
  render as Python dict reprs where FR-020 asks for a field, and `converters.py`'s `scalar_skip`
  already lists both for the same reason. Follow the repo's established idiom otherwise: iterate
  `_meta.get_fields()` and use `hasattr(field, "attname")` to tell a concrete scalar from a relation.
  It lives in the UI app, not `literature/utils/`, because its only caller is `item_detail.html` and
  FR-006 keeps this feature out of the core (D-6). Do **not** rewrite the three existing in-line
  copies in `converters.py` and the two test modules — that is a refactor no requirement asks for,
  and it would put working code into the tamper guard. Unit-test it in `tests/test_ui/test_fields.py`.
  **D-6, FR-020, FR-021**
- **T011** `ItemDetailView`, subclassing `MVPDetailView` on `Item`, `template_name` set explicitly,
  prefetching `item_names__name`, `item_dates` and `item_identifiers`. Set `show_list_action = True`
  so `PageObjectMixin.get_breadcrumbs()` reverses `literature:item-list` — the default False renders
  the crumb with an empty `href`. A missing item is Django's ordinary 404. **FR-019, FR-025, FR-027**
- **T012** `item_detail.html`. Scalar fields through `<c-data-field>` inside a `<c-grid>`, labels from
  each field's `verbose_name`, absent fields omitted entirely rather than rendered with a dash.
  Contributors in a `<c-section>`, grouped by role with `{% regroup %}` over the already-ordered
  `item_names` and shown in stored position; an unparsed or institutional name printed as held.
  Dates in a `<c-section>`, one per slot, at stored precision, a range shown as a range, and the
  stored fallback shown where there is one. Identifiers in a `<c-section>` with their type, including
  types the store does not recognise, and a value addressing a resolvable location rendered as a
  link. **FR-020 through FR-024, FR-026**
- **T013** Tests for the reference page — class `TestItemDetailView` in `tests/test_ui/test_views.py`.
  Every field the item
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
  so the view builds a `Paginator` over
  `Item.objects.filter(item_names__name=self.object).distinct().prefetch_related("item_names__name", "item_dates")`
  in the catalogue's order and puts it in context as `page_obj`, the name `<c-pagination>` expects.
  The prefetch matches the catalogue list's, because FR-034 gives a credit row the same content a
  catalogue row carries — omit it and every row costs its own queries. **Hand-building the paginator
  loses `ListView.paginate_queryset`'s 404 behaviour**, which FR-036 inherits through FR-017: catch
  `InvalidPage` and raise `Http404`. `Paginator.get_page()` is the wrong call here — it silently
  clamps an out-of-range page to the last one.
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
- **T020** Tests for the contributor page — class `TestContributorDetailView` in
  `tests/test_ui/test_views.py`. The credits are listed with roles; a contributor holding two roles
  on one item sees that item once carrying both; the list paginates in the catalogue's order; **a
  page number past the end is a 404** (FR-036 through FR-017 — the assertion the hand-built paginator
  makes necessary); an institutional name renders unsplit; a contributor with no credits renders the
  empty result; a missing contributor is a 404; two records with identical names keep separate pages
  showing their own credits. Assert query count so neither the role lookup nor the row content can
  regress to one query per row. **FR-032 through FR-038**

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
- **T023 [P]** `README.md`: how to install the extra, which apps to add and in what order
  (`django.contrib.sites`, `django.contrib.staticfiles`, `django_cotton`, `easy_icons`, `flex_menu`,
  `mvp`, `literature.ui` — **no crispy apps or settings**, see T004), the `mvp_config` context
  processor, `SITE_ID` and `django.contrib.sites.middleware.CurrentSiteMiddleware` (without it
  `mvp/base.html`'s `{{ request.site.name }}` renders the page title suffix blank), how to include
  the URLs, and the note that the extra requires Python 3.12 and Django 5.2 while the core keeps its
  own lower floor. **This section is SC-002's evidence** — the success criterion is met by these
  steps being documented and sufficient, not by the app configuring itself. **FR-003, FR-004,
  SC-002, Article VII**
- **T025 [P]** Check the non-mirror test paths. Each entry is declared by the commit that creates
  its file, so the conformance gate stays green between stories rather than going red for the whole
  run; this task confirms the final list reads:

  ```toml
  [tool.forge.conformance]
  non-mirror-paths = ["tests/test_ui/test_architecture.py", "tests/test_ui/test_boot.py", "tests/test_ui/test_packaging.py", "tests/test_ui/test_templates.py"]
  ```

  Article XIV exempts a test whose subject is not a Python module only when the repo declares it, and
  these four take the package boundary, the core's boot under `tests.settings_core`, `pyproject.toml`
  and the shipped templates as their subject. `test_boot.py` is US-3's own addition: T016's task text
  names a core-only boot test without a filename, and its subject — the core package booting with the
  UI app absent — mirrors no module either.
  **Article XIV**
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

Success criteria, which the FR list does not reach:

- SC-001, SC-004 through SC-008, SC-010, SC-011 → carried by the requirement tasks above
- **SC-002** → T023. The criterion is that the documented install steps are sufficient, not that the
  app self-configures — see the spec amendment recorded in `decisions.md` D-8
- **SC-003, SC-012** (a page's queries do not grow with its rows) → the query-count assertions inside
  T009 and T020, and nothing else. Stated here rather than left implied, because they are the only
  evidence for either criterion
- **SC-009** → T014, T015, T016 together

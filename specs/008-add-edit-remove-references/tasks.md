# Tasks: Add, Edit and Remove References Through the Front End

**Input**: `spec.md`, `plan.md`, `research.md`, `decisions.md` in `specs/008-add-edit-remove-references/`

**Format**: `[ID] [P?] [Story] Description` — `[P]` marks a task that can run in parallel with the
one before it (different files, no dependency).

Tests are written before the code they check, per constitution Article I.

Plan against django-mvp **0.17.0** (the locked version), never the 0.18.0 working copy — see
`research.md` §2.

---

## Phase 1: Foundational (blocking — no story can be verified until this lands)

**Purpose**: the field-group mapping and the form every write flow renders. This phase carries the
only substantial judgement in the feature.

- [ ] T001 Set `CRISPY_TEMPLATE_PACK = "tailwind"` in `tests/settings.py` and `demo/settings.py`. Both install `crispy_tailwind` and neither sets the pack, so crispy currently falls back to `bootstrap4` — nothing has noticed because the package renders no form yet (plan D-5). Add a comment in each naming what it prevents.
- [ ] T002 Write `tests/test_ui/test_fieldgroups.py`, failing, for the structural guarantees before any assignment exists: every field of `Item` except `categories`, `custom`, `created` and `modified` belongs to exactly one group (assert by set equality against `Item._meta.get_fields()`, so a field added to the model later fails this test rather than silently vanishing from the form); no field belongs to two groups; every one of the 45 `ItemType` values has an entry; `core` and `general` are in every type's set and `processor` is in none; every group named by a type exists.
- [ ] T003 Write `literature/ui/fieldgroups.py` with the thirteen groups exactly as `plan.md` D-1 tabulates them, and a class carrying `groups_for(item_type)`, `fields_for(group)` and `groups_holding_values(item)` (Article XV — they share a subject). Group labels are user-visible headings, so wrap them with `gettext_lazy` (Article VIII). Populate the per-type assignments for all 45 types by applying D-1's six criteria **in the order given**, and give every type a one-line comment naming the criterion that decided it — the comment is the artefact FR-004 requires, not decoration. Make T002 pass.
- [ ] T004 Sanity-check the assignment sizes against the figures in `research.md` §1 — Zotero reaches a median of 24 CSL variables per type over the 32 types it covers, range 16–35. Any type whose group set resolves to markedly more or fewer fields than that band gets re-read against the criteria and either corrected or its comment extended to say why it genuinely differs. The 13 types Zotero does not cover (`classic`, `collection`, `entry`, `event`, `figure`, `musical_score`, `pamphlet`, `performance`, `periodical`, `regulation`, `review`, `review-book`, `treaty`) have no external check and rest on the criteria alone — say so in the story report. This is a review pass over T003, not a second source of truth: Zotero is unlicensed and is never copied from.
- [ ] T005 Write `tests/test_ui/test_forms.py`, failing: `ItemForm` declares every scalar field of `Item`; it declares neither `categories` nor `custom` nor `created` nor `modified`; a form with only `type` and `citation_key` is valid; a form missing either is invalid and names that field; a `citation_key` duplicating a stored item's key is **valid** (FR-007) and saving stores it unchanged.
- [ ] T006 Write `literature/ui/forms.py` with `ItemForm(ModelForm)` over every scalar field (plan D-3, D-4). Put `x-model="form.itemType"` on the `type` widget's `attrs` — crispy renders that select and there is no component seam that injects it (`research.md` §2). Every label and help text comes from the model, which already carries translated ones; anything the form adds is wrapped. Make T005 pass.

**Checkpoint**: the mapping and the form exist and are tested. No page renders yet.

---

## Phase 2: US-1 — Enter a reference by hand (P1)

**Goal**: a reference can be created from the catalogue page, through a form scoped by item type.

- [ ] T007 [US1] Write `tests/test_ui/test_urls.py` additions, failing: `literature:item-create`, `literature:item-update` and `literature:item-delete` reverse, and — the specific failure worth guarding — **every action name in every view's `crud_views` reverses**, iterating the views rather than listing names by hand. An action that is shown with no resolvable route raises `NoReverseMatch` inside `get_breadcrumbs()`, which is an uncaught 500 on the form page rather than a missing button (plan D-6).
- [ ] T008 [US1] Add the three routes to `literature/ui/urls.py`: `add/` → `item-create`, `<int:pk>/edit/` → `item-update`, `<int:pk>/delete/` → `item-delete`. Keep the existing three untouched.
- [ ] T009 [US1] Write the `TestItemCreateView` class in `tests/test_ui/test_views.py`, failing, one test per acceptance scenario of US-1: the page renders and carries the type select; posting a valid form stores an item with exactly the values posted and redirects to its detail page; posting without `type` or without `citation_key` stores nothing and returns the form naming the field; posting a duplicate citation key stores it unchanged with no warning in the response; a created item's detail page renders with no contributors, dates or identifiers.
- [ ] T010 [US1] Write `ItemCreateView(MVPCreateView)` in `literature/ui/views.py`: `form_class = ItemForm`, `success_url = "detail"` (the CRUD shorthand — `Item` has no `get_absolute_url()`, so a literal is not available and the fallback chain ends in `ImproperlyConfigured`), a translated `page_title` and `success_message`, and `crud_views` extended with the namespaced `create`, `update` and `delete` names. Make T009 pass.
- [ ] T011 [US1] Write `literature/ui/templates/literature/ui/item_form.html`, extending django-mvp's `form_view.html` and rendering the form group by group rather than through one `c-form.render` call — there is no fieldset, accordion or tabs component in 0.17.0, so grouping is `c-card`/`c-section` per group (`research.md` §2). Serialise the type→groups map into the page once as JSON. Each group wrapper carries `x-show="showAll || typeGroups[form.itemType].includes(group) || forcedGroups.includes(group)"`, and a translated "Show every field" toggle sets `showAll`. `cotton/form/index.html` already opens `x-data="{form: {}}"` on the `<form>`, so declare no second scope. **Every field stays in the DOM whether or not its group is shown** — that is what makes a hidden field post the value it already held, and it is the whole of the no-loss guarantee (plan D-3). No custom CSS, no custom component (FR-026).
- [ ] T012 [US1] Add the catalogue entry point: `directory = ["create"]` and the namespaced `crud_views` on `ItemListView`. Leave `create_form_class` unset so the component renders a link to the create page rather than a modal — an 89-field form does not belong in a modal (plan D-8). Extend `tests/test_ui/test_views.py`'s existing `TestItemListView` with a test that the Add link renders and points at `item-create`.
- [ ] T013 [US1] Write a rendering test asserting the crispy **tailwind** pack's markup is what comes back from the create page, not the setting's value (plan D-5). A test on the setting passes even when the pack is misconfigured somewhere the setting does not reach.

**Checkpoint**: a reference can be created through the interface, and the form is scoped by type.

---

## Phase 3: US-2 — Correct a reference that is wrong (P2)

**Goal**: a stored reference can be corrected through the same form, losing nothing.

- [ ] T014 [US2] Write the `TestItemUpdateView` class in `tests/test_ui/test_views.py`, failing, one test per acceptance scenario of US-2, plus **the round trip that is SC-003**: build an item with a value in every scalar field and in `categories` and `custom`, GET the form, POST it back unchanged, and assert every stored field is identical — including the two the form does not carry. That single test is the whole no-loss guarantee and is the most valuable test in the feature.
- [ ] T015 [US2] Write a test that a populated field belonging to a group the current item type does not use is present in the response **and** its group is in the forced-visible set — the FR-010 guarantee. Then a test that changing the item type on POST retains values in groups the new type does not use (FR-014).
- [ ] T016 [US2] Write a test that saving through the form leaves the item's `ItemName`, `ItemDate` and `ItemIdentifier` rows unchanged in value, role and order (FR-012). Use the `populated_item` fixture in `tests/test_ui/conftest.py`.
- [ ] T017 [US2] Write `ItemUpdateView(MVPUpdateView)` in `literature/ui/views.py`, reusing `ItemForm` and `item_form.html`: `success_url = "detail"`, translated `page_title`/`success_message`, namespaced `crud_views`. Pass `groups_holding_values(self.object)` into the context as the forced-visible set. Make T014–T016 pass.
- [ ] T018 [US2] Add the reference-page entry point: `directory = ["update", "delete"]` on `ItemDetailView` and the three new names in its `crud_views` — it currently maps only `list` and `detail` and sets `directory = []`. Extend `TestItemDetailView` with a test that the Edit and Delete actions render and point at the right routes.

**Checkpoint**: a reference can be corrected, and nothing is lost by doing so.

---

## Phase 4: US-3 — Remove a reference that does not belong (P3)

**Goal**: one reference at a time can be removed, behind a confirmation, without taking contributors with it.

- [ ] T019 [US3] Write the `TestItemDeleteView` class in `tests/test_ui/test_views.py`, failing, one test per acceptance scenario of US-3: GET renders a confirmation naming the reference and deletes nothing; POST removes the item together with its `ItemName`, `ItemDate` and `ItemIdentifier` rows and redirects to the catalogue; the `Name` records survive whether or not they are credited elsewhere, and a contributor left credited on nothing still renders their own page; removing the last reference leaves the catalogue rendering its empty state; an unknown pk answers 404.
- [ ] T020 [US3] Write `ItemDeleteView(MVPDeleteView)` in `literature/ui/views.py`: `show_related_objects = True` so the confirmation lists what goes with the reference (FR-019), `require_confirmation` left off (plan D-7), `success_url = "list"` — `MVPDeleteView` deliberately does not consult `get_absolute_url()`. Translated `page_title`/`success_message`. Make T019 pass. django-mvp's `delete_view.html` renders the whole confirmation, so no template is written here.

**Checkpoint**: all three flows work through the interface.

---

## Phase 5: US-4 — The demo shows the flows, and a broken one is caught (P4)

**Goal**: the demo carries the flows and the guard walks them.

- [ ] T021 [US4] Extend `demo/smoke.py` with a write pass over the demo project's own settings and URLs, following links as the existing walk does: create a reference, follow to its page, correct a field and confirm the change renders, remove it and confirm the catalogue no longer lists it. Assert the catalogue changed as each step claims rather than that a page returned 200 (FR-032). Keep the existing read walk intact — this is an addition. The guard still asserts no page redirects to a login (FR-033).
- [ ] T022 [US4] Prove the guard by reinstating the defect, the method FS-007 used for its own (its D-8): break each of the three flows in turn — a wrong `success_url`, a form field removed, a delete that does not delete — and confirm the guard fails and names the flow each time. Assert on the guard's emitted output, never on a piped exit code. Record the three runs in the story report.
- [ ] T023 [US4] Confirm the demo's documented start path still reaches the new pages by following links only, with no URL typed by hand, and that no step asks for a sign-in.

**Checkpoint**: the demo carries the flows and a broken one fails the guard.

---

## Phase 6: Polish

- [ ] T024 Document the write flows in `README.md`: what the three pages do, that they are open with no permission check and that restricting them is the host's to do, and `CRISPY_TEMPLATE_PACK = "tailwind"` in the install steps (plan D-5) — a host copying the current instructions hits the same latent defect this feature found.
- [ ] T025 Document the field-group mapping where a reader can check it: what the groups are, that CSL publishes no such mapping and this one is the package's own, that it governs presentation and never what can be stored, and how to disagree with an entry. Cite the CSL specification's Appendices III and IV as the evidence base, with attribution (the specification text is CC BY-SA 4.0).
- [ ] T026 CHANGELOG entry.
- [ ] T027 Run the humanizer pass over every public markdown this feature authored or rewrote — `README.md`, any docs page from T025, and the PR body — per the public-markdown checklist. No internal handles.
- [ ] T028 Full `forge verify` and `tamper-check` over the whole feature diff.

---

## Dependencies

- Phase 1 blocks everything. T003 blocks T004; T006 blocks every view task.
- Phase 2 blocks Phase 3 (the update view reuses `ItemForm` and `item_form.html`).
- Phase 3 blocks Phase 4 only through `ItemDetailView`'s `directory`, which T018 sets.
- Phase 5 needs all three flows.
- Phases 2–4 share `views.py`, `item_form.html` and `test_views.py`, so they run sequentially. No `[P]` tasks in this feature.

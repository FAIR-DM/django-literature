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

- [ ] T001 Set `CRISPY_TEMPLATE_PACK = "tailwind"` in `tests/settings.py` and `demo/settings.py`, with a comment in each naming what it prevents. crispy-forms 2.7's `get_template_pack()` is `getattr(settings, "CRISPY_TEMPLATE_PACK")` with **no default**, so the current state is an `AttributeError` on the first form render rather than a fallback to another pack (plan D-5). In the same task, drop the single assertion `not hasattr(settings, "CRISPY_TEMPLATE_PACK")` at `tests/test_ui/test_smoke.py:90` and cite plan D-5 in the edit — it is a pre-existing passing test that this change makes wrong, and Article I requires the decision to be on record rather than improvised. **Leave line 91's `CRISPY_ALLOWED_TEMPLATE_PACKS` assertion alone**: that setting is only consulted when `{% crispy %}` is given an explicit pack argument, which `cotton/form/render.html` does not do.
- [ ] T002 Write `tests/test_ui/test_fieldgroups.py`, failing, for the structural guarantees before any assignment exists: every field of `Item` except `categories`, `custom`, `created` and `modified` belongs to exactly one group (assert by set equality against `Item._meta.get_fields()`, so a field added to the model later fails this test rather than silently vanishing from the form); no field belongs to two groups; every one of the 45 `ItemType` values has an entry; `core` and `general` are in every type's set and `processor` is in none; every group named by a type exists. **Add a ceiling so the mapping cannot degenerate**: `groups_for(ItemType.ARTICLE_JOURNAL)` must resolve to fewer than half of the form's 60 fields. Without it, a mapping that assigns every group to every type passes every other assertion here and SC-002 has nothing failing on it.
- [ ] T003 Write `literature/ui/fieldgroups.py` with the thirteen groups exactly as `plan.md` D-1 tabulates them, and a class carrying `groups_for(item_type)`, `fields_for(group)` and `groups_holding_values(item)` (Article XV — they share a subject). Group labels are user-visible headings, so wrap them with `gettext_lazy` (Article VIII). Populate the per-type assignments for all 45 types by applying D-1's six criteria **in the order given**, and give every type a one-line comment naming the criterion that decided it — the comment is the artefact FR-004 requires, not decoration. Then compare each type's resolved field count against `research.md` §1's band (Zotero reaches a median of 24 CSL variables per type, range 16–35, over the 32 types it covers) and extend the comment of any type sitting outside it to say why it genuinely differs. Zotero is a plausibility check, never a source: it is unlicensed and is never copied from, and the 13 types it does not cover (`classic`, `collection`, `entry`, `event`, `figure`, `musical_score`, `pamphlet`, `performance`, `periodical`, `regulation`, `review`, `review-book`, `treaty`) rest on the criteria alone — say so in the story report. Make T002 pass.
- [x] ~~T004 Sanity-check the assignment sizes against `research.md` §1~~ — **folded into T003 at design review (DR-012)**. It duplicated T003's own criteria, its threshold ("markedly more or fewer") was not checkable, and it produced no test. The durable instruction now lives at the end of T003.
- [ ] T005 Write `tests/test_ui/test_forms.py`, failing: `ItemForm` declares every scalar field of `Item`; it declares neither `categories` nor `custom` nor `created` nor `modified`; a form with only `type` and `citation_key` is valid; a form missing either is invalid and names that field; a `citation_key` duplicating a stored item's key is **valid** (FR-007) and saving stores it unchanged.
- [ ] T006 Write `literature/ui/forms.py` with `ItemForm(ModelForm)` over every scalar field (plan D-3, D-4). Put **both** `x-model="form.itemType"` and `x-init="form.itemType = $el.value"` on the `type` widget's `attrs` — crispy renders that select and there is no component seam that injects them (`research.md` §2). The `x-init` is not decoration: `cotton/form/index.html` opens `x-data="{form: {}}"` with an empty object, so without it `x-model` writes undefined onto the select at initialisation, the edit page renders with no type selected, and saving then fails validation because `type` is required (plan D-3). Every label and help text comes from the model, which already carries translated ones; anything the form adds is wrapped. Make T005 pass.

**Checkpoint**: the mapping and the form exist and are tested. No page renders yet.

---

## Phase 2: US-1 — Enter a reference by hand (P1)

**Goal**: a reference can be created from the catalogue page, through a form scoped by item type.

- [ ] T007 [US1] Write `tests/test_ui/test_urls.py` additions, failing: `literature:item-create`, `literature:item-update` and `literature:item-delete` reverse, and — the specific failure worth guarding — **every action name in every view's `crud_views` reverses**, iterating the views rather than listing names by hand. An action that is shown with no resolvable route raises `NoReverseMatch` inside `get_breadcrumbs()`, which is an uncaught 500 on the form page rather than a missing button (plan D-6). This assertion is only literally true because T010 assigns the shared `CRUD_VIEWS` rather than overriding three keys of the unnamespaced default.
- [ ] T008 [US1] Add the three routes to `literature/ui/urls.py`: `add/` → `item-create`, `<int:pk>/edit/` → `item-update`, `<int:pk>/delete/` → `item-delete`. Keep the existing three untouched.
- [ ] T009 [US1] Write the `TestItemCreateView` class in `tests/test_ui/test_views.py`, failing, one test per acceptance scenario of US-1: the page renders and carries the type select **carrying both the `x-model` and the `x-init`**; with no type chosen, every group wrapper but the type's own carries a guard that evaluates false (FR-002); posting a valid form stores an item with exactly the values posted **and redirects to that item's detail URL** — assert the redirect target, not only the stored object; posting without `type` or without `citation_key` stores nothing and returns the form naming the field; posting a duplicate citation key stores it unchanged with no warning in the response; a created item's detail page renders with no contributors, dates or identifiers. **Every POST in this class carries the same `default_next` the rendered page emits** — a bare field dict omits it and would pass against a view that redirects to the wrong page (plan D-3).
- [ ] T010 [US1] Write `ItemCreateView(MVPCreateView)` in `literature/ui/views.py`: `form_class = ItemForm`, `success_url = "detail"` (the CRUD shorthand — `Item` has no `get_absolute_url()`), `show_list_action = show_detail_action = True` (without the flags the shorthand does not resolve and the redirect degrades to the literal relative path `detail`, and `get_breadcrumbs()` needs both — plan D-6), a translated `page_title` and `success_message`. In the same file, add the module-level `CRUD_VIEWS` dict mapping all five actions under the `literature:` namespace and assign it here. Make T009 pass.
- [ ] T011 [US1] Write `literature/ui/templates/literature/ui/item_form.html`, extending django-mvp's `form_view.html` and rendering the form group by group rather than through one `c-form.render` call — there is no fieldset, accordion or tabs component in 0.17.0, so grouping is `c-card`/`c-section` per group (`research.md` §2). Serialise the type→groups map into the page once as JSON. Each group wrapper carries `x-show="showAll || forcedGroups.includes(group) || (typeGroups[form.itemType] || []).includes(group)"` — the `|| []` prevents the expression throwing on a blank create page where `form.itemType` is empty. A translated "Show every field" toggle sets `showAll`. `cotton/form/index.html` already opens `x-data="{form: {}}"` on the `<form>`, so declare no second scope. **Override `{% block actions %}`** with a single translated Save button: the stock block posts `default_next=list`, which `NextURLMixin` consults ahead of `success_url`, so leaving it would land every save on the catalogue and break FR-008 and FR-015 (plan D-3). **Every field stays in the DOM whether or not its group is shown** — `x-show` sets `style.display` and leaves the element in place, which is what makes a hidden field post the value it already held, and it is the whole of the no-loss guarantee. No custom CSS, no custom component (FR-026).
- [ ] T012 [US1] Add the catalogue entry point on `ItemListView`: `directory = ["create"]`, `show_create_action = True` (`directory` alone shows nothing — every `show_<action>_action` defaults to `False` and `get_directory()` drops the entry, plan D-6), and the shared `CRUD_VIEWS`. Leave `create_form_class` unset so the component renders a link to the create page rather than a modal — a thirteen-group form does not belong in a modal (plan D-8). Extend `tests/test_ui/test_views.py`'s existing `TestItemListView` with a test that the Add link renders and points at `item-create`.
- [ ] T013 [US1] Write a rendering test asserting the crispy **tailwind** pack's markup is what comes back from the create page, not the setting's value (plan D-5). A test on the setting passes even when the pack is misconfigured somewhere the setting does not reach.

- [ ] T030 [US1] **Re-run the per-type assignment in `literature/ui/fieldgroups.py` against the corrected criteria** (plan D-1, C2 and the new C2a). The first pass applied C2 as though the four clusters named in its parenthetical were the whole of it, so it read `numbering` off the "paginated inside a host" reasoning and never reached `container`. The result: `article-journal` resolves to a form with no `container_title`, so the most common item type in any bibliography cannot record which journal it appeared in. The same gap hits chapter, entry, entry-dictionary, entry-encyclopedia, article-magazine, article-newspaper, paper-conference, review and review-book. `software` likewise resolves to the bare baseline although Appendix IV defines `version` in terms of it, and `version` sits in `publication`.

  Work from `research.md` §1's type-bound variable list, which is already gathered — every variable there whose definition names a type is C2 evidence for that type's group. Keep the existing comment discipline: one line per type naming the criterion, and a stated reason for any type still sitting outside the 16-35 band. Types genuinely outside every criterion stay at the baseline; that is a real answer, but it has to be the answer to a search rather than the residue of one.

  **First, extend `tests/test_ui/test_fieldgroups.py` with the assertions that would have caught this**, and watch them fail before touching the mapping: `container` is in `groups_for()` for every type whose CSL definition names a containing work — article-journal, article-magazine, article-newspaper, chapter, entry, entry-dictionary, entry-encyclopedia, paper-conference, review, review-book, book, broadcast, motion_picture, report, song, speech, webpage — and `publication` is in `groups_for(ItemType.SOFTWARE)`. Keep the existing structural tests green.

**Checkpoint**: a reference can be created through the interface, and the form is scoped by type.

---

## Phase 3: US-2 — Correct a reference that is wrong (P2)

**Goal**: a stored reference can be corrected through the same form, losing nothing.

- [ ] T014 [US2] Write the `TestItemUpdateView` class in `tests/test_ui/test_views.py`, failing, one test per acceptance scenario of US-2, plus **the round trip that is SC-003**: build an item with a value in every scalar field and in `categories` and `custom`, GET the form, POST it back unchanged, and assert every stored field is identical — including the two the form does not carry. Compare every concrete field **except `created` and `modified`**, which are `auto_now_add`/`auto_now` and change on every save by design; naming the exclusion keeps the test from failing for a reason unrelated to the guarantee. Build the POST body from the field names the rendered form emits, not by hand. That single test is the whole no-loss guarantee and is the most valuable test in the feature.
- [ ] T015 [US2] Write a test that a populated field belonging to a group the current item type does not use is present in the response **and** its group is in the forced-visible set — the FR-010 guarantee. Then a test that changing the item type on POST retains values in groups the new type does not use (FR-014). Also assert the edit page's type select renders the item's stored type as selected — the failure T006's `x-init` prevents.
- [ ] T016 [US2] Write a test that saving through the form leaves the item's `ItemName`, `ItemDate` and `ItemIdentifier` rows unchanged in value, role and order (FR-012). Use the `populated_item` fixture in `tests/test_ui/conftest.py`.
- [ ] T017 [US2] Write `ItemUpdateView(MVPUpdateView)` in `literature/ui/views.py`, reusing `ItemForm` and `item_form.html`: `success_url = "detail"`, `show_list_action = show_detail_action = True` (plan D-6 — needed for both the shorthand and `get_breadcrumbs()`), the shared `CRUD_VIEWS`, translated `page_title`/`success_message`. Pass `groups_holding_values(self.object)` into the context as the forced-visible set. Make T014–T016 pass.
- [ ] T018 [US2] Add the reference-page entry point on `ItemDetailView`: `directory = ["update", "delete"]`, `show_update_action = show_delete_action = True`, and the shared `CRUD_VIEWS` replacing its current two-key override. Extend `TestItemDetailView` with a test that the Edit and Delete actions render and point at the right routes.
- [ ] T029 [US2] Write the CSL round-trip test that SC-006 asks for and nothing else covers: create an item through the create view with a representative spread of fields, call `to_csl_json` on the stored item, feed the result back through `from_csl_json`, and assert the two items are equivalent. One test in `tests/test_ui/test_views.py`, no new mechanism. Article IX makes round-trip fidelity the load-bearing contract, so a reference entered by hand has to reach the same standard as an imported one.

**Checkpoint**: a reference can be corrected, and nothing is lost by doing so.

---

## Phase 4: US-3 — Remove a reference that does not belong (P3)

**Goal**: one reference at a time can be removed, behind a confirmation, without taking contributors with it.

- [ ] T019 [US3] Write the `TestItemDeleteView` class in `tests/test_ui/test_views.py`, failing, one test per acceptance scenario of US-3: GET renders a confirmation naming the reference and deletes nothing; **the confirmation's Back link points at that reference's own page and the item still exists** (FR-018, US-3 scenario 2 — the scenario the first draft of this task missed); POST removes the item together with its `ItemName`, `ItemDate` and `ItemIdentifier` rows and redirects to the catalogue; the `Name` records survive whether or not they are credited elsewhere, and a contributor left credited on nothing still renders their own page; removing the last reference leaves the catalogue rendering its empty state; an unknown pk answers 404.
- [ ] T020 [US3] Write `ItemDeleteView(MVPDeleteView)` in `literature/ui/views.py`: `show_related_objects = True` so the confirmation lists what goes with the reference (FR-019), `require_confirmation` left off (plan D-7), `success_url = "list"` with `show_list_action = True` — `MVPDeleteView` deliberately does not consult `get_absolute_url()`, and the shorthand does not resolve without the flag. Also `show_detail_action = True` and an override of `get_back_url()` returning the `detail` shorthand, honouring an inherited `?back` first: the stock fallback is the catalogue list, and the detail page's delete link carries no `?back`, so declining would otherwise land on the catalogue and break FR-018 (plan D-7). Assign the shared `CRUD_VIEWS`. Translated `page_title`/`success_message`. Make T019 pass. django-mvp's `delete_view.html` renders the whole confirmation, so no template is written here.

**Checkpoint**: all three flows work through the interface.

---

## Phase 5: US-4 — The demo shows the flows, and a broken one is caught (P4)

**Goal**: the demo carries the flows and the guard walks them.

- [ ] T021 [US4] Extend `demo/smoke.py` with a write pass over the demo project's own settings and URLs, following links as the existing walk does: create a reference, follow to its page, correct a field and confirm the change renders, remove it and confirm the catalogue no longer lists it. Assert the catalogue changed as each step claims rather than that a page returned 200 (FR-032). Keep the existing read walk intact — this is an addition. The guard still asserts no page redirects to a login (FR-033). Two mechanics the module does not have today and needs, both within its standard-library-only constraint: build one `urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))` reused across the walk and scrape `name="csrfmiddlewaretoken"` out of each form page, posting it back with a `Referer` header — the module currently calls `urlopen` bare and the demo runs `CsrfViewMiddleware`, so a POST as it stands returns 403. And build every POST body by parsing the field names the rendered form emits, so the correct step round-trips the whole form with one field changed. Posting only the changed field blanks the other 59, for the same `construct_instance` reason plan D-3 states — which also makes this step the over-HTTP proof of SC-003.
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

- Phase 1 blocks everything. T006 blocks every view task.
- Phase 2 blocks Phase 3 (the update view reuses `ItemForm` and `item_form.html`).
- Phase 3 blocks Phase 4 only through `ItemDetailView`'s `directory`, which T018 sets.
- Phase 5 needs all three flows.
- Phases 2–4 share `views.py`, `item_form.html` and `test_views.py`, so they run sequentially. No `[P]` tasks in this feature.

## Design-review amendments (2026-08-13, S3R)

One round, thirteen findings, three of them verified high. Every one applied. Summary, so the
implementer knows which instructions above are corrections rather than first drafts:

- **DR-001** every `show_<action>_action` defaults to `False`, so `directory` alone renders nothing and a CRUD shorthand in `success_url` degrades to a literal relative redirect → flags named in T010, T012, T017, T018, T020 and tabulated in plan D-6.
- **DR-002** `form_view.html`'s stock buttons post `default_next=list`, which is consulted ahead of `success_url` → T011 overrides `{% block actions %}`; T009 and T014 post what the page actually emits.
- **DR-003** nothing seeded `form.itemType`, so the edit page would render with no type selected and the create page's guard would throw → `x-init` in T006, `|| []` in T011's expression.
- **DR-004** declining the delete confirmation fell back to the catalogue → `get_back_url()` in T020, scenario test in T019.
- **DR-005** `demo/smoke.py` has no cookie jar and no CSRF handling → mechanics named in T021.
- **DR-006** T007's assertion contradicted T010's partial `crud_views` override → one shared `CRUD_VIEWS`.
- **DR-007** T001 turned a pre-existing passing test red, and D-5 had the mechanism wrong (`AttributeError`, not a bootstrap4 fallback) → both corrected, Article I decision recorded in plan D-5.
- **DR-008** SC-006 had no task → T029.
- **DR-009** FR-002's type-first rule had no treatment and no test → stated in plan D-3, asserted in T009.
- **DR-010** SC-003's "byte-identical" cannot include `auto_now` fields → exclusion named in T014.
- **DR-011** "89 fields" was a count across every model in `models.py`; `Item` declares 64, 60 on the form → corrected in plan.md and research.md.
- **DR-012** T004 duplicated T003 with no checkable exit → folded into T003 and struck.
- **DR-013** SC-002 had no assertion → ceiling added to T002.

The reviewer confirmed plan D-3's no-loss guarantee holds as a data claim, with the limit now stated
in D-3 itself: structural for the rendered page, not for the endpoint. The security lens produced no
finding.

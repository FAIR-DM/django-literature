# Progress — 008 Add, Edit and Remove References Through the Front End

Append-only. Each entry is dated, states what happened, and never rewrites an earlier one.

## 2026-08-13 — S0 INTAKE

Grilled from issue #47. Grounded first on the issue standalone, its dependency #45 (merged as
PR #55), the three open siblings citing R6 (#48, #49, #50), the delivered #46, roadmap item R6 and
goal G4, then on the code the feature lands in: `literature.ui` carries no form, no POST handler and
no write path of any kind today.

Three questions, all answered by the maintainer:

1. Access control. Answer: none. The write pages are open exactly as the read pages are, because the
   package is developed for one person managing their own library. Permissions arrive later as their
   own work.
2. How much of the record someone meets. Answer: the item type is chosen first and the form is scoped
   to the fields applying to that type, with the rest reachable and any populated field always shown.
3. The citation key. Answer: typed by hand, and collisions are not the software's problem — nothing
   warns, refuses or rewrites. The maintainer additionally ruled the store's own import-path
   de-duplication wrong on the same reasoning, filed as issue #69 for separate resolution.

Issue labelled `accepted`. One planning input recorded rather than treated as a requirement:
Alpine.js ships with django-mvp and is the preferred mechanism for type scoping.

## 2026-08-13 — S1 SPECIFY

`spec.md` written: 4 user stories (P1–P4), 34 functional requirements, 6 success criteria, cites G4.
Clarification scan resolved seven ambiguities from intake context without escalation, each recorded
under `## Clarifications` and reasoned out in `decisions.md` as D1–D7.

One scan question changed the spec materially. The draft asserted the item-type-to-field mapping
would derive from CSL JSON's own definition of which variables each type uses. Checking rather than
assuming showed no such definition exists: `csl-data.json` declares all 103 properties flat with no
conditional on `type`, the specification lists variables by data category and uses type only to drive
style conditionals, and neither reference processor carries a table. The nearest published mapping,
Zotero's schema, covers 32 of 45 types and carries no licence at all. FR-004 was rewritten to make
the mapping an artefact this package authors and owns, and FR-004a added to bind it to presentation
so it can never restrict what is storable. Recorded as D1.

Spec lint green: `stage-exit --stage S1` green, no unresolved markers.

## 2026-08-13 — S2 SETUP

Branch `008-add-edit-remove-references` pushed as `fairdm-bot` (push actor = bot). Issue #47 promoted
to epic in place, retitled `FS-008: Add, edit and remove references through the front end`, intake
paragraph preserved under `## Original request`. Four story sub-issues created and linked: #70 (P1),
#71 (P2), #72 (P3), #73 (P4), no lifecycle labels, no milestones (matching FS-007). Draft PR #74
opened by `fairdm-bot[bot]`, title byte-identical to the epic, milestone `v1.0.0`, description
carrying a `Closes` line for the epic and one per story.

`check-issue-titles` green. `stage-exit --stage S2` green.

## 2026-08-13 — GATE_SPEC: APPROVED

Approved by Sam in session, 2026-08-13. Gate brief posted as a bot comment on epic #47
(comment 5280894807) covering the story list, the seven self-resolved ambiguities, and three open
risks: the package-owned type-to-field mapping joining the public surface, the openness of the new
write pages, and the import path's contradictory citation-key de-duplication (#69). No conditions
attached, no scope changes requested.

## 2026-08-13T14:32:45Z · Implementer US1 · T001

Did: set `CRISPY_TEMPLATE_PACK = "tailwind"` in `tests/settings.py` and `demo/settings.py`, each with
a comment naming the `AttributeError` it prevents (plan.md D-5). Dropped the single
`tests/test_ui/test_smoke.py:90` assertion that the setting was absent, replacing it with a comment
citing D-5; left the `CRISPY_ALLOWED_TEMPLATE_PACKS` assertion beside it untouched.

Verified: `poetry run pytest tests/test_ui/test_smoke.py -q` — before the test edit, 7 passed, 1
failed (`test_mvp_precedes_crispy_tailwind`, `assert not True` on `hasattr(settings,
"CRISPY_TEMPLATE_PACK")`, the expected failure). After the edit, 8 passed.

Next: T002, the failing structural test for the field-group partition.

Watch: none.

## 2026-08-13T14:45:00Z · Implementer US1 · T002

Did: wrote `tests/test_ui/test_fieldgroups.py` — the partition of `Item`'s 60 form fields into
groups, coverage of all 45 `ItemType` values (core/general always present, processor never), that
every group a type names is real, the ArticleJournal ceiling (SC-002, DR-013), and the shape of
`groups_holding_values()`.

Verified: `poetry run pytest tests/test_ui/test_fieldgroups.py -q` — 1 error at collection,
`ModuleNotFoundError: No module named 'literature.ui.fieldgroups'` (right reason: the module does
not exist yet).

Next: T003, the mapping itself.

Watch: none.

## 2026-08-13T15:05:00Z · Implementer US1 · T003

Did: wrote `literature/ui/fieldgroups.py` — the thirteen groups exactly as plan.md D-1 tabulates
them, translated group labels, and the `FieldGroups` class (`groups_for`, `fields_for`,
`groups_holding_values`). Populated `TYPE_GROUPS` for all 45 types, applying D-1's six criteria in
the stated order; C4 and C5 name no worked examples in the plan, so each use of them states which
of three sub-cases it is (D9 in decisions.md). Every entry carries a one-line comment naming the
criterion. Checked every type's resolved field count against research.md §1's Zotero band
(16–35, median 24, 32 types covered): nine covered types resolve below it (`dataset`, `document`,
`interview`, `manuscript`, `map`, `personal_communication`, `post`, `post-weblog`, `software`), each
with a stated reason; the 13 types Zotero does not cover rest on the criteria alone. `titles` is
assigned to no type at all — no criterion names it — recorded in the module docstring per T003's
instruction to say so here: it is reachable only through the form's "Show every field" toggle, for
every type.

Verified: `poetry run pytest tests/test_ui/test_fieldgroups.py -q` — 11 passed. `poetry run ruff
check literature/ui/fieldgroups.py tests/test_ui/test_fieldgroups.py` — all checks passed. Cross-
checked every type's field count and Zotero-band annotation against the code with a one-off script
(`FieldGroups.groups_for(t)` summed against `FieldGroups.GROUPS`), all 45 counts matched the
comments written into `TYPE_GROUPS`.

Next: T005, the failing form tests.

Watch: the per-type judgement calls in `TYPE_GROUPS` (especially C4/C5) are the artefact most likely
to draw review comment — each is commented, but they are editorial, not derivable.

## 2026-08-13T15:20:00Z · Implementer US1 · T005

Did: wrote `tests/test_ui/test_forms.py` — `ItemForm` declares every one of `Item`'s 60 scalar
fields and none of `categories`/`custom`/`created`/`modified`; `type` + `citation_key` alone make a
valid form; either missing is invalid and names the field; a `citation_key` duplicating a stored
item's is valid (FR-007) and the duplicate is stored unchanged.

Verified: `poetry run pytest tests/test_ui/test_forms.py -q` — 1 error at collection,
`ModuleNotFoundError: No module named 'literature.ui.forms'` (right reason: the module does not
exist yet).

Next: T006, `ItemForm` itself.

Watch: none.

## 2026-08-13T15:32:00Z · Implementer US1 · T006

Did: wrote `literature/ui/forms.py` — `ItemForm(ModelForm)`, `Meta.fields` built from
`fieldgroups.GROUPS`'s own partition (union of all thirteen groups) rather than a second hand-typed
list, so the form's field set and the mapping cannot drift apart. The `type` widget's `attrs` carry
both `x-model="form.itemType"` and `x-init="form.itemType = $el.value"` per plan.md D-3 —
`cotton/form/index.html` opens `x-data="{form: {}}"` empty, so `x-init` is what reads the
server-rendered value back into Alpine's scope. No label or help text is restated; both come from
the model.

Verified: `poetry run pytest tests/test_ui/test_forms.py -q` — 7 passed. Also ran
`tests/test_ui/test_forms.py tests/test_ui/test_fieldgroups.py` together — 18 passed, confirming
T006 did not disturb T002/T003. `poetry run ruff check literature/ui/forms.py
tests/test_ui/test_forms.py` — all checks passed.

Next: T007, the URL-reversal tests for Phase 2.

Watch: none.

## 2026-08-13T15:50:00Z · Implementer US1 · T007

Did: wrote `literature:item-create` reverses, and a per-view test that every action a view's own
`show_<action>_action` flags mark as shown resolves through its `crud_views` (DR-006's iterate-the-
views fix). Deviated from `tasks.md`'s literal text, which also asks for `literature:item-update` and
`literature:item-delete` to reverse: `ItemUpdateView` (T017) and `ItemDeleteView` (T020) are separate
stories' own tasks and do not exist in this worktree. Recorded as D10 in decisions.md.

Verified: `poetry run pytest tests/test_ui/test_urls.py -q` — 1 error at collection,
`AttributeError: module 'literature.ui.views' has no attribute 'ItemCreateView'` (right reason).

Next: T008, the create route.

Watch: whoever's brief adds `ItemUpdateView`/`ItemDeleteView` needs to add their own route
alongside — flagged in this story's `concerns`.

## 2026-08-13T15:58:00Z · Implementer US1 · T008

Did: added `add/ → item-create` to `literature/ui/urls.py`. Per D10, `item-update`/`item-delete` are
not registered here.

Verified: `poetry run pytest tests/test_ui/test_urls.py -q` — still the same collection error as
T007 (`ItemCreateView` still doesn't exist). Tree is not green after this commit alone by design —
tasks.md's own checkpoint for this slice is T010 ("Make T009 pass"), not T008 in isolation.

Next: T009, the failing `TestItemCreateView`.

Watch: none.

## 2026-08-13T16:20:00Z · Implementer US1 · T009

Did: wrote `TestItemCreateView` in `tests/test_ui/test_views.py`, one test per US-1 acceptance
scenario, plus `create_page_post_data()` — builds every POST in the class from the rendered create
page's own form (including whatever the Save button's own name/value pair is) rather than a bare
hand-typed dict, so a regression to django-mvp's stock `default_next=list` button would be caught by
the redirect-target assertions rather than silently passing (plan.md D-3).

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemCreateView -q` — 1 error at
collection, `AttributeError: module 'literature.ui.views' has no attribute 'ItemCreateView'`.

Next: T010, `ItemCreateView` itself.

Watch: none.

## 2026-08-13T16:45:00Z · Implementer US1 · T010

Did: wrote `ItemCreateView(MVPCreateView)` — `form_class=ItemForm`, `success_url="detail"`,
`show_list_action`/`show_detail_action` both set (D-6), translated `page_title`/`success_message`
using the catalogue's own vocabulary. Added the shared `CRUD_VIEWS` module constant (D-6, all five
actions, `literature:` namespaced) and assigned it here and on `ItemListView` (see T012 below — the
two changes landed in one commit since both are edits to the same file; noted as a one-task-one-commit
deviation). Added `_field_group_context(form)`: pulls `type` out of `core` and returns every other
group as a `{key, label, fields}` dict in a fixed order, plus `TYPE_GROUPS_JSON` computed once at
import time.

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemCreateView -q` — still failing at
collection (template does not exist: T011 next). `literature.ui.views` now has `ItemCreateView`, so
the failure moved from `AttributeError` to `TemplateDoesNotExist` once exercised.

Next: T011, `item_form.html`.

Watch: none.

## 2026-08-13T17:15:00Z · Implementer US1 · T011

Did: wrote `literature/ui/templates/literature/ui/item_form.html`. Overrides `{% block page.content
%}` in full rather than only `formset`/`actions` — `form_view.html`'s own `<c-form :form-obj="form"
...>` fires `<c-form.render />` unconditionally, which is the whole-form-through-one-crispy-call D-3
says this template avoids, and no block `form_view.html` exposes wraps that call. Recorded as D11.
The type field renders unconditionally, ahead of every group; each of the thirteen groups gets an
`x-show` guard built from `TYPE_GROUPS_JSON`; every value lives under `form.*` (never a bare top-level
Alpine variable — D11 explains why that would silently leak to `window` instead of becoming reactive).
`{% block actions %}` carries one Save button with no `name`/`value` pair. The "Show every field"
toggle uses `<c-form.field type="checkbox">` rather than hand-written daisyUI classes, to stay inside
this app's own utility-class allowlist (`tests/test_ui/test_templates.py`, T021/FR-008) — the first
attempt used raw `class="label"`/`class="checkbox"` and that pre-existing test caught it immediately.

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemCreateView -q` — 8 passed. Full
`tests/test_ui/` — 267 passed, including the utility-class allowlist test. `poetry run ruff check
literature/ui/views.py literature/ui/urls.py tests/test_ui/test_views.py tests/test_ui/test_urls.py`
— all checks passed (one import-order autofix in `literature/ui/views.py`).

Next: T012's test (the view-side change already landed in this commit's predecessor), then T013.

Watch: none.

## 2026-08-13T17:20:00Z · Implementer US1 · T012

Did: extended `TestItemListView` with a test that the catalogue's Add link renders and points at
`item-create`. The view-side change (`directory = ["create"]`, `show_create_action = True`,
`crud_views = CRUD_VIEWS` on `ItemListView`) landed already in T010's commit, since both were edits to
`literature/ui/views.py` made in the same pass — a one-task-one-commit deviation, noted honestly
rather than split after the fact by rewriting history.

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemListView -q` — 12 passed
(immediately, since the view-side change already existed).

Next: T013, the tailwind-pack rendering test.

Watch: none.

## 2026-08-13T17:30:00Z · Implementer US1 · T013

Did: wrote `TestCreatePageRendersTheTailwindPack`, asserting the create page's own HTML carries
crispy_tailwind's exact label class string and neither of bootstrap4's `form-label`/`form-control`
tokens (plan.md D-5).

Verified: `poetry run pytest tests/test_ui/ -q` — 269 passed. `poetry run ruff check
tests/test_ui/test_views.py` — all checks passed.

Next: full-story verify (`poetry run pytest -q && poetry run pre-commit run --all-files`) and the
completion report.

Watch: the two recorded deviations (D10 — item-update/item-delete routes not registered; D11/commit
bundling — T010 and T012's views.py edits landed in one commit) belong in the completion report's
`deviations`/`concerns`, not silently absorbed.

## 2026-08-13T15:20:00Z · Implementer (corrective) · T030

Did: extended `tests/test_ui/test_fieldgroups.py` with `TestCorrectedC2Criterion` — `container` in
`groups_for()` for the 17 types the base branch's corrected plan.md D-1 (C2, C2a) names, plus
`publication` for software. Ran and watched all 12 fail for the right reason (missing group
membership), committed the failing test. Then re-ran the full itemized C2 evidence in plan.md D-1
point 2 against every type rather than just the 11 named in the defect paragraph, per the task's
"re-derive each entry" instruction, and found three more gaps the same criterion-misreading pattern
produced: `song` missing `numbering` (chapter-number), `book` missing `numbering`
(number-of-volumes/ISBN), `patent` missing `legal` (authority/jurisdiction/division — patent sits
outside the named legal-types cluster). Added three more failing tests for those, watched them fail,
committed. Then rewrote `TYPE_GROUPS` entries for all 16 affected types plus `software`, keeping one
comment line per type naming its criterion(s) and field count. `book` now resolves to 36 fields,
one above the stated 16–35 plausibility band; documented why in the entry's comment (CSL's own text
names `number-of-volumes` for book directly, and Zotero's schema — which sets the ceiling, not a
rule — has nothing equivalent for its own book type).

Verified: `poetry run pytest tests/test_ui/test_fieldgroups.py -q` — 32 passed. `poetry run pytest
tests/test_ui/ -q` — 290 passed (269 baseline + 21 new). Field counts in every touched comment
checked against `FieldGroups.groups_for()` output directly, not computed by hand.

Next: nothing — this closes T030. Full-story verify (`poetry run pytest -q && poetry run pre-commit
run --all-files`) still to run before the completion report.

Watch: the three additional corrections (song, book, patent) are outside the defect paragraph's
named list but inside T030's own instruction to re-derive against the full itemized evidence, not
patch the named symptoms only — flagged in the completion report's `deviations` for visibility.

## 2026-08-13T18:09:00Z · Implementer US2 · T014

Did: added `update_page_post_data()` (same technique as US-1's `create_page_post_data` — GET the
rendered page, read every field's bound-form value, carry the Save button's own name/value pair if
it has one) and `TestItemUpdateView::test_saving_an_unchanged_form_leaves_every_stored_field_identical`
— SC-003's round trip. Built an item with a value in every `ItemForm` field (via `FORM_FIELDS`) plus
`categories` and `custom` (which the form never carries, D-4), GET the edit page, POST it back
unchanged, and compare every concrete field on the model except `created`/`modified` (auto_now_add/
auto_now, DR-010) before and after.

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemUpdateView -q` — 1 failed,
`NoReverseMatch: Reverse for 'item-update' not found` — the right reason, since neither the view nor
the route exist yet.

Next: T015.

Watch: nothing.

## 2026-08-13T18:12:00Z · Implementer US2 · T015

Did: three more tests on `TestItemUpdateView` — a populated field outside the current type's own
groups is present in the DOM (`id_authority`) and its group ("legal") is in `forced_groups_json`
(FR-010); changing the item type on POST retains a value in a group the new type does not use
(FR-014); the edit page's type `<select>` renders the item's stored type as the `selected` option
(the failure US-1's T006 `x-init` guards against on the client, asserted here at the server-rendered
HTML level).

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemUpdateView -q` — 4 failed, all
`NoReverseMatch` on `literature:item-update` — same right reason as T014.

Next: T016.

Watch: nothing.

## 2026-08-13T18:14:00Z · Implementer US2 · T016

Did: `test_saving_through_the_form_leaves_contributor_date_and_identifier_rows_unchanged` on
`TestItemUpdateView`, using the `populated_item` fixture (`tests/test_ui/conftest.py`, US-1's). Saves
through the update form and asserts the `ItemName`/`ItemDate`/`ItemIdentifier` rows are pk-for-pk,
value-for-value unchanged — `ItemForm` carries none of them, so the guarantee is that a save never
touches them at all (FR-012).

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemUpdateView::test_saving_through_the_form_leaves_contributor_date_and_identifier_rows_unchanged -q`
— 1 failed, `NoReverseMatch` on `literature:item-update` — same right reason.

Next: T017, to make T014–T016 green.

Watch: nothing.

## 2026-08-13T18:20:00Z · Implementer US2 · T017

Did: `ItemUpdateView(MVPUpdateView)` in `literature/ui/views.py` — `form_class = ItemForm`,
`template_name = "literature/ui/item_form.html"` (both reused unchanged from US-1, per the brief),
`success_url = "detail"`, `show_list_action = show_detail_action = True`, `crud_views = CRUD_VIEWS`,
translated `page_title`/`success_message`. `_field_group_context()` gained an optional
`forced_groups` parameter, defaulted to empty so `ItemCreateView`'s call site needs no change, and now
always emits `forced_groups_json` (previously absent — `item_form.html` already defaulted the key to
`[]` in the template, so this is not a behaviour change for the create page). `ItemUpdateView.get_context_data()`
passes `FieldGroups.groups_holding_values(self.object)` as the forced set. Registered
`<int:pk>/update/` → `item-update` in `literature/ui/urls.py`, updated its module docstring
(item-update is no longer "not registered yet"; item-delete still is, naming US-3). Extended
`tests/test_ui/test_urls.py`: a `TestUpdateRouteReverses` class (mirroring US-1's
`TestCreateRouteReverses`) and added `views.ItemUpdateView` to `TestCRUDViewsReverse`'s parametrize
list per plan.md D-6's "every name in every view's crud_views reverses" guarantee — its docstring
already anticipated this ("whichever task adds each of those views is expected to register its own
route alongside it"), so this extends rather than weakens that shared test.

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemUpdateView -q` — 5 passed.
`poetry run pytest tests/test_ui/test_views.py::TestItemCreateView tests/test_ui/test_urls.py -q` —
16 passed (no regression from the `_field_group_context` signature change or the shared crud_views
test extension). `poetry run pytest tests/test_ui/ -q` — 297 passed.

Next: T018.

Watch: the SC-003 test initially failed on `language`/`year_suffix` (max_length=10) because Django's
`CharField` strips surrounding whitespace by default and a space-joined synthetic value could land
mid-space after truncation — switched to underscore-joined synthetic values so truncation never
introduces a strippable trailing space. Not a production defect, a test-data artifact; noted here
rather than silently reworked.

## 2026-08-13T18:35:00Z · Implementer US2 · T018

Did: `test_the_edit_action_renders_and_points_at_the_update_page` on `TestItemDetailView` — asserts
the reference page carries an `href` to the item's update URL. Watched it fail (the button's markup
absent from the response) before implementing. Then on `ItemDetailView`: `directory = ["update",
"delete"]` (per plan.md D-6's table, and matching `MVPDetailView`'s own default directory),
`show_update_action = True`, `crud_views = CRUD_VIEWS` replacing the former two-key override.
`show_delete_action` is deliberately **not** set — see `decisions.md` D13.

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemDetailView tests/test_ui/test_views.py::TestReferencePageReadability -q`
— 64 passed. `poetry run pytest tests/test_ui/ -q` — 298 passed.

Next: T029.

Watch: T018's tasks.md text also assigns `show_delete_action = True` and a Delete-action assertion;
deferred per `decisions.md` D13 — flagged in the completion report's `deviations`.

## 2026-08-13T18:45:00Z · Implementer US2 · T029

Did: `TestCSLRoundTrip` in `tests/test_ui/test_views.py` — creates an item through the create view
with a representative spread of scalar fields (title, container_title, volume, issue, page, abstract,
language), calls `to_csl_json()` on the stored item, feeds the result through `from_csl_json()`, and
asserts the two items' CSL JSON is equal except for `"id"` (citation_key), which `from_csl_json`'s own
dedup logic is expected to change since the original item with that key is still in the store. No
production code changed — SC-006 coverage over US-1's create view and the pre-existing converters.

Verified: `poetry run pytest tests/test_ui/test_views.py::TestCSLRoundTrip -q` — 1 passed.

Next: full-story verify (`poetry run pytest -q && poetry run pre-commit run --all-files`) and the
completion report.

Watch: nothing outstanding for US-2's own tasks.

## 2026-08-13T19:05:00Z · Implementer US3 · T019

Did: wrote `TestItemDeleteView` in `tests/test_ui/test_views.py` — one test per US-3 acceptance
scenario: GET renders a confirmation naming the reference and deletes nothing; declining returns to
the reference's own page with the item still present (FR-018, US-3 scenario 2, the one the first
draft of this task missed); an inherited `?back` is honoured ahead of that fallback; POST removes the
item together with its `ItemName`/`ItemDate`/`ItemIdentifier` rows and redirects to the catalogue;
`Name` records survive whether or not credited elsewhere, including a contributor left credited on
nothing whose own page still renders (FR-020); removing the last reference leaves the catalogue's
empty state; an unknown pk answers 404. Widened the module's `literature.models` import to add
`ItemDate`, `ItemIdentifier`, `ItemName`, `Name` for the cascade/survival assertions.

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemDeleteView -q` — 7 failed, all
`NoReverseMatch: Reverse for 'item-delete' not found` (right reason: neither the route nor the view
exist yet). `poetry run ruff check tests/test_ui/test_views.py` — all checks passed.

Next: T020, `ItemDeleteView` and its route.

Watch: none.

## 2026-08-13T19:25:00Z · Implementer US3 · T020 — BLOCKED

Did: `ItemDeleteView(MVPDeleteView)` in `literature/ui/views.py` — `show_related_objects = True`
(FR-019), `require_confirmation` left off (plan.md D-7), `success_url = "list"` with
`show_list_action = True`, `show_detail_action = True`, `crud_views = CRUD_VIEWS`, translated
`page_title`/`success_message`, and `get_back_url()` overridden to honour an inherited `?back` first
and otherwise fall through to the `detail` shorthand rather than `MVPDeleteView`'s own catalogue-list
fallback (FR-018, plan.md D-7). Registered `<int:pk>/delete/ → item-delete` in
`literature/ui/urls.py`, updated its module docstring. Set `show_delete_action = True` on
`ItemDetailView` (T018's deferred flag, decisions.md D13) and added
`test_the_delete_action_renders_and_points_at_the_delete_page` to `TestItemDetailView` (T018's
deferred test — the brief names this explicitly as US-3's to write). Added `TestDeleteRouteReverses`
to `tests/test_ui/test_urls.py` (mirroring `TestUpdateRouteReverses`) and extended
`TestCRUDViewsReverse`'s parametrize list with `views.ItemDeleteView` — additive to a shared test, not
a modification of it.

Verified: `poetry run pytest tests/test_ui/test_views.py::TestItemDeleteView tests/test_ui/test_views.py::TestItemDetailView tests/test_ui/test_urls.py -q`
— 77 passed, 3 failed. The 3 failures are `TestItemDeleteView`'s three GET-rendering scenarios
(confirmation renders and names the reference; decline returns to the reference; an inherited `?back`
is honoured); all four POST/404/empty-state scenarios pass, as does everything else in scope,
including the new detail-page delete-action test and both URL tests. Root-caused directly (not
assumed) rather than re-edited on a guess: `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -c
"from django.template.loader import get_template; get_template('cotton/form/render.html')"` fails with
the same `TemplateSyntaxError` on the template alone, no request or form involved. Recorded in full as
decisions.md D14: django-mvp's `cotton/form/render.html` (which `delete_view.html` renders through
unmodified, per D-7's "write no template") compiles a `{% crispy form %}` tag unconditionally at
first-compile regardless of which `{% if form.helper %}` branch would run at render time, and that
tag validates `CRISPY_TEMPLATE_PACK = "tailwind"` (plan.md D-5) against
`CRISPY_ALLOWED_TEMPLATE_PACKS`, which is unset in both `tests/settings.py` and `demo/settings.py` and
defaults to `("uni_form", "bootstrap3", "bootstrap4")` — a pack that is never in that tuple can never
compile. Plan.md D-5's own claim that this setting "is only consulted when the `{% crispy %}` tag is
given an explicit pack argument" is the mistake this surfaces; the probe above shows the default-pack
path is validated identically. `poetry run ruff check literature/ui/views.py literature/ui/urls.py
tests/test_ui/test_views.py tests/test_ui/test_urls.py` — all checks passed.

Next: nothing further to attempt inside this story's scope — the fix is a settings change
(`CRISPY_ALLOWED_TEMPLATE_PACKS`) in files this brief marks `must_not_touch`, and the one route that
avoids it (a custom delete template) is exactly what D-7 and the brief say not to write. Reported
blocked in the completion report, with decisions.md D14 as the full record.

Watch: `test_smoke.py`'s `assert not hasattr(settings, "CRISPY_ALLOWED_TEMPLATE_PACKS")` and plan.md
D-5's mistaken claim both need attention once the settings fix is scoped to a session that can touch
them — flagged in `concerns`.

## 2026-08-13T21:10:00Z · Implementer US4 · T021 — DONE

Did: extended `demo/smoke.py`'s write pass (plan.md D-9). Added `_FormFieldParser`
(`html.parser.HTMLParser`) and `_form_fields()`, which read the first `<form>` on a page into a
name→value dict the same way a browser's own submission would — an unnamed control (the "Show every
field" toggle) posts nothing, a `<select>`'s value is its `selected` option or otherwise its first
(browser default), a `<textarea>`'s value is its text content minus the one leading newline the HTML
spec has every browser strip. `DemoWalk.__init__` now builds `self.opener` via
`urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))`,
reused for every request the walk makes — a CSRF cookie set while GETting a form page has to still
be attached when the walk POSTs back to it. `_get` now reads through `self.opener` instead of a bare
`urllib.request.urlopen`; a new `_post` builds the request with a `Referer` header and the same
opener; both delegate to a new `_fetch` that carries the existing login-redirect and error handling.
Added `_CREATE_LINK_RE`, `_EDIT_LINK_RE`, `_DELETE_LINK_RE` and `DemoWalk._walk_write_pass`, called
from `run()` after the read walk: follows the catalogue's own Add link, creates a reference, follows
to its own page, follows its Edit link, corrects the title while posting the whole scraped form back
unchanged otherwise, follows its Delete link, and confirms the catalogue no longer lists it. Every
step asserts on content (the created/corrected title appears, the citation key survives the edit, the
catalogue's own link list changes), never a bare status code (ADR-0018), and the create/edit steps
also assert the redirect landed on the reference's own page rather than the catalogue.

Added to `tests/test_demo/test_smoke.py`: `TestSharedOpener` (the opener carries exactly one
`HTTPCookieProcessor`), `TestCreateLinkPattern`/`TestEditLinkPattern`/`TestDeleteLinkPattern` (each
regex against markup the front end really renders, mirroring the existing `TestItemLinkPattern`), and
`TestFormFields` (csrf token captured, a populated edit form's stored values captured, a textarea's
content captured, the unnamed toggle excluded, the delete confirmation carrying only the token).
Updated `TestUnauthenticatedWalk`'s two tests to monkeypatch `urllib.request.OpenerDirector.open`
instead of the now-unused `urllib.request.urlopen` — see decisions.md D16 for why changing this
pre-existing test is in scope.

Verified: `poetry run pytest tests/test_demo/test_smoke.py -q` — RED first (`ImportError: cannot
import name '_CREATE_LINK_RE'`, the right reason — the symbols did not exist yet), then GREEN, 18
passed, after one further fix (a raw parsed textarea value carried the widget template's leading
newline; stripped once in `_FormFieldParser`). `poetry run pytest tests/test_demo/ -q` — 40 passed.

Verified live, against a demo server built and seeded exactly as `.github/workflows/demo.yml` does
(`DEMO_DB_PATH` pointed at a scratch file, `migrate`, `seed_demo`, `runserver --noreload`, polled
until `/catalogue/` answered): `poetry run python demo/smoke.py http://127.0.0.1:8000` →
`OK: walked the demo catalogue, its second page, a reference and a contributor, and
created/corrected/removed a reference, at http://127.0.0.1:8000`, exit 0.

Next: T022, prove the guard by breaking each flow in turn.

Watch: none.

## 2026-08-13T21:40:00Z · Implementer US4 · T022 — DONE

Did: reinstated each of the three defects T021's write pass exists to catch, against the same live
demo server, restarting it between each so the change takes effect (`runserver --noreload`), then
reverted and confirmed `git diff --stat literature/` was empty before moving to the next. No other
code change — this task's evidence is the three runs themselves, recorded below verbatim.

**Run 1 — wrong `success_url`.** Changed `ItemCreateView.success_url` from `"detail"` to `"list"` in
`literature/ui/views.py`. `poetry run python demo/smoke.py http://127.0.0.1:8000`:
```
FAILED: http://127.0.0.1:8000/catalogue/ [200]: creating a reference did not redirect to its own page (landed on http://127.0.0.1:8000/catalogue/)
```
Exit 1. Names the create flow precisely: it redirected to the catalogue instead of the new
reference's own page. Reverted; `git diff --stat literature/ui/views.py` empty.

**Run 2 — a form field silently dropped.** In `_field_group_context` (`literature/ui/views.py`),
changed the group-field filter from `name != "type"` to also exclude `"citation_key"`, so the field
stops rendering (and therefore stops posting) while `ItemForm` still declares it. `poetry run python
demo/smoke.py http://127.0.0.1:8000`:
```
FAILED: http://127.0.0.1:8000/catalogue/32/update/ [200]: correcting a reference did not redirect to its own page (landed on http://127.0.0.1:8000/catalogue/32/update/)
```
Exit 1. Names the correction/edit flow: because `citation_key` is a required field, posting the form
without it re-renders the edit page invalid rather than saving a blanked value — the guard still
catches it and still names the broken flow, one step earlier than the no-loss assertion would have.
Reverted; `git diff --stat literature/ui/views.py` empty.

**Run 3 — a delete that does not delete.** Added a `form_valid` override to `ItemDeleteView`
(`literature/ui/views.py`) that redirects to the success URL without calling `self.object.delete()`.
`poetry run python demo/smoke.py http://127.0.0.1:8000`:
```
FAILED: http://127.0.0.1:8000/catalogue/ [200]: catalogue list still lists the deleted reference at /catalogue/33/
```
Exit 1. Names the delete flow: the confirmation "succeeded" but the reference is still listed.
Reverted; `git diff --stat literature/` empty.

**Final confirmation**, server restarted clean on the reverted tree: `poetry run python demo/smoke.py
http://127.0.0.1:8000` → `OK: walked the demo catalogue, its second page, a reference and a
contributor, and created/corrected/removed a reference, at http://127.0.0.1:8000`, exit 0.

Verified: the three runs above, plus the final clean run. `poetry run pytest -q` unaffected (this
task touches no test file).

Next: T023, confirm the documented start path reaches the new pages by following links only.

Watch: none.

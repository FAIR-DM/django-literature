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

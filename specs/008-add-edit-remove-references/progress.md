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

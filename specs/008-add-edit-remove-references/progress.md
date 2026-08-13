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

# Progress — 006 Browse the Reference Catalogue in an Opt-In Front End

Append-only. Each entry records a stage transition or a gate outcome at the moment it happened.

## 2026-08-11 — S0 INTAKE

Grilled from issue #45, its five R6 siblings (#46–#50), roadmap item R6, `GOALS.md`, `README.md`
and `memory/constitution.md`. Four questions asked and answered:

1. `literature.ui` inherits django-accounts-center's composition rule — django-mvp built-ins by
   default, a custom component raised before it is built, a local fill only as a bridge until an
   upstream release carries the component.
2. The catalogue list ships paginated here, in one fixed order. Search, facets and reader-chosen
   ordering stay with #49.
3. The reference page shows the whole record, not just contributors, dates and identifiers.
4. The pages are open by default. Gating is a later specification.

Feature statement confirmed. `accepted` added to #45 alongside the permanent `feature-request`
label.

## 2026-08-11 — S1 SPECIFY

`specs/006-browse-reference-catalogue/` created on branch `006-browse-reference-catalogue`.
`spec.md` drafted, clarification scan run in full: five ambiguities resolved from intake context
without escalating, recorded under `## Clarifications` and in `decisions.md` (D1–D6). Spec lint
green: every FR covered by a story, no unresolved markers, goal id cited.

## 2026-08-11 — S2 SETUP

Branch pushed as `fairdm-bot`. Issue #45 promoted in place to the epic
(`FS-006: Browse the reference catalogue in an opt-in front end`), intake body preserved under
`## Original request`. Three story sub-issues created with no lifecycle labels: #52 (P1), #53 (P2),
#54 (P3). Draft PR #55 opened bot-authored, milestone `v1.0.0`, `Closes` block seeded with one line
per issue. `forge check-issue-titles` green.

## 2026-08-11 — Spec gate, revision

Sam asked for a dedicated contributor-centred page at the gate, reversing the clarification scan's
D4. Added as User Story 4 at P4, with FR-032 through FR-038 and SC-010 through SC-012. D4 rewritten
with the original decision struck through rather than removed; D7 added for the non-merging of
identical stored names. Story #56 created and linked, epic body and PR description re-synced,
`forge check-issue-titles` green again. Revised gate brief posted to the epic as the bot.

## 2026-08-11 — Spec gate APPROVED

Sam approved the revised specification. Four stories in flight. State advances to S3 PLAN.

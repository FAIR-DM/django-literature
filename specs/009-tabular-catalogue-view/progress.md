# Progress — 009 A tabular catalogue view

Append-only. Each entry is written when the event happens, not reconstructed afterwards.

- **2026-08-19 — intake.** Issue #81 grilled and accepted. Six questions asked and answered: access control (none introduced), sortable headers (yes), the title column's shape (fallback chain), two further columns (item type, container title), which roles the credited-names column means (authors, falling back to editors), and whether the contributor page becomes a table (no).
- **2026-08-19 — specification.** `spec.md` written: five user stories, twenty-nine functional requirements, seven success criteria. Ten further ambiguities resolved from intake context and recorded under `## Clarifications`, with the longer reasoning in `decisions.md`. No unresolved markers.
- **2026-08-19 — setup.** Branch pushed under the repository's bot identity. Issue #81 promoted in place to the epic `FS-009: A tabular catalogue view`; story sub-issues #82–#86 created and linked. Draft pull request #87 opened bot-authored, milestone v1.0.0, with a closing line per issue. Title lint and the stage checks green.
- **2026-08-19 — awaiting sign-off** before planning starts. Raised for decision: the table rendering needs a third-party package in the `ui` extra, which the constitution's stack constraints admit only by amendment, and governance forbids amending mid-feature.

# Progress — 011 Import a bibliography file through the front end

| When | Event |
|---|---|
| 2026-08-24 | Intake on issue #50. Four questions, all answered: report exists once and is not stored; the reader always lands on a report rather than a redirect with a summary; the entry point is an action in the catalogue toolbar rather than a control on every page; the import runs in the request, with background imports deferred to their own specification. |
| 2026-08-24 | Issue #50 accepted. |
| 2026-08-24 | `spec.md` and `decisions.md` written. Eleven further ambiguities resolved without escalating, recorded in the clarification scan and in nine numbered decisions. |
| 2026-08-24 | Branch `011-import-bibliography-file` pushed. Issue #50 promoted to the feature's parent issue; story sub-issues #100, #101, #102 created; draft PR #103 opened against the v1.0.0 milestone. Issue-title lint green. |
| 2026-08-24 | Specification gate: **approved** by Sam, in session, with no changes requested. |
| 2026-08-24 | Plan, research and task graph written. Core handle-type defect found and raised as #104; FR-023 narrowed (D11). |
| 2026-08-24 | Design review: approve with six findings, three of them medium. Two changed the design — the table view does have a supported way to add a toolbar action, so the table wrapper template is dropped, and the card list's block override must re-render the whole action row rather than replacing it. The unauthenticated, unbounded upload is recorded as an accepted specification-level risk (D12) rather than fixed. Research R2, the plan, the task graph and the documentation task amended. |

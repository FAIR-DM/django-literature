# Progress — 007 A Runnable Demo That Serves the Front End Over Real References

Append-only. Each entry is dated, states what happened, and never rewrites an earlier one.

## 2026-08-12 — S0 INTAKE

Grilled from issue #46. Two questions, both confirmed without correction: the guard's subject is the
demo project's own settings and wiring rather than a second rendering of what the test suite already
covers, and the catalogue is a small fixed curated set of genuine published references rather than
volume. Issue labelled `accepted`.

## 2026-08-12 — S1 SPECIFY

`spec.md` written: 4 user stories (P1–P4), 25 functional requirements, 10 success criteria.
Clarification scan resolved six ambiguities from intake context without escalation; each is recorded
in `spec.md` under `## Clarifications` and reasoned out in `decisions.md` as D1–D6. Spec lint green:
every requirement maps to a story, every story carries acceptance scenarios, the spec cites G6, no
unresolved markers.

## 2026-08-12 — S2 SETUP

Branch `007-runnable-demo-project` pushed as the repository bot. Issue #46 promoted to epic in place
(retitled `FS-007: …`, body grown, intake paragraph preserved). Story sub-issues #59–#62 created
with no labels and linked under the epic. Draft PR #63 opened bot-authored, titled verbatim from the
epic, milestone `v1.0.0`, description carrying one `Closes` line per issue in the graph.
`check-issue-titles` green.

## 2026-08-12 — GATE_SPEC: APPROVED

Approved by Sam in session, without changes. Brief posted as a bot comment on the epic
(issue #46, comment 5264831385) covering the summary, goal link, story list, the six self-resolved
ambiguities and two risks. Recorded here at the moment of approval, before S3 creates the ledger.

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

## 2026-08-12 — S3R DESIGN REVIEW: CHANGES APPLIED

One reviewer, three lenses, one round. Verdicts: spec-compliance `request_changes` (high),
security `approve` (low), architecture `request_changes` (medium). Thirteen findings — two high,
eight medium, three low. Craft-skill receipts matched the registry in all three files. Every
remedy was applied to `plan.md` and `tasks.md`, and both blocking findings were verified against
the repository before the edit rather than accepted on the reviewer's word.

**SPEC-001 (high, verified).** Nothing in the plan ever ran `manage.py demo`. The workflow composed
`migrate` + `seed_demo` + a server start itself and the only command test covered `seed_demo`, so
the single documented command — the whole subject of FR-003, SC-001 and SC-002 — was checked by
nothing. T016 now starts the demo by running that command, which removes steps from the workflow
rather than adding them.

**SPEC-002 (high, verified).** `literature/converters.py:525-541` catches `ValidationError` per
entry, logs a warning and returns the survivors, so a rejected seed entry vanished silently: T008
reported a count and compared it to nothing, and T011 asserted the spread against the JSON file
rather than the loaded catalogue. A half-loaded catalogue would have passed every check with
SC-004 false in the running demo. T008 now fails when the loaded count does not match the file.

Also applied: `Name` rows are deleted on re-seed (they are shared between items and survive
`Item`'s cascade); `runserver` runs with the autoreloader off, which was re-running the destructive
seed on every file save and is also what makes the backgrounded command in CI a single process;
the demo carries the README's `mvp_config` context processor (SC-010); `demo/settings.py` reads its
SQLite path from an environment variable so the suite stops deleting the developer's demo database;
the smoke walk tries references in order until one has a contributor, rather than assuming the
first does; failures report a bounded excerpt, not a full `DEBUG` traceback page, into a public CI
log; the workflow takes `permissions: contents: read` and no secrets, being the first job here to
run the pull request head's own code; `tests/test_demo/` is declared once as a non-mirror path with
its real reason; and T020 was dropped as work to remove.

Ledger and `forge stage-exit --stage S3R` green.

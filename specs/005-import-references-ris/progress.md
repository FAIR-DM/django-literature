# Progress — 005 Import References from RIS Files

Append-only. One entry per stage transition, gate outcome, or escalation.

## 2026-08-05 — S0 INTAKE → S1 SPECIFY

Grilled against issue #23, roadmap R5, the two delivered dependencies (#21, #22) and their specs,
`GOALS.md` and `CONTEXT.md`. Two questions asked and answered: what becomes the citation key when
RIS supplies no cite key, and which producers' exports acceptance is judged against. Feature
statement confirmed by the maintainer. `accepted` label added to #23.

## 2026-08-05 — S1 SPECIFY → S2 SETUP

`spec.md` authored (4 stories, 36 FRs, 9 SCs) and the clarification scan run in full, five questions
self-resolved into `decisions.md` (D1–D10). The scan's largest catch: the draft used RIS's own word
*record* 74 times for a source entry, which `CONTEXT.md` retires on both sides of the import
boundary. Spec lint green — no unresolved markers, every FR mapped to a story, G5 cited.

## 2026-08-05 — S2 SETUP → GATE_SPEC

Branch pushed as `fairdm-bot`. Issue #23 promoted to epic in place (title `FS-005: Import references
from RIS files`, intake body preserved under `## Original request`). Story sub-issues #36–#39 created
with no lifecycle labels and linked via `addSubIssue`. Draft PR #40 opened bot-authored, title
byte-identical to the epic, `Closes` block carrying one line per issue, milestone `v1.0.0`.
`check-issue-titles` green. `stage-exit --stage S2` green.

## 2026-08-05 — GATE_SPEC: APPROVED

Approved by Sam in session: "Spec looks good. Proceed to planning." No changes requested to the six
self-resolved decisions surfaced in the gate brief. Gate brief mirrored as a bot comment on #23.

Sam also flagged that `main` had moved. The branch was rebased onto `7b4b866` (merge of #35) before
planning began, which brings the constitution to **v3.1.0** — three new core articles that did not
exist when the spec was written:

- **Article XIII — Data-model conventions.** No new model fields in this feature, so it bites only
  if the plan proposes one.
- **Article XIV — Test structure & fixtures.** `tests/test_importers/test_ris.py` already satisfies
  the mirror rule; the class-grouping and factory rules constrain how the suite is written.
- **Article XV — Cohesion.** The consequential one. The existing `bibtex.py` is 15 module-level
  functions that share subjects (normalization, name parsing, date parsing), which is the shape
  Article XV now rules out. RIS is planned to the article; `bibtex.py` is pre-existing drift and
  stays out of scope under the spec's own assumption that the BibTeX format is not modified.

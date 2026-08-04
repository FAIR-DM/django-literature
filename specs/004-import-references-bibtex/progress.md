# Progress — 004 Import References from BibTeX Files

Append-only run record. Each entry is written when the event happens, not reconstructed
afterwards.

## 2026-08-04

- **S0 INTAKE** — grilled from issue #22. Three points settled with the maintainer: recovery
  before rejection, one format for both BibTeX dialects, preservation on the record without
  per-field reporting. Feature statement confirmed. Issue labelled `accepted`.
- **S1 SPECIFY** — branch `004-import-references-bibtex` created; `spec.md` authored (4 stories,
  30 FRs, 9 SCs). Clarify taxonomy scan run against the drafted spec and found four items
  drafting had missed, including a direct contradiction between FR-004 (one entry at a time) and
  FR-015 (`crossref` inheritance). All four self-resolved and recorded in `decisions.md` (D4–D7)
  and inline under `## Clarifications`. Spec lint green.
- **S2 SETUP** — spec artifacts committed (`ede9e52`) and pushed as `fairdm-bot`. Issue #22
  promoted to epic in place, retitled `FS-004: Import references from BibTeX files`, intake body
  preserved under `## Original request`. Story sub-issues #30–#33 created under it, no lifecycle
  labels, linked via the sub-issues API. Draft PR #34 opened bot-authored, title byte-identical
  to the epic, `Closes` block covering the epic and all four stories, milestone `v1.0.0`.
  `forge check-issue-titles` green. `forge stage-exit --stage S2` green.
  Also carried FS-003's uncommitted ledger close-out (PR #29 merged) onto this branch, since
  `main` is protected.
- **Spec gate — APPROVED** by SamuelJennings, 2026-08-04, in session.
  Approval carried an explicit instruction that supersedes the pipeline's default: **the plan is
  a hard gate on this run, not a veto notification.** Work stops after S3 ANALYZE and does not
  enter S4 IMPLEMENT until the maintainer approves the plan.
- **S3 PLAN** — `research.md` settles the parser question Article VII requires a justification for:
  `bibtexparser>=1.4.4,<2` plus its declared `pyparsing`, two new runtime dependencies, with a
  hand-written parser, `bibtexparser` 2.0.0b9 and `pybtex` all evaluated and rejected for stated
  reasons. `plan.md` carries the design, the constitution check (no violation requiring
  justification), and one open question for the maintainer: the library resolves macros and
  cross-references in a single load, which makes FR-005 unnecessary and shows FR-004 to be
  stricter than the contract's FR-024 that it inherits from. A refinement is proposed and **not
  applied** pending a ruling. `tasks.md` breaks the work into 39 tasks across a setup phase, a
  blocking foundational phase, one phase per story, and a cross-cutting phase at convergence.
  `feature-state.json` written, all 39 tasks `todo`. `forge stage-exit --stage S3` green.
- **Plan review** — the maintainer challenged the split into `_bibtex_maps.py` and `_bibtex_clean.py`
  and was right: it was structure argued from a prediction about size rather than a measurement,
  which Article III bars. Collapsed to one `bibtex.py`, estimated 400–500 lines against
  `converters.py` at 542. The same correction applied to the tests, where the constitution requires
  test modules to mirror the `literature/` tree, so four planned test modules became one
  `test_bibtex.py` with concerns grouped by class. The parallel markers on tasks that now share that
  file were removed, since they were claiming a parallelism the layout no longer allows.
- **Plan gate — APPROVED** by SamuelJennings, 2026-08-04. The FR-004 and FR-005 refinement was taken
  as accepted with the plan, since the plan carried the recommendation, and this reading was stated
  back for veto rather than assumed silently. Applied to `spec.md` under `## Refinements` by
  strikethrough, so FR-006 onward keep the numbers the story issues cite and the issue graph needed
  no re-sync.
- **S4 IMPLEMENT** — begins here.

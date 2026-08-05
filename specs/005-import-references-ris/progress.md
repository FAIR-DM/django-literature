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

## 2026-08-05 — S3 PLAN → S3R DESIGN_REVIEW

Research (`research.md`, R1–R11) settled the parser decision and corrected two approved requirements
against genuine producer exports. `plan.md`, `tasks.md` and the ledger written. `stage-exit --stage
S3` green.

## 2026-08-05 — S3R: three lenses, one re-plan cycle, PASS

Round one returned four blocking findings, three of which two independent lenses reached separately:

- **FR-022 was unimplementable as designed.** `handle_for` runs before the de-duplication suffix
  exists. Moved to an `entry_created` override, which is a documented override point and needs no
  change to `base.py`.
- **The preservation sink was unnamed.** A flat `custom` write turns every unmapped tag into an
  `ItemIdentifier` row, and a value over 500 characters then fails the whole entry — the opposite of
  what US-4 requires. Now nested under `custom["ris"]`, mirroring BibTeX.
- **`T005` extracted BibTeX's LaTeX decoder into a shared module**, which would have silently
  rewritten RIS values. Narrowed to the two genuinely format-neutral normalizers.
- **A latent hang in `converters.py`.** `_generate_dedup_suffix` emits 701 suffixes then repeats
  forever while `_resolve_citation_key` loops until a free key. BibTeX never reached it because a
  `.bib` file carries its own keys. Minting makes collision the normal case, so this feature is what
  makes it reachable. Filed as **#41**.

Round two cleared the security and architecture lenses. One HIGH survived, on the #41 fix: the first
revision fixed it in this branch and amended T039 — the task that verifies SC-009 — to grant its own
exception, which is a gate certifying itself. SC-009 says such a change is "recorded as its own issue
rather than made here". **Resolved by removing T041 and landing #41 as its own pull request**, merged
before this feature. Same ordering outcome, and the approved success criterion stays true rather than
being amended.

Design-review cycles used: 1 of 1. Task count 37. `gates.design_review` recorded after the verdict,
not before.

## 2026-08-05 — Correction: issue #41 closed, severity was inflated

Sam challenged the de-duplication finding and was right. The code trace was correct; the severity was
adopted from the design-review panel rather than checked.

Reaching the ceiling needs 702 stored items sharing one base key, and a minted key is family name
*plus* year *plus* first significant title word — so it takes 702 records agreeing on all three, which
in practice means importing one record 702 times. That is artificial, not remote. The secondary
effect, one query per suffix candidate, costs a few dozen queries at realistic collision counts.

**#41 closed with its diagnosis preserved in the closing comment**, so it stays searchable without
sitting in the backlog. The plan's dependency on it is removed and `converters.py` is untouched,
which is what T039 asserts.

The process lesson, which is not about de-duplication: **a subagent reviewer's severity is a claim to
verify, not a verdict to adopt.** The trace was evidence; the reachability was mine to test and I did
not test it. Cost: one filed issue, a section of the plan, and a merge dependency invented for a
scenario nobody will meet.

## 2026-08-05 — Correction to the correction: #41 folds into this pull request

Sam's second challenge: considering the defect was fine, and fixing it is fine — what was not fine
was giving a two-line fix its own issue and pull-request cycle.

He is right, and the cause was a clause I wrote myself. SC-009's "recorded as its own issue **rather
than made here**" was authored at S1 to stop the import contract being widened to suit this format,
which is what makes the roadmap's claim about the second format falsifiable. At S3R it was read as
"no line of `converters.py` may change", and the review panel reinforced that reading. A loop that
terminates widens nothing and concedes nothing about the seam.

Splitting it also broke a standing rule of Sam's that predates this feature — a session's work lands
as one pull request, because splitting by concern multiplies his review, merge and rebase overhead.
That rule should have won over a criterion I had authored myself hours earlier.

Actions: **SC-009 amended** in place with a Refinements entry separating a widening (still its own
issue, still out of scope) from a defect fix that changes no public behaviour (may land here, issue
kept for traceability). **#41 reopened**, T041 restored to Phase 0 with the sharpened fix
specification, `Closes #41` added to PR #40's description. Task count 38.

The lesson, distinct from the previous entry's: **a criterion I wrote is not an external constraint.**
When my own spec text starts forcing an outcome that contradicts a standing instruction from Sam, the
text is what gives, and amending it is a normal move rather than a last resort.

## 2026-08-05 — Foundational Implementer dispatched (US0)

Skills loaded: `craft-tdd` (receipt `craft-tdd/2026-08-04/c95488d8`), `craft-increments` (receipt
`craft-increments/2026-08-05/d3dce07f`), both via the Skill tool. Baseline `forge verify` green
(conformance, lint, typecheck, 326 tests, build) immediately before starting.

### T001 — genuine corpus vendored

Did: added `tests/data/ris/genuine/{endnote,scopus,webofscience}.ris` from
`asreview/citation-file-formatting` (CC0-1.0, already staged locally from the S3 research pull),
each the same ten references from a different producer. `SOURCE.md` records origin, licence,
retrieval date and each file's fingerprint. The repo's own `trailing-whitespace`/`end-of-file-fixer`
hooks trimmed a trailing space after `ER  -`'s empty value and a final blank line on first commit —
noted in `SOURCE.md` rather than fought, since neither touches a tag or a value.

Verified: `poetry run pytest tests/test_importers/test_ris.py -q` — 5 passed. `poetry run
pre-commit run --files tests/test_importers/test_ris.py tests/data/ris/genuine/*` — clean after the
whitespace fix above.

Next: T003 (constructed malformation fixtures).

### T003 — constructed malformation fixtures

Did: 15 hand-written fixtures under `tests/data/ris/constructed/`, one per malformation
spec.md names (empty, missing/absent `ER`, no `TY` anywhere, post-entry tag block with no `TY`,
header material, BOM, CRLF, single-space separator, wrapped prose vs EndNote multi-value
continuation, `TY`-only, truncation, CP1252, an over-500-char unmapped tag value, a 500-entry
bulk file). `README.md` documents what each isolates. A structural test (`TestConstructedCorpus`)
asserts the named set matches disk exactly and each file's byte-level shape, since `RISParser`
doesn't exist yet — T006-T008 will drive these same files through it behaviourally.

Verified: `poetry run pytest tests/test_importers/test_ris.py -q` — 21 passed. `poetry run
pre-commit run --files ...` clean (end-of-file-fixer trimmed one trailing blank line in the bulk
fixture, re-verified the 500-entry count held after).

Next: T004 (negative fixtures).

### T004 — negative fixtures

Did: `tests/data/ris/negative/wos_native_tagged.ris` (rispy's `example_wos.ris`, MIT) and
`bibtex_under_ris_name.ris` (this repo's own BibTeX fixture content), both saved under a `.ris`
name — research.md R10's named negative corpus. `SOURCE.md` records origin and licence. A
structural test asserts neither file contains a line matching the RIS tag grammar (duplicated
locally, since `RISParser` doesn't exist until T006), so the eventual parser will correctly find
no entries to frame.

Verified: `poetry run pytest tests/test_importers/test_ris.py -q` — 26 passed. Pre-commit clean.

Next: T005 (extract normalizers.py).

### T005 — extract IdentifierNormalizer

Did: `literature/importers/normalizers.py`, new — `IdentifierNormalizer.normalize_doi` and
`.normalize_isbn`, moved verbatim from `bibtex.py`'s `_normalize_doi`/`_normalize_isbn`.
`bibtex.py` re-points `_IDENTIFIER_NORMALIZERS` to the new class and drops the two module-level
functions and their regexes. `_clean_text`, `_unescape_entities`, `_clean_identifier` untouched —
they stay put, per plan.md, since they decode a LaTeX/XML layer RIS does not have.

Verified: `poetry run pytest tests/test_importers/test_bibtex.py tests/test_converters.py
tests/test_importers/test_normalizers.py -q` — 333 passed. `git diff --stat -- \
tests/test_importers/test_bibtex.py tests/test_converters.py` — empty, confirming both stayed
unmodified. `poetry run mypy` — clean. `poetry run pre-commit run --files ...` — clean.

Next: T041 (dedup suffix ceiling).

### T041 — de-duplication ceiling fixed (closes #41)

Did: `_generate_dedup_suffix` in `literature/converters.py` now extends past the two-letter
product into three, four, ... letter suffixes (odometer over increasing lengths) instead of
cycling the two-letter product forever. First 701 values unchanged. New regression module
`tests/test_converters_dedup.py` (decisions.md D16 explains why not `tests/test_converters.py`)
tests the generator directly: 701-value prefix pinned, 20,000 values asserted distinct.

Verified: `poetry run pytest tests/test_converters_dedup.py tests/test_converters.py -q` — 83
passed. `git diff --stat -- tests/test_converters.py` — empty. `poetry run mypy` — clean.
`poetry run pre-commit run --files literature/converters.py tests/test_converters_dedup.py` —
clean.

Next: T006 (RISParser grammar and entry framing).

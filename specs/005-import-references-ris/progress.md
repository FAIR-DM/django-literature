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

### T006 — RISParser line grammar and entry framing

Did: new `literature/importers/ris.py` — `RISEntry` (tags, index, start_line) and
`RISParser.parse`, a generator opening at `TY` and closing at `ER` or the next `TY`. Decodes
`utf-8-sig` itself from a binary-mode file; `UnicodeDecodeError` becomes a translatable
`ParseError` naming the encoding and byte offset. Three whole-file outcomes distinguished (empty
→ nothing, tag-lines-no-TY → raise, no-tag-lines → raise). Header material yielded once as a
plain-string sentinel, only when non-empty (decisions.md D17). A malformed post-entry tag block
is recognised and silently dropped rather than failed — deferred to T021 (D18). `REPEATABLE_TAGS`
defined on the parser (D20) but not yet consumed — that's T007. Binary-mode contract documented
(D19).

Verified: `poetry run pytest tests/test_importers/test_ris.py -q` — 39 passed (all new
framing/encoding/streaming tests green on first implementation, no red-green cycle needed beyond
the initial "module doesn't exist" collection error). `poetry run pytest -q` (full suite) — 805
passed. `poetry run mypy` — clean. `poetry run pre-commit run --files literature/importers/ris.py
tests/test_importers/test_ris.py` — clean (ruff-format collapsed one multi-line frozenset literal).

Next: T007 (per-tag continuation lines).

### T007 — per-tag continuation lines

Did: `RISParser._continue_value`, called from `_entries` in place of the T006 placeholder.
Resolves an untagged line against `pairs[-1][0]` (the tag it follows): a `REPEATABLE_TAGS`
member appends a new `[tag, line.strip()]` pair; anything else joins `line.strip()` onto the
existing value with a single space. Tests red against `wrapped_prose.ris` and
`endnote_multivalue_continuation.ris` before the fix (4 failures, right reason: continuation
lines silently dropped), green after.

Verified: `poetry run pytest tests/test_importers/test_ris.py -q` — 46 passed. `poetry run
pytest -q` (full suite) — 812 passed. `poetry run mypy` — clean. `poetry run pre-commit run
--files literature/importers/ris.py tests/test_importers/test_ris.py` — clean (ruff-format
rewrapped one long assertion).

Next: T008 (whole-file outcomes, header sentinel raising SkipEntry).

### T008 — whole-file outcomes through the full import workflow

Did: nine `TestWholeFileOutcomes` tests calling `RISFormat().import_file(...)` (the full
workflow, not `RISParser` directly) over the whole-file cases: empty succeeds empty; no-TY and
no-tag-line fixtures each report one failed entry naming the reason, never raise; header material
reports one skipped entry with `item is None`; a header-less file reports no skip; a sweep over
every constructed and negative fixture confirms nothing raises. All passed on first run —
`RISFormat.to_csl_json`'s `SkipEntry`-for-the-header-sentinel handling was already written in
T006 alongside `RISParser`, so no red-green cycle was needed here; noted rather than fabricated.

Verified: `poetry run pytest tests/test_importers/test_ris.py::TestWholeFileOutcomes -v` — 9
passed. `poetry run pytest -q` (full suite) — 821 passed. `poetry run mypy` — clean. `poetry run
pre-commit run --files tests/test_importers/test_ris.py` — clean.

Next: T009 (RISFormat registration and the literature namespace export).

### T009 — RISFormat registration and the literature namespace export

Did: `RISFormat` appended to `DEFAULTS` in `config.py`; `RISFormat`, `RISEntry`, `RISParser`
exported from `literature.importers` (the latter two are public classes by Python convention, so
the pre-existing public-surface smoke test requires them exported). Added the docstrings
`RISFormat.parse`/`to_csl_json` were missing (`test_documentation.py` coverage check). Updated
two pre-existing tests that track the shipped-defaults surface — `test_config.py`'s
`test_an_unset_setting_yields_the_shipped_defaults` and `test_smoke.py`'s `PUBLIC_SURFACE` — the
same way both were updated when BibTeX first landed (their own comments record that precedent);
neither is `test_converters.py` or the BibTeX suite, so this is in scope.

`forge verify`'s conformance step then rejected the standalone `tests/test_converters_dedup.py`
from T041 outright — its mirror rule is path-based with no exception for "the file you're
forbidden to edit." Relocated that regression into `tests/test_ris.py` as
`TestGenerateDedupSuffix` instead (decisions.md D16, revised).

Verified: `poetry run pytest -q` (full suite) — 851 passed. `git diff --stat -- \
tests/test_importers/test_bibtex.py tests/test_converters.py` — empty. `poetry run mypy` — clean.
`poetry run pre-commit run --files ...` — clean. `forge verify --repo .` — conformance, lint,
typecheck, test, build all green.

**Foundational phase (US0) complete.** All nine assigned tasks (T001, T003, T004, T005, T041,
T006, T007, T008, T009) done, committed individually, tree green throughout.

### T010 — RIS reference-type table

Did: `REFERENCE_TYPE_TABLE`, a RIS reference type -> CSL item type dict of 55 codes, adapted from
citation-js's per-type table (MIT, research.md R3) rather than Zotero's (AGPL). Unmapped types fall
to `_FALLBACK_TYPE = "document"`. `GRNT`/`GRANT` (research R2's two specification generations) and
`UNPD`/`UNPB` are both listed explicitly so the spelling-variant equivalence is a documented mapping
rather than an accident of both being unrecognised. `RISFormat.to_csl_json` now reads `TY` and
looks the type up; nothing else in the result dict yet (citation key, contributors, dates,
identifiers land in T011-T016).

Verified: `poetry run pytest tests/test_importers/test_ris.py::TestReferenceTypeTable -v` — 60
passed (parametrized over every table entry, the unlisted-type fallback, and the two spelling-
variant pairs). Confirmed RED first: importing `REFERENCE_TYPE_TABLE` failed with `ImportError`
before the table existed. `poetry run pytest tests/test_importers/test_ris.py -q` — 125 passed.
`poetry run mypy literature/importers/ris.py` — clean. `poetry run pre-commit run --files
literature/importers/ris.py tests/test_importers/test_ris.py` — ruff-format reformatted the new
test class (line length); re-run clean after.

Next: T011 (core tag -> CSL variable table, with the T2/SP type-conditional cases).

### T011 — core tag to CSL variable table, T2/SP type-conditional resolution

Did: `FIELD_TABLE` (TI, AB, ST, VL, IS, LA, M3, ET, PB, CY -> their CSL variables), plus
`_container_or_collection_variable` and `_page_variable` for the two type-conditional cases. `T2`
resolves to `collection-title` on a type that is already its own container (`_BOOK_LIKE_TYPES` —
reused from research.md R4's "book-like" A2-resolution set, since it is the same underlying fact:
no container of its own) and to `container-title` everywhere else, which correctly covers `JOUR`
without needing it in that set. `SP` resolves to `number-of-pages` on `BOOK`/`EBOOK`/`EDBOOK`/`THES`
(research.md R11) and to `page` (a locator, which may be a whole range like `549-565`) elsewhere.

Verified: `poetry run pytest tests/test_importers/test_ris.py::TestCoreFieldMapping
tests/test_importers/test_ris.py::TestT2ContainerOrCollection
tests/test_importers/test_ris.py::TestSPLocatorOrPageCount -v` — 19 passed. Confirmed RED first:
all 18 new field-mapping assertions failed with `KeyError` before the table and resolvers existed.
`poetry run pytest tests/test_importers/test_ris.py -q` — 144 passed. `poetry run mypy
literature/importers/ris.py` — clean. `poetry run pre-commit run --files
literature/importers/ris.py tests/test_importers/test_ris.py` — clean.

Watch: `_BOOK_LIKE_TYPES` is reused for both T2 resolution and (T012) A2 collection-editor
resolution — a single source of truth for "this type is already its own container," not two tables
that could drift apart.

Next: T012 (contributors — repeated tags to contributor records, roles resolved on reference type).

### T012 — contributors, roles resolved on reference type

Did: `_name_to_csl` (RIS's own `Family, Given[, Suffix]` author format; no comma means
institutional/unparsed and goes to `literal` unsplit, FR-014), `_contributors` resolving `AU`/`A2`/
`A3` to their CSL role from the reference type (research.md R4): `AU` is `author` except on
`EDBOOK` where it is `editor`; `A2` is `editor` on the chapter-like set, `collection-editor` on
`_BOOK_LIKE_TYPES` (T011's same set — one source of truth for "this type has no container of its
own"); `A3` is `editor` only on `BOOK` (the one type where `A2`/`A3` invert) and `collection-editor`
on its own documented set. Contributors keep source order within each role (`list.append` in tag
order). `ED` (Web of Science's non-canonical editor tag) and `A2` resolving to `editor` on `JOUR`
are research.md R4/R9 findings explicitly assigned to T024 (US-3) — not built here.

Verified: `poetry run pytest tests/test_importers/test_ris.py::TestContributors -v` — 9 passed.
Confirmed RED first: all 8 role/order assertions failed with `KeyError` before `_contributors`
existed. `poetry run pytest tests/test_importers/test_ris.py -q` — 153 passed. `poetry run mypy
literature/importers/ris.py` — clean. `poetry run pre-commit run --files
literature/importers/ris.py tests/test_importers/test_ris.py` — clean.

Next: T013 (dates — PY anchors, DA refines precision, Y1 falls back, Y2 is the access date).

### T013 — dates: PY anchors, DA refines precision, Y1 fallback, Y2 access date

Did: `_ris_date_parts` (shared slash-separated parser for `PY`/`DA`/`Y1`/`Y2`'s common shape),
`_issued_date` (`PY` anchors the year; a same-year `DA` refines to month or day precision with no
padding; `Y1` supplies `issued` when `PY` is absent) and `_accessed_date` (`Y2`, unconditionally).
Recorded decisions.md D25: a `DA` whose parsed year disagrees with `PY`'s is not treated as a
refinement at all, since trusting its month/day while discarding its year would splice two
unrelated dates together — `PY`'s own precision is kept instead.

Verified: `poetry run pytest tests/test_importers/test_ris.py::TestDates -v` — 8 passed. Confirmed
RED first: all 7 date assertions failed with `KeyError` before `_issued_date`/`_accessed_date`
existed. `poetry run pytest tests/test_importers/test_ris.py -q` — 161 passed. `poetry run mypy
literature/importers/ris.py` — clean. `poetry run pre-commit run --files
literature/importers/ris.py tests/test_importers/test_ris.py` — clean.

Watch: Web of Science's year-less `DA` (`SEP 22`, `DEC`) does not parse under `_ris_date_parts`
(no leading digit) and so is silently ignored rather than spliced — that splicing is T026 (US-3),
not built here.

Next: T014 (identifiers — DO/UR, SN resolved by shape then reference type).

### T014 — identifiers: DO/UR, SN resolved by shape then reference type

Did: `_identifiers`, mapping `DO` through the shared `IdentifierNormalizer.normalize_doi` (the
same resolver-URL/`doi:`-label recovery `bibtex.py` already uses) to `DOI`, `UR` verbatim to
`URL`, and `SN` resolved by `_sn_identifier`: shape first (`validate_issn`/`validate_isbn`, the
same validators `ItemIdentifier.save()` uses), reference type second — on `RPRT`/`PAT` it is a
report or patent number and goes to the scalar `number` field, never an identifier row
(research.md R6). An `SN` that validates as neither shape and isn't on a report-like type is left
unconsumed for now — its preservation under `custom["ris"]` is US-4 (T030), not built here.

Verified: `poetry run pytest tests/test_importers/test_ris.py::TestIdentifiers -v` — 8 passed.
Confirmed RED first: all 7 identifier assertions failed with `KeyError` before `_identifiers`
existed. `poetry run pytest tests/test_importers/test_ris.py -q` — 169 passed. `poetry run mypy
literature/importers/ris.py` — clean. `poetry run pre-commit run --files
literature/importers/ris.py tests/test_importers/test_ris.py` — clean (one ruff-format pass,
no net diff).

Next: T015 (citation keys — ID verbatim, minted fallback, max_length guard).

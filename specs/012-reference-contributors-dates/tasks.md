# Tasks — FS-012 Manage a Reference's Contributors, Dates and Identifiers

**Branch**: `012-reference-contributors-dates` · **Plan**: [`plan.md`](plan.md) · **Research**: [`research.md`](research.md)

Every task is test-first per Article I. Where a task closes a defect that no test covers, its first
step is to reinstate the defect as a failing assertion — a gate that has never failed is not a gate.

`[P]` marks tasks that may run in parallel with the others in the same group.

## Phase 0 — Foundational

Blocks every story. Sequential.

- **T001** — Raise the `django-mvp` floor from `>=0.19.1` to `>=0.19.3` in `pyproject.toml`, with a
  comment saying what the version buys (the inline formset machinery and its tabular layout).
  Relock and install. Confirm `mvp.views.InlineFormSet`, `MVPInlineCreateView` and
  `MVPInlineUpdateView` import, and that `cotton/form/formset/index.html` accepts `layout="tabular"`.
  *Done ahead of the task graph while measuring the library; recorded here so the ledger is honest.*

- **T002** — `ItemDate` enforces its own span rule. Test first: assert that a date with an `end` and
  no `begin` is rejected, and that an `end` earlier than its `begin` is rejected — both currently
  pass and both must fail before the fix. Then add `clean()` and `save()` following the
  `ItemIdentifier` precedent in the same module. **Do not compare `PartialDate` objects with the
  ordering operators** — research R5 measured them as non-total across precisions, and neither
  `PartialDate("2020") > PartialDate("2019-05")` nor its reverse is true. Compare the underlying
  dates, allowing for the library's no-op precision truncation. Messages are `gettext_lazy`-wrapped.
  No migration: this is Python-level validation, not a database constraint (FR-016, FR-039).

- **T003** — `TYPE_DATE_SLOTS` in `literature/ui/fieldgroups.py`, beside `TYPE_GROUPS` and never
  inside `GROUPS` (research R6 measured why: `GROUPS` is flattened into `ItemForm.Meta.fields`, and a
  name that is not an `Item` column raises `FieldError` at class-definition time). `issued` is
  always-on; each of the 45 item types names the slots that additionally lead for it. **Every entry
  carries a comment naming the criterion that decided it**, per ADR-0020, and the evidence is CSL's
  own appendices — not any unlicensed schema. Tests mirror the existing field-group tests: every
  `ItemType` value is a key, every named slot is a real `DateType`, and the existing
  `GROUPS`-equals-scalar-fields assertion still passes untouched (FR-013).

- **T004** — `literature/ui/inlines.py` with `ContributorInline`, `DateInline` and
  `IdentifierInline`. Declarations only at this stage — model, fields, extra, `can_delete` — with the
  forms arriving in their own stories. Assert the three resolve to distinct prefixes so the
  library's duplicate-prefix guard cannot fire (D-2).

- **T005** — The create and update views compose django-mvp's inline mixin and declare all three
  sets. `item_form.html` overrides the formset block and renders each set with `layout="tabular"`,
  since the library's own form template passes no layout and there is no view-level equivalent
  (research R2). The existing type-scoped scalar groups are untouched. Assert the page renders all
  three sets, that a save covering the reference and its rows commits as one transaction, and that
  an invalid submission re-renders every set with its own errors and its entered values intact
  (FR-031, FR-032, FR-033).

## Phase 1 — US-1 Credit the people behind a reference (P1)

Depends on Phase 0.

- **T006** — `NameForm` fields on the contributor row form. Family and given are the row's own
  columns; the particles, the suffix and the unparsed organizational form are reachable through a
  disclosure rather than five more columns (FR-009, FR-008). The three citation-processor flags are
  never declared, so `ModelForm` cannot write them (FR-010). Test that a contributor with only an
  unparsed name saves, and that a contributor with neither a family name nor an unparsed name is
  rejected with a message rather than stored (FR-011).

- **T007** — The row form over `ItemName` creates or updates the `Name` it points at in its own
  `save()`, and **never reuses a stored record** (FR-006, D-3). Test that entering a name matching
  one already stored creates a second record, that the stored one is unchanged, and that everything
  it was credited on it is still credited on (SC-002). Test that the same name entered twice in one
  role stores two records with no warning (FR-007).

- **T008** — The `<datalist>` of stored names, rendered once per page from the distinct names in the
  catalogue and referenced by every contributor row through `list=` (D-1, D-12). It lives in its own
  template so the formset's `__prefix__` cloning never rewrites it. Test that the suggestions are
  present, that accepting one posts text and nothing identifying, and that a name absent from the
  list is accepted exactly as one present in it is (FR-005, FR-006).

- **T009** — Ordering within a role. The row carries a position column through Django's own formset
  ordering, reached by the declaration's escape hatch (D-4, D-13). `ItemName.order` is
  `editable=False`, which excludes it from a generated form and places no restriction on what the
  view writes, so the form assigns it in `save()` and positions are renumbered per `(item, role)` so
  that 1, 1, 3 becomes a coherent sequence rather than a rejection. Test that reordering one role
  leaves every other role's order untouched, and that no ordering across roles is offered (FR-004).

- **T010** — Removing a contributor from a reference removes the link and never the `Name` (FR-003).
  Test that the record survives, that it survives even when credited on nothing else, and that its
  own page still renders while listing nothing.

- **T011** — Test that a save rejected anywhere on the form leaves no `Name` record behind from the
  attempt, and returns the form carrying what was entered (FR-033, D10). This is the failure a naive
  implementation produces — records created while processing the form and orphaned when validation
  fails elsewhere — so it is asserted directly rather than assumed from the transaction.

- **T012** — `docs/` covers crediting contributors: how a name is entered, that completion is a
  spelling aid which never links to a stored record, why duplicates therefore accumulate, and where
  joining them is tracked. Reachable from the documentation's table of contents.

## Phase 2 — US-2 Give a reference its dates (P2)

Depends on Phase 0. Independent of Phase 1.

- **T013** — `ItemDateForm` declaring `begin` and `end` and nothing else, so the parts the form does
  not offer are never written (FR-017, D-6). Research R5 established that a plain text input over
  `PartialDateField` already accepts a year, a year and month, or a full date with no precision
  declared, so this task asserts that behaviour through a form rather than building it: test each
  precision round-trips, and that a stored value renders back as the string that re-parses to it
  (FR-014).

- **T014** — A span is two ends, each keeping its own precision (FR-015). Test a year-to-year span, a
  mixed-precision span, and that the rejections from T002 surface as form errors rather than
  exceptions (FR-016).

- **T015** — Which slots the set renders: those `TYPE_DATE_SLOTS` leads with for the reference's
  type, **plus every slot the reference already holds a value in, whatever the mapping says**
  (FR-012, FR-018, D-6). Test that changing item type never drops a stored date, and that a slot
  outside the type's set but holding a value is rendered rather than merely reachable.

- **T016** — A stored date whose only content is unparsed shows that content, so an imported date the
  catalogue could not read can be repaired instead of being invisible (FR-018, D4). Test with a date
  carrying only a literal or raw value: it is visible, and replacing it with a readable date stores
  the readable date while leaving the rest of the record alone.

- **T017** — Clearing a date removes the reference's date in that slot, through the formset's
  explicit deletion rather than by the row's absence (FR-019, D-6). Test that a cleared slot is gone
  and that no other slot moved.

- **T018** — The date set validates `(item, date_type)` across its own rows in `clean()` and reports
  a collision against the offending row, before the database constraint can fire inside the
  transaction (D-8). Test the message names the slot.

- **T019** — `docs/` covers dating a reference: the precisions accepted, spans, which slots lead for
  which kind of reference, and that the mapping decides what is offered and never what can be
  stored.

## Phase 3 — US-3 Give a reference its identifiers (P3)

Depends on Phase 0. Independent of Phases 1 and 2.

- **T020** — The ISBN distinction, in `literature/validators.py`. Test first, and test both
  directions: the existing parametrised accepted and rejected value lists must pass untouched — they
  are the proof that acceptance is unchanged (FR-029, SC-005) — and the two values already commented
  as bad-check-digit cases must now produce a different message and a different code from a
  wrong-shape value. `_isbn10_valid` and `_isbn13_valid` each already begin with a standalone shape
  regex and only then compute the checksum, so this recovers a distinction the code discards one line
  before the raise rather than adding a rule (D-7, research R7). New code is
  `invalid_isbn_checksum`, so a caller can branch without matching on prose. **ISSN is not touched**
  — see the specification's refinement note and #118.

- **T021** — Assert the two consumers that use these validators as raise-or-not discriminators are
  unaffected: the BibTeX identifier branch and the RIS `SN` router. The existing RIS routing tests
  are the guard and must pass untouched (research R7).

- **T022** — `ItemIdentifierForm`: the six known kinds offered, another nameable, and a nameable kind
  matching a known one other than by casing cleaned to the canonical acronym before it reaches the
  model (FR-023, FR-024, FR-025, D-9). The normalization is in the form, not the dispatch dict —
  changing the dispatch would alter what the import path validates, which is outside this feature and
  is behaviour FR-029 protects. Test that `isbn` is checked as ISBN, and that a genuinely unknown
  kind is stored exactly as given and unchecked.

- **T023** — The identifier set validates its own rows for a repeated kind in `clean()` and reports
  it against the offending row with a message naming the limit, before the database constraint fires
  (FR-030, D-8). Test the message says the reference already holds one of that kind.

- **T024** — Adding and removing identifiers through the set (FR-021, FR-022), and that a rejected
  identifier's message reaches the person on the form (FR-026).

- **T025** — Regenerate `literature/locale/en/LC_MESSAGES/django.po` with
  `django-admin makemessages -l en`. Research R7 found no Makefile, no CI step and no pre-commit hook
  touching the catalogue, so nothing will remind anyone — hence a task. Confirm the new strings are
  present and the stale line references are corrected (FR-041, Article VIII).

- **T026** — `docs/` covers identifiers: the kinds known, that another can be named and is stored
  unchecked, one per kind per reference, and what a rejection tells you. Update the data-model page's
  validation table, which currently describes ISSN as shape-only and stays correct.

## Phase 4 — US-4 The demo shows the flows, and a broken one is caught (P4)

Depends on Phases 1, 2 and 3.

- **T027** — The demo's seeded catalogue reaches the three flows by following links from the pages it
  already serves, with no sign-in anywhere on the documented path (FR-042, FR-044).

- **T028** — The guard walks each flow against the demo and asserts the catalogue changed as the flow
  claims (FR-043). Following the package's own rule, a guard asserts on content rather than on a
  status code (ADR-0018).

- **T029** — Break each flow in turn and confirm the guard fails and names it (SC-008). This is the
  task that proves the guard is a guard.

- **T030** — `docs/` gains the demo's coverage of these flows, and the feature's documentation is
  reachable from the table of contents.

## Cross-cutting, at convergence

- Squash any migrations the branch introduced. It should introduce none (FR-039); if
  `makemigrations --check` reports one, that is a finding rather than a file to squash.
- ADR graduation. Two decisions look likely to qualify: D1/D12, which governs the write side of the
  whole front end rather than this feature, and D14, which amends how ADR-0021's guarantee is upheld
  once the write path includes related rows. Each decision records its verdict either way.
- Raise the reordering affordance with django-mvp as an upstream request (D-13).
- Humanize every public markdown the run authored or rewrote, and confirm no internal vocabulary
  reached a landed file.

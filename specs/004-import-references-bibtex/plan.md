# Implementation Plan: Import References from BibTeX Files

**Branch**: `004-import-references-bibtex` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-import-references-bibtex/spec.md`

## Summary

Add `literature.importers.bibtex`, a single `BibFormat` subclass that reads both classic BibTeX and
BibLaTeX. It supplies the two stages a format owns, `parse` and `to_csl_json`, plus `handle_for`,
and touches nothing else. Everything the contract already delivers, atomicity, per-entry reporting,
ordering, dry runs and the configured-format lookup, applies as-is.

The technical core is a mapping problem wrapped in a cleaning problem. `bibtexparser` turns the file
into entries with macros expanded and cross-references resolved. A mapping table turns an entry type
and its fields into CSL JSON. A cleaning layer sits between the two and is where most of the value
is: it strips resolver prefixes off DOIs, decodes LaTeX-escaped text, and routes anything it cannot
make sense of into preservation rather than letting it fail the record.

Nothing here changes the data model. No new fields, no migration.

## Technical Context

**Language/Version**: Python 3.12–3.13 (package floor 3.11), per `pyproject.toml`

**Primary Dependencies**: Django 5.2 and 6.0. **Two new runtime dependencies**: `bibtexparser>=1.4.4,<2`
and its declared `pyparsing>=2.0.3`. Justified in [research.md](research.md) under Article VII. No
separate LaTeX decoder is needed, since `bibtexparser.latexenc` covers it.

**Storage**: Django ORM. No new models, no migration.

**Testing**: pytest + pytest-django. Test modules mirror the `literature/` tree, per the workspace
testing standard. Acceptance rests on the committed corpus the specification describes.

**Target Platform**: Any Django project installing this package.

**Project Type**: Library (installable Django app).

**Performance Goals**: None stated, deliberately, as for the import contract. The roadmap's concern
is correct handling of messy files, and any throughput number set here would be invented.

**Constraints**: Article V, file content is untrusted and decoding LaTeX must not evaluate it.
Article VIII, every human-readable string is translatable.

**Scale/Scope**: One new module and its tests, plus a documented mapping table and four glossary
entries.

## Constitution Check

| Article | Bearing on this feature | Status |
|---|---|---|
| I — Test-First | Each story's tests are written and failing before its implementation. The corpus is a test artifact and lands with the tests that read it. | Planned |
| II — Simplicity | One class, two mapping tables, one cleaning layer. No new abstraction over the contract. | Pass |
| III — Anti-Abstraction | No base class is introduced. `BibFormat` already exists and this is its first real subclass, which is what #21 was verified against. | Pass |
| V — Security & data-safety | FR-029. LaTeX decoding is table substitution, never evaluation. No file, network, or subprocess access from file content. | Planned |
| VI — Documentation | FR-007 mapping table published in `docs/`; FR-030 adds four glossary entries to `CONTEXT.md`. | Planned |
| VII — Dependency discipline | Two new runtime dependencies with stated justification in `research.md`; `deptry` must stay green, which means declaring `pyparsing` explicitly rather than relying on it transitively. | Decision recorded |
| VIII — i18n | Every failure reason and label wrapped for translation; the `makemessages` gate runs in CI. | Planned |
| IX — CSL JSON as lingua franca | The whole feature converts *into* CSL JSON and reuses `from_csl_json` untouched. Unknown entry types map to `document` rather than inventing a type. | Pass |
| X — Embeddable | The format is exported from the `literature` namespace and added to the shipped defaults so no configuration is required. | Planned |
| XI — Data integrity | Atomicity is the contract's, unchanged. Recovery happens before the catalogue is asked to store anything, so nothing invalid reaches it. | Pass |

No violation requiring justification.

## Proposed specification refinement

**This needs a ruling before implementation starts, because it changes two approved requirements.**

FR-004 as approved requires that what an import holds be bounded by a file's macros and
cross-reference parents rather than by its entry count, and FR-005 requires the source to be
readable twice, which I flagged at the spec gate as the change most likely to be vetoed.

`bibtexparser` reads a file into a database in a single pass, expanding `@string` macros and
resolving `crossref` inheritance as part of that load. Two consequences follow.

**FR-005 becomes unnecessary.** There is no second pass, so nothing is asked of the caller that the
contract did not already ask. The constraint I flagged disappears rather than being worked around.

**FR-004 is stricter than the contract it inherits from.** The contract's FR-024 requires that an
import "consume a format's entries one at a time rather than requiring the whole file's
**converted** content to be materialised before any entry is stored". My FR-004 tightened that from
converted content to all content, which is not what #21 settled.

**Recommendation: restore FR-004 to the contract's scope and drop FR-005.** Converted content is
where the real cost lives, an `Item` with its contributors, dates and identifiers per entry, and
streaming that is preserved either way, since entries are converted and stored one at a time. Parsed
source text is proportional to a `.bib` file, which is small, bounded, and something the caller
already had in hand.

The alternative, if you would rather keep FR-004 as written, is to write an entry-level splitter over
the raw text and drive the parser per entry, with our own macro and cross-reference pre-pass. It
keeps the stricter memory guarantee, keeps FR-005 and its caller-facing constraint, and adds bespoke
parsing of exactly the kind `research.md` argues against. I do not recommend it, but it is a real
option and the choice is yours.

Applying the refinement means the amendment ritual: `refine.update`, `refine.diff`,
`refine.propagate`, re-sync of the issue graph, then implementation. Nothing is edited until you
rule.

## Design in brief

**One class, `BibTeXFormat`, in `literature/importers/bibtex.py`.**

`parse(file)` loads the source through `bibtexparser` with `interpolate_strings`, `common_strings`
and `add_missing_from_crossref` on, then yields each entry in source order. Comments and preambles
are collected by the library into separate lists rather than as entries, so `parse` yields them
explicitly, tagged, and `to_csl_json` raises `SkipEntry` for them. Without that they would not appear
in the report at all, which FR-014 forbids.

`to_csl_json(raw)` is the mapping, in a fixed order:

1. **Clean.** Decode LaTeX through `latexenc.latex_to_unicode`, drop capitalization-protecting
   braces, then normalize per field: strip resolver prefixes off a DOI, tidy an ISBN.
2. **Type.** Look up the entry type in one table covering both dialects, falling back to `document`.
3. **Fields.** Map through a second table, again covering both dialects, with a documented precedence
   where the two disagree, such as BibLaTeX `date` over classic `year` and `month`.
4. **Names.** Split contributor lists with `customization.splitname`, which yields First/von/Last/Jr
   and maps cleanly onto the `Name` model's given, particles, family and suffix. A brace-wrapped
   institutional name goes to `literal` unsplit.
5. **Dates.** Build CSL date parts at the precision stated. Anything that will not resolve goes to
   the existing `raw` and `literal` fallbacks rather than being dropped.
6. **Identifiers.** Known types become top-level CSL identifier fields. A value that survives cleaning
   but is still not a valid identifier of its type goes to preservation instead of failing the entry.
7. **Preserve.** Every source field that mapped nowhere is collected into CSL `custom`, which is what
   `Item.custom` stores, including an unresolvable `crossref`.

`handle_for(raw)` returns the cite key, which is also the citation key, so a failure report names the
thing a researcher will search for.

**The mapping tables are data, not code.** Two module-level dicts, one for entry types and one for
fields, each annotated with the dialect a key comes from. That is what lets the published mapping
(FR-007) be generated from the source of truth rather than maintained beside it and left to drift.

**It all lives in one module.** Tables at the top, cleaning helpers next, the class below. The
estimate is 400 to 500 lines, which sits between `importers/base.py` at 282 and `converters.py` at
542, so it is unremarkable for this package. An earlier draft of this plan split the tables and the
cleaning helpers into separate private modules, which was structure argued from a prediction about
size rather than from a measurement, and Article III bars precisely that. If the tables turn out
substantially larger than estimated once both dialects are in, lifting them into their own module is
a mechanical move available at the time, and it should be made then rather than assumed now.

**Where the parser is allowed to appear.** `bibtexparser` is imported by
`literature/importers/bibtex.py` and by nothing else. A test asserts it, so the reversibility
`research.md` relies on is a checked property rather than an intention.

## Source layout

```text
literature/
└── importers/
    └── bibtex.py          # tables (both dialects), cleaning helpers, BibTeXFormat
docs/
└── bibtex-mapping.md      # FR-007, generated from the tables
tests/
├── test_importers/
│   └── test_bibtex.py     # concerns grouped into classes, one module per source module
└── fixtures/bibtex/       # the committed corpus
```

One source module means one test module. The constitution states it plainly, that test modules
mirror the `literature/` tree with `test_` prefixes, and the existing `test_base.py`,
`test_config.py` and `test_results.py` each pair with a source module. Concerns are separated by
test class, not by file.

## Phases

**Foundational, sequential, before any story.** Dependencies added and locked, `deptry` green,
`BibTeXFormat` skeleton registered in the shipped defaults so the contract's lookup finds it, and the
corpus scaffolding in place. Nothing here is user-visible on its own, and every story sits on it.

**Then one phase per story, in priority order.** US-1 is the mapping and is the bulk of the work.
US-2 is the cleaning layer. US-3 extends the two tables to BibLaTeX and adds date precedence. US-4 is
preservation, which is small because the cleaning layer already routes to it. Each is independently
testable against the corpus, which is what makes them dispatchable one at a time.

**Cross-cutting, at convergence.** The published mapping table, the four glossary entries, and an
i18n pass over every string the feature emits.

## Risks

- **The mapping tables are where quiet errors live.** A wrong entry-type mapping produces a record
  that looks fine and is wrong, which is the failure mode this whole feature was written to avoid.
  Mitigated by driving the published table from the same dicts the code uses, so a reviewer reads
  what actually runs.
- **BibLaTeX could prove larger than it looks.** If extending the tables turns into its own body of
  work, splitting US-3 into a separate feature is better than letting it distort this one. Flagged at
  the spec gate and still the plan.
- **`bibtexparser` v1 is in maintenance.** Accepted knowingly, and contained by keeping the import to
  one module and asserting it in a test.
- **The corpus needs real exports.** Two files have to be sourced from a reference manager and
  stripped of anything personal before they can be committed. This is the one task with a dependency
  outside the repository.

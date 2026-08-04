# Research: Import References from BibTeX Files

Phase 0. The only open technical question this feature carries is what parses BibTeX, which
Article VII makes a decision requiring stated justification rather than a default. The import
contract deliberately left it here: `specs/003-import-contract/plan.md` records "parsing libraries
arrive with the formats that need them (#22, #23), not here."

The package currently has two runtime dependencies, `django` and `django-partial-date`. Onboarding
dropped `python-dateutil` and `citeproc-py` as unused. That is the bar anything new has to clear.

## Why not hand-write the parser

Tempting, since it adds nothing to the dependency list, and rejected.

BibTeX's grammar is worse than it looks. Values can be brace-delimited, quote-delimited, or bare;
braces nest and protect their contents from almost every other rule; values concatenate with `#`;
`@string` defines macros that later entries reference; anything outside an entry is a comment, and
`@comment` blocks have their own shape. Name lists have three distinct forms with particles and
suffixes. The specification then asks this parser to stay upright on files that have been
hand-edited for years.

Article II favours simplicity, but simplicity is a property of the result, not of the dependency
count. A bespoke parser for a messy legacy format is where the bugs would live, and every one of
them would surface as a researcher's reference going missing. This is the wrong place to save a
dependency.

## Candidates

**`bibtexparser` 1.4.4** (2026-01-29, dual LGPLv3/BSD, so the BSD arm is compatible with this
package's MIT licence). Declares `pyparsing>=2.0.3` in `setup.py`, which the PyPI metadata does not
surface, so adopting it costs two runtime dependencies rather than one. Parses with brace awareness,
expands `@string` macros through `interpolate_strings`, ships common month abbreviations through
`common_strings`, and resolves `crossref` inheritance through `add_missing_from_crossref`. It also
carries two things worth more than the parser itself: `customization.splitname`, which breaks a name
into First/von/Last/Jr, and `latexenc.latex_to_unicode`.

**`bibtexparser` 2.0.0b9** (2026-01-29, no runtime dependencies). Architecturally the better fit. Its
middleware layers model exactly what this feature calls recovery, and its `Library` separates parsed
blocks from failed ones, which lines up with per-entry failure reporting. It has also been in beta
since August 2023, nine betas over three years, with no stable release. This package is published to
PyPI, so a beta dependency is not a risk taken locally, it is one propagated to everyone who
installs downstream, along with whatever API changes arrive before 2.0 final.

**`pybtex` 0.26.1** (2026-04-03). Mature and well tested, but it is a bibliography *processor* whose
API is oriented toward formatting rather than extraction, and it pulls `latexcodec` and `pyyaml`,
making three new runtime dependencies. PyYAML in particular is a large thing to inherit for a
feature that reads `.bib` files.

**`pylatexenc` 2.11** (2026-07-25, MIT, no dependencies) was considered for LaTeX decoding, and is
not needed. `bibtexparser.latexenc.latex_to_unicode` covers the same ground, so decoding costs no
additional dependency.

## Decision

**`bibtexparser` 1.4.4, declared alone. It brings `pyparsing` as its own requirement, so the install
footprint is two packages and the `pyproject.toml` declaration is one line. No separate LaTeX
decoder.**

`pyparsing` is deliberately *not* declared by this package. We never import it, so declaring it
would register with `deptry` as a defined-but-unused dependency, which is what happened on the first
attempt at this task.

Stability decides it. Publishing a package whose install pulls a three-year-old beta puts that risk
onto every downstream project, and 2.0's API is not fixed. The v1 line is in maintenance rather than
active development, which is a real cost, but it is the smaller of the two: v1 is stable and
finished, where v2 is neither.

Three things make the choice cheap to reverse, which is what makes it acceptable at all:

- The parser sits behind `BibTeXFormat` and nothing else in the package imports it. That is precisely
  what the seam in #21 was drawn for, and moving to v2 later would touch one class.
- `splitname` and `latex_to_unicode` are the parts hardest to replace, and both are self-contained
  functions rather than architecture. If the parser is ever swapped, they can be vendored or replaced
  independently.
- `pyparsing` is pure Python, ubiquitous, and carries no dependencies of its own.

## What the library does not do

Three requirements land on our side of the line, and each is small:

- **DOI normalization (FR-017).** `customization.doi` builds a resolver link *from* a DOI. It does
  not do the reverse, which is what a real export needs. Stripping a `https://doi.org/` or `doi:`
  prefix is ours to write.
- **Reporting comments and preambles as skipped (FR-014).** The library collects `@comment` and
  `@preamble` into separate lists on the database rather than yielding them as entries, so they would
  simply vanish from the report. Since we own `parse()`, they can be yielded explicitly so
  `to_csl_json` can raise `SkipEntry` for each.
- **Dialect unification (FR-022, FR-023).** The library parses BibLaTeX syntax without complaint,
  because the two dialects share a file syntax. Knowing that `journaltitle` and `journal` mean the
  same thing, and that a BibLaTeX `date` supersedes a classic `year`/`month` pair, is mapping-table
  work that belongs to us either way.

## Consequence for FR-004 and FR-005

`bibtexparser` reads a file into a `BibDatabase` in one pass, expanding macros and resolving
cross-references as part of that load. This is worth putting in front of the maintainer, because it
makes two requirements in the approved specification unnecessary rather than merely satisfiable a
different way. See `plan.md`, *Proposed specification refinement*.

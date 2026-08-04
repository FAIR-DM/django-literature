# Decisions: Import References from BibTeX Files

Rationale too long to sit inline in `spec.md`, plus every point resolved without escalation.
Maintainer decisions are marked as such. Everything else was resolved from the intake discussion
and the governing documents, and is open to veto at the spec gate.

---

## D1 — Recovery is the format's job

**Maintainer decision.**

The import contract makes an entry atomic, and Article IX forbids storing an invalid known-type
identifier. Put together, a record carrying `doi = {https://doi.org/10.1234/abc}` fails outright
and stores nothing, even where every other field in it is sound. Publisher and database exports
write DOIs that way constantly, so the rule protecting data integrity was also the rule that would
cost a researcher a large part of their library on first contact with the package.

Resolved by cleaning an entry before the catalogue ever sees it. A value whose intended meaning can
be recovered is normalized on the way in, a value that cannot be recovered is preserved instead of
discarded, and an entry is refused only when nothing is left to build a record from. The maintainer
put it plainly: cleaning belongs to the format subclass, and rejection is a last resort.

What makes this consistent with both rules rather than an exception to either: the catalogue still
refuses invalid identifiers, because by the time it is asked there are none left to refuse.
Atomicity is untouched, because recovery happens before the entry is built rather than by relaxing
what a built entry may contain.

One consequence is worth stating plainly, because it looks like a defect from the outside. Failure
becomes rare for BibTeX. That is the intent. It is also why the preservation rule in D3 carries more
weight than it first appears: without it, "this entry did not fail" would be indistinguishable from
"this entry was quietly emptied".

## D2 — One format reads both dialects

**Maintainer decision.**

"BibTeX" names two things. Classic BibTeX is what publisher export links and Google Scholar emit.
BibLaTeX is what current Zotero and JabRef emit by default, sharing the file syntax but disagreeing
on field names and entry types. The issue did not distinguish them, and no sibling issue covers
BibLaTeX, so it was either inside this feature or nowhere.

Resolved as one format under one name, reading both. What decided it was the failure mode of the
alternative. A BibLaTeX file read by a classic-only reader does not error. It yields entries with no
container title and no date, reports every one of them as created, and leaves the researcher to find
the damage months later. Refusing the file outright would be better than that. Reading it properly
is better than either, and the cost is a larger field and type mapping, which is a table rather than
a design problem.

Two registered formats, `bibtex` and `biblatex`, was considered and rejected. It hands the
researcher a question they have no way to answer, since reference managers do not announce which
dialect they wrote, and the whole point of the feature is that an existing library imports in one
step.

## D3 — Preservation without reporting

**Maintainer decision.**

The issue asks that nothing be "dropped in silence", which can mean not discarded or can mean
actively reported. The two readings cost very different amounts: the second needs new vocabulary in
an import contract that shipped days earlier.

Resolved as not discarded. Unmapped fields are preserved on the record and per-entry reporting is
left exactly as the contract defines it. The roadmap deliverable already said as much, asking that
unresolved source fields be "preserved through the model's fallback slots rather than discarded",
and CSL defines `custom` for this purpose. A per-field reporting channel would mean reopening a
settled contract on behalf of a need nobody has stated. Nothing is foreclosed by waiting, either: if
that need does appear, the preserved data is already on the record to build the report from.

## D4 — `crossref` inheritance, and what it costs streaming

Not raised at intake. The clarification scan found that the spec required both one-at-a-time
consumption and `crossref` inheritance, and that classic BibTeX requires a cross-referenced entry to
appear *after* every entry referencing it. A forward reference is therefore the normal case, and
converting strictly in one forward pass cannot resolve inheritance at all. Two requirements in the
same document contradicted each other.

Resolved by keeping inheritance in scope for parents in the same file, and having the format
establish a file's `@string` macros and cross-reference targets before it converts anything. An
unresolvable `crossref` is preserved as an ordinary unmapped field, since there is nothing to
resolve it against.

The requirement that actually mattered was never "read the file exactly once". It was that memory
must not grow with the size of the file, which is close to how the contract's own clarification
worded it. Bounding what is held to a file's macros and cross-reference parents keeps that promise,
because neither scales with entry count. Reporting order is unaffected, since entries are still
converted in the order they occur.

The cost was that the source must be readable more than once. **Superseded at the plan gate,
2026-08-04**: the parsing library expands macros and resolves cross-references inside one load, so
there is no second pass and the cost never materialised. FR-005 was removed and FR-004 restored to
the import contract's scope. What survives of this decision is that inheritance is in scope and that
an unresolvable `crossref` is preserved rather than failed.

Holding entries with unresolved cross-references until their parent turns up was considered and
rejected. It preserves single-pass reading but breaks source-order reporting, because everything
after a pending entry has to queue behind it, and a file whose first entry carries a `crossref`
would buffer in its entirety.

## D5 — Who actually calls this

The stories were drafted around a researcher running an import, while the feature ships no
interface and the front end is roadmap item R6.

Resolved by naming the caller as a developer, or an administrator acting for the researcher, which
is what the import contract's own stories say throughout. The researcher stays in the stories as the
person the feature is for and whose library decides whether it succeeded. Conflating the two would
have made the acceptance scenarios read as though an interface were in scope.

## D6 — Acceptance rests on a committed corpus

A criterion reading "no entry is refused for a reason normalization resolves" cannot be measured
against an unnamed body of files, and the roadmap asks for tests over representative real-world
files without saying where those come from.

Resolved as a corpus committed to the repository: constructed fixtures isolating one malformation
each, a genuine export per dialect from a mainstream reference manager, and one file large enough
that a whole-file conversion would be visible.

Neither kind of file is sufficient alone. Constructed fixtures only ever test the malformations
somebody thought of, which is the weakness that makes real exports worth having. Real exports on
their own make a failure hard to localise. Together they give a reproducible corpus that needs no
network, where a failure points at the rule it broke. Bibliographic metadata is factual, and
stripping anything personal out of an export leaves nothing raising a licensing or privacy question.

## D7 — The synonym this feature would otherwise start

The requirement to add vocabulary to `CONTEXT.md` did not name the terms, where the import
contract's equivalent did.

Resolved as entry type, field, dialect, and cite key. Cite key is the one that matters. BibTeX calls
it a cite key, the model calls it a citation key, and they are the same value under two names.
Leaving that unpinned is exactly how a synonym starts circulating, which is what the glossary's
*Synonyms to avoid* convention exists to prevent.

## D8 — The contract's `label` annotation forbade the translation Article VIII requires

Found during the foundational phase, by mypy, the first time a real format tried to translate its own
label. `BibFormat` declared `label: ClassVar[str]`, so `gettext_lazy` was a type error, and
`gettext_lazy` is what Article VIII makes non-negotiable for human-readable strings. The package
already had the convention in hand: `Outcome` labels are lazy, and `test_results.py` asserts they are
`Promise` instances.

Widened to `ClassVar[str | Promise]` in `literature/importers/base.py`. A type annotation only.
Nothing about the contract's behaviour changes, so FR-002 holds, and no test of the contract changed.

Worth naming because it is the shape of defect a first concrete implementation exists to find. The
contract shipped verified against a test-only format whose label was a plain literal, so nothing
exercised the annotation until a format that respects Article VIII arrived.

## D9 — One half of the real corpus is not genuine

The specification asks for a genuine export per dialect. The classic BibTeX half is genuine:
`real_crossref_classic.bib` came from Crossref by content negotiation, and it earned its place
immediately by carrying quirks nobody would have constructed, uppercase `ISSN` and `DOI` field names,
bare `month=July` macros, `&amp;` entities in titles, and real Unicode en-dashes in page ranges.

The BibLaTeX half is not. Producing a genuine Zotero or JabRef export needs the tool, which is not
available here, so `constructed_biblatex.bib` is written to follow those exporters' conventions and
is named to say so rather than claiming provenance it lacks. The fixtures README states it plainly.

Recorded rather than quietly accepted, because it is a real gap in the acceptance evidence: the whole
argument for real exports is that they carry what nobody thought to construct, and a constructed file
cannot do that by definition. Replacing it with a genuine export is worth doing whenever one can be
supplied.

## D10 — Two pre-existing tests modified, and why it is not a regression being papered over

`forge tamper-check` flags two files, and both flags are correct: `tests/test_importers/test_config.py`
and `tests/test_importers/test_smoke.py` were written before this feature and were changed by it. The
default reading of that signal is that an implementation broke a test and edited the test instead of
the code, so the justification belongs on the record rather than in a commit message alone.

Neither test failed because behaviour regressed. Both asserted, correctly at the time, that the
package ships no format of its own.

`test_an_unset_setting_yields_the_shipped_defaults` asserted `available_formats() == {}`. Its own
docstring said the package "ships no format of its own **yet**", and what it tests is the mechanism,
that an unset setting yields the shipped defaults rather than an error. The assertion now names
`bibtex`. The test is stronger than before, because there is finally a real default for it to check.

`test_all_lists_exactly_the_documented_surface` compares `__all__` against a hand-maintained map of
public names to modules, deliberately in both directions. Adding `BibTeXFormat` to `__all__` without
adding it to that map is exactly what the guard exists to catch, and it caught it. Updating the map
is the guard working, not the guard being silenced.

The distinction that matters: a test asserting *behaviour this feature changed* would be evidence
that the feature is wrong. These assert *inventory* the feature is supposed to change.

## D11 — Two things `bibtexparser` needed help with, found while implementing US1

Not raised at intake or planning; both surfaced empirically while writing `to_csl_json` against the
committed corpus.

**Bare full month names abort the whole file's parse.** `real_crossref_classic.bib` writes
`month=July` — a bare, unquoted macro reference, which is Crossref's own convention. `bibtexparser`'s
`common_strings` defines the three-letter abbreviations (`jan`…`dec`) as macros, so `month=May` and
`month=Oct` happen to resolve (they coincide with their own abbreviation), but `july` is not a
three-letter abbreviation and is therefore an undefined macro. With `interpolate_strings=True` this
raises `UndefinedString` while loading the file, which is not one entry failing — it is the entire
`bibtexparser.load()` call raising, which aborts parsing before a single entry is yielded. Resolved
by extending the parser's own macro table with the twelve full month names
(`literature/importers/bibtex.py:_MONTH_MACROS`) before loading. This is macro *resolution*, the same
thing `common_strings` already does for abbreviations — FR-013's territory — not a value cleanup: no
already-parsed field content is altered, and nothing here reaches into US2. The alternative,
disabling `interpolate_strings` and resolving macros field-by-field with a fallback, was rejected as
solving a one-line problem with an architecture-level change to how every field is read.

**A zero-field entry is not parsed as an entry at all.** `sparse_entry.bib` — `@misc{bare_minimum,}` —
is built to exercise spec.md's edge case: "An entry with no fields at all beyond its type and cite
key... Sparse is not invalid." `bibtexparser` 1.4.4's grammar requires at least one `field` inside an
entry (`field_list` is `pp.DelimitedList(field)`, which needs one or more matches), so a zero-field
entry fails to match the `entry` rule and falls through to `implicit_comment` instead — the whole
`@misc{bare_minimum,}` block is silently reclassified as a comment. It never reaches `parse()` as an
entry, so no cite key, no type, nothing for `to_csl_json` to map: the file imports as one skipped
element rather than one stored item.

This is a real gap between the corpus and the parsing library research.md chose, not a mapping defect
this story's tasks (T007–T020) can fix. Two ways to close it were considered and rejected for this
story: patching `bibtexparser`'s private pyparsing grammar (`BibtexExpression.entry`) to accept zero
fields, which reaches past a documented public API into implementation detail of a "maintenance
mode" dependency (research.md); or pre-scanning the raw source text for this shape before handing it
to the parser, which is exactly the hand-written parsing research.md rejected for the whole feature.
Recorded as a concern rather than worked around. `TestBlocks.test_a_zero_field_entry_is_swallowed_as_a_comment_by_the_parser`
asserts the actual (skipped, not created) behaviour, so a future fix has a red test to turn green
rather than a silent gap.

## D12 — Two US1 verification flags, triaged

Both raised by re-running the machine gates against the story's base rather than by reading the
Implementer's report, which is the point of re-running them.

**The tamper guardrail fired, and the change is legitimate.** `tests/test_importers/test_bibtex.py`
existed before this story (the skeleton commit created it with the registration and handle tests),
so every later edit to it trips the modified-pre-existing-test check by design. The diff is additive:
five test classes added, and the only pre-existing lines touched are two import statements that grew
to cover the names the new tests use. No assertion was weakened, no test removed, none skipped or
marked expected-to-fail. Approved rather than escalated, on the evidence of the diff.

Worth noting for later stories, since all four write to this one file and each will trip the same
flag: the guardrail cannot tell an addition from a weakening when both land in a file that already
existed, which is a consequence of the single-test-module layout the maintainer asked for at the
plan gate. The layout is still right — the constitution requires test modules to mirror the source
tree — so the answer is that each story's flag gets triaged on its diff, not that the flag is
switched off.

**The lint gate is red on a file no story task touched.** `tests/fixtures/bibtex/real_crossref_classic.bib`
was committed without a trailing newline in the foundational phase, which the repo's commit hooks
would have fixed had they run on it. `ruff` does not look at `.bib` files, so the Implementer's own
lint step was clean and the failure only appears under the full hook chain. Fixed in place. The
general lesson is the one the workspace already recorded about verify not matching CI: a story that
runs the linter directly rather than the repo's configured hook chain is checking less than the
pipeline will.

## D13 — Where a value US2 cannot rescue is allowed to land

US2 is required to preserve a value it cannot normalize into something the catalogue accepts
(FR-019), and US4 owns preservation of unmapped fields generally (FR-022, FR-023). The two meet at
the same slot, CSL `custom`, which raised the question of whether US2 may write there at all before
US4 exists.

It may, for the narrow case only. A cleaned value that still fails validation is written under its
own source field name in `custom`, one field at a time, at the point the failure is detected. What
US2 must not do is build the general sweep — walking every field of an entry and preserving whatever
had nowhere else to go — because that is US4's mechanism and duplicating it would leave two
implementations of the same rule to reconcile at convergence.

The alternative, making US2 fail such an entry and letting US4 rescue it later, was rejected. It
would land a state where a messy export refuses entries it is supposed to accept, and the story
would be reported complete with its own acceptance criterion unmet.

Unparseable dates are not this case. `ItemDate` already carries `literal` and `raw` for a date that
cannot be structured (FR-020), so those go to the model's own fallback rather than to `custom`.

## D14 — Decoding a name runs after the wrapped-literal check, not before

Found while implementing T023. `_is_wrapped_literal` decides whether a name is an unsplit
institutional literal (`{World Wide Web Consortium}`) by looking for exactly one surviving brace
pair once the parser has stripped the field's own outer delimiter. `latex_to_unicode` strips every
brace in a string as part of decoding it (that is what removes capitalization-protecting braces,
FR-018). Running decode first would remove the very braces the literal check depends on, so a
brace-wrapped institutional name would silently fall through to `splitname` instead and come out
split into given/family parts that do not exist.

Resolved by keeping the order fixed: check for the wrapped-literal shape on the raw name first,
then decode — either the literal's inner text, or the whole name before `splitname` runs on it.
Both paths decode eventually, so FR-018 holds for institutional names too; only the sequencing
matters. Worth recording because the two operations look independent (one about brace *meaning*,
the other about brace *removal*) until you notice they share the same character.

## D15 — ISBN normalization has no fixture, so it mirrors the DOI shape it was asked to match

T023 asks for "per-field normalization for DOI and ISBN", but FR-017 only names DOI by case, and
the committed corpus carries no malformed-ISBN fixture — every ISBN in the corpus already validates
once hyphens are stripped, which `validate_isbn` already does on its own.

Resolved by giving ISBN the same shape of normalization as DOI, a label strip
(`isbn:`, `isbn-10:`, `isbn-13:`, case-insensitive) ahead of validation, on the reasoning that a
label pasted in front of an otherwise-valid identifier is the one malformation shape FR-017
demonstrates and ISBN is exactly as likely to carry as DOI. It is speculative in the absence of a
concrete case: revisit if a real ISBN fixture (an existing export, or one built once a malformation
is observed) turns out to need something this does not cover.

The validation this normalization feeds is not reimplemented here. `_clean_identifier` produces a
value; whether that value earns its top-level CSL key or goes to `custom` (D13) is decided by
`literature.validators.validate_identifier`, the same function `ItemIdentifier.clean()` and
`.save()` call on every other write path. Reusing it rather than checking the DOI/ISBN shape
independently in `bibtex.py` is what keeps "valid" meaning one thing.

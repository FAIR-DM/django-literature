# Decisions — 005 Import References from RIS Files

Rationale that would not fit inline in `spec.md`, plus every ambiguity resolved without escalating.
Each decision names what was ambiguous, what was chosen, and why the choice is defensible.

## D1 — Every entry gets a citation key, and the format mints it

**Ambiguity**: The catalogue requires a citation key. `_resolve_citation_key` in `converters.py`
raises when a CSL JSON record supplies neither `citation-key` nor `id`. RIS has no cite key concept:
some producers write an `ID` tag, and Scopus and Web of Science exports typically do not. On the
existing conversion path, every entry in a database download would fail.

**Chosen**: The format supplies a key for every entry. An `ID` tag is taken verbatim. Otherwise the
key is minted from the entry's own bibliographic content, deterministically. An entry too sparse to
mint from falls back to its position in the file.

**Why defensible**: The alternative is refusing entries that carry no `ID`, which would fail most
real Scopus and Web of Science exports — the exact case issue #23 exists to serve. Minting is what
every established reference manager does when it ingests a keyless record. The cost is that the key
is the package's invention rather than the researcher's, which is stated in the specification rather
than hidden.

## D2 — No matching against stored items, and no de-duplication

**Ambiguity**: Minting a key from content invites the question of whether a matching key should be
treated as the same reference.

**Chosen**: No. Importing the same file twice produces two sets of items. Batch-scoped
de-duplication applies exactly as it does today and is a collision-resolution mechanism, not a
matching one.

**Why defensible**: Established tools do not match either — importing the same citation into JabRef
ten times yields ten entries. The package's purpose is a simple management interface that integrates
with Django, not reference-management magic nobody asked for. De-duplication, user-selectable key
styles, key regeneration, and import from URLs are all plausible later features, and none of them is
foreclosed by this decision.

## D3 — The reported handle is the stored key, not the minted one

**Ambiguity**: Minting must be deterministic, and batch de-duplication may suffix a colliding key
before it is stored. Both cannot describe one value, and the import contract's FR-009 does not say
which the handle is.

**Chosen**: Minting is deterministic on entry content and happens before de-duplication, so the same
entry always mints the same key. The result reports the key **as stored**, suffix included, and in a
dry run the key that would have been stored.

**Why defensible**: This diverges from the BibTeX format, whose FR-012 reports the cite key the
source wrote even where the stored key was suffixed. The reason the two differ is that a BibTeX cite
key is *in the file*, so a reader can search the file for what the report names. A minted key is in
no file. Its only use is finding the item in the catalogue afterwards, and reporting a value that
matches nothing in either the file or the catalogue would serve nobody.

## D4 — Position, not shape, separates header material from a malformed entry

**Ambiguity**: The draft skipped material before the first entry and failed a block of tags carrying
no reference type. A header written as tag-shaped lines satisfies both descriptions.

**Chosen**: Everything before the file's first reference-type tag is header material and is skipped,
whatever it looks like. After the first entry has been seen, a block of tags with no reference type
is a malformed entry and is failed.

**Why defensible**: The rule is mechanical and needs no inference about intent. It also matches how
a person reads the file: nothing is a bibliographic entry until the file has said "here is an entry
and this is its kind".

## D5 — The specification does not fix the minted key's shape

**Ambiguity**: "The author-year-title shape reference managers use" is not implementable as written,
yet SC-004 asserts only determinism.

**Chosen**: The feature owes three things — the key derives from the entry's own bibliographic
content, minting is deterministic, and the scheme is documented where a user can read it. The exact
shape is a plan-stage decision.

**Why defensible**: Fixing the shape here would pre-empt a later feature letting a user choose a
citation-key style, and a specification should not settle something no user has asked for. Nothing
downstream depends on the shape, because nothing matches on it (D2).

## D6 — The glossary's *entry* wins over RIS's own *record*

**Ambiguity**: RIS calls its unit a record, and the first draft of this specification used that word
throughout — 74 times. `CONTEXT.md` retires *record* on both sides of the import boundary: as a
synonym for an item, and as a synonym for a source-side entry.

**Chosen**: The specification says *entry*. RIS's own word is recorded once, where the file syntax
is described, and the glossary gains *record* as RIS's spelling of *entry*.

**Why defensible**: This is the same shape as *cite key* against *citation key* — one thing under
the source's name and under the package's — and Article VI requires the relationship be pinned
rather than left to circulate. It was the largest defect in the draft and the clarification scan is
what caught it, which is the argument for running the scan rather than clarifying while drafting.

## D7 — Producer support is named, and the package says what it does not promise

**Ambiguity**: RIS has no specified dialects. The 1980s Reference Manager specification is the only
written standard, and producers have diverged from it in undocumented ways, most sharply in the
contributor tags where `A2` means an editor in one export and something else in another. There is no
document to be correct against, so "reads RIS" is not an acceptance criterion.

**Chosen**: EndNote is the primary support target, with Web of Science and Scopus secondary.
Acceptance is judged against genuine exports from all three, committed to the repository. Tags
outside those producers' usage are read where the original specification defines them and preserved
where it does not. No producer detection, no configuration setting, one format name. The README
states the boundary: the package supports the common producers as best it can, promises no more, and
grows through bug reports and feature requests.

**Why defensible**: Sam's ruling, and it matches the evidence — moving a library between two
established, well-funded tools loses detail today. Targeting perfection against an ecosystem this
inconsistent would be an unkeepable promise. Naming the boundary is more honest than a claim of
general RIS support, and it makes acceptance testable.

## D8 — A genuine export is one the project did not write

**Ambiguity**: Acceptance rests on genuine exports, but EndNote is licensed software and both
databases need institutional subscriptions.

**Chosen**: Files the producers or third parties publish count as genuine, because what matters is
that the producer's own code wrote the file. Where no genuine file can be obtained for a producer,
its coverage rests on a fixture built from that producer's published tag documentation, and the
*Verification corpus* section records which producer that applies to.

**Why defensible**: It keeps the criterion honest in both directions. A constructed file is never
presented as a genuine export, so the corpus never overstates what has been proven, and the feature
is not blocked on a subscription the project may not hold.

## D9 — Single-value model limits are preserved, not widened

**Ambiguity**: An RIS entry can carry two serial numbers, a print and an electronic ISSN. The
catalogue allows one identifier per type per item, and one date per slot.

**Chosen**: The first value is stored and the remainder preserved on the item. The entry still
imports.

**Why defensible**: `CONTEXT.md` states plainly that widening either limit is a feature and not a
fix. Widening a shipped model constraint to accommodate a second format's convenience would be
exactly the quiet scope creep the import contract was drawn to prevent. Sam was shown this decision
at intake and did not object.

## D10 — The contract is inherited, and a defect in it is a finding rather than a fix

**Ambiguity**: R5 says the second format is what proves the seam was drawn in the right place. A
proof can come out either way, and the BibTeX specification's equivalent clarification said only
that the contract was not to be moved.

**Chosen**: This feature changes nothing in the contract's public surface. Where it cannot be
delivered without a change, that is raised as its own issue (FR-005) and recorded against SC-009.

**Why defensible**: It keeps the roadmap's claim falsifiable. A feature permitted to quietly widen
the contract it is meant to test would prove nothing, and one forbidden from reporting a genuine
defect would hide it. Separating the two — no silent change, and a visible finding — is what makes
the proof mean something.

---

# S3 decisions (research stage, 2026-08-05)

## D11 — The parser is hand-rolled, departing from the BibTeX format's precedent

**Ambiguity**: The BibTeX format depends on `bibtexparser`, which sets a precedent that a format
takes a parsing library. The obvious equivalent for RIS is `rispy`.

**Chosen**: Hand-roll the parser in `literature/importers/ris.py`. Add no runtime dependency.

**Why defensible**: `rispy` was installed and exercised rather than read about, and it fails four of
this feature's requirements outright — it silently drops the final entry when the closing `ER` is
missing (FR-006), silently discards material before the first entry (FR-008) and a tag block with no
reference type (FR-009), and discards repeated values by default (FR-018). It also returns zero
records for a file carrying a byte-order mark, which Scopus and Web of Science both emit, and its
`ParseError` is exported but never raised, so a file that is not RIS returns an empty list with no
error. None of that is configuration: its recovery strategy is to resynchronise silently, where this
feature's whole contract is to report what happened to every entry. Fixing it means replacing its
one parsing method, and preserving raw tags means discarding its tag table, which is the only asset
left. Against Article VII no justification for the dependency survives, and against Article III its
friendly field names would add a third naming layer between RIS tags and CSL variables. RIS is a
line-oriented format — a tag line, a continuation rule, and `ER`. Data is still lifted rather than
code: `rispy`'s tag and reference-type tables are MIT and serve as a census.

## D12 — FR-007 amended: continuation lines resolve per tag, not per file

**Ambiguity**: The approved FR-007 required an untagged line to be read as part of one value.
Genuine EndNote exports use that exact syntax to carry *additional* values — eight keywords under one
`KW`, two ISSNs under one `SN` — while Web of Science uses it for wrapped prose.

**Chosen**: The rule is per tag. Repeatable tags (the author tags, `KW`, `UR`, `SN`, `N1`) take an
untagged line as another value; scalar and prose tags (`AB`, `TI`, `T2`) join it with a space.

**Why defensible**: The original wording produced actively wrong data on the primary support target,
which is a fault rather than a preference. Indentation cannot be the discriminator — it is a Web of
Science habit and EndNote never indents — whereas the tag is known before the line is read, so the
rule is decidable with no inference about the file's origin. The amendment changes no story, no
success criterion and no scope, so it is notified rather than re-gated.

## D13 — FR-008 amended and FR-008a added: a file with no reference type anywhere is a failure

**Ambiguity**: Scopus omits `TY` entirely when the person exporting unchecks "Source & document
type". Under the approved FR-008 the whole file counts as material before the first entry, so it is
skipped and the run reports a successful import of nothing.

**Chosen**: FR-008 is scoped to files that contain at least one reference-type tag. A file with RIS
tag lines and no reference type anywhere is a reported parse failure naming the missing tag.

**Why defensible**: A real export from a supported producer yielding an empty catalogue in silence is
the exact failure the import contract's FR-013 exists to prevent — a caller should never have to
compare counts to discover something went wrong. The behaviour is confirmed by Scopus support in a
Zotero forum thread and independently in an asreview discussion, so it is a real case rather than a
hypothetical one.

## D14 — Scopus's mistyped chapters are not corrected

**Ambiguity**: Scopus exports some book chapters as `TY - JOUR`, with the book's title in `T2`, its
editors in `A2`, and `M3 - Book Chapter`. The real type is recoverable by inference.

**Chosen**: Store what the source states. Do not infer the type from other tags. `M3` is preserved on
the item under FR-024, so the evidence survives.

**Why defensible**: FR-031 draws the boundary at reading what the specification defines and
preserving the rest. Inferring a type from a combination of tags is the guessing that boundary rules
out, and it would make the catalogue disagree with the file the researcher holds. The consequence is
that `A2` must resolve to `editor` on `JOUR` as well as on chapter-like types — Zotero's rule, which
citation-js omits — because the case is real in a supported producer's output.

## D15 — `TA` is not mapped as a contributor

**Ambiguity**: `TA` is listed as "Translated Author" in secondary compilations.

**Chosen**: Treat it as an unmapped tag, preserved under FR-024.

**Why defensible**: It is absent from both official specifications, Zotero drops it explicitly, and
in the one corpus file where it appears it is PubMed's journal-title abbreviation. Mapping it as a
name would store a journal abbreviation as a person.

---

# Foundational-phase decisions (Implementer, 2026-08-05)

## D16 — The #41 regression test lives in its own module, not `tests/test_converters.py`

**Ambiguity**: T041 asks the fix to be tested "on the generator directly" — take 20,000 values,
assert all distinct. `literature/converters.py`'s natural mirror under Article XIV is
`tests/test_converters.py`, but this story's own prohibition keeps that file green **and
byte-for-byte unmodified**, since it is the evidence T005 was a move and not a rewrite. Article
XIV's own mirror rule (one test module per source module, "the per-unit split is expressed with
classes, not extra files") is exactly what a second file for the same module would violate.

**Chosen**: `tests/test_converters_dedup.py`, a new module holding one class,
`TestGenerateDedupSuffix`, testing `_generate_dedup_suffix` directly.

**Why defensible**: The hard prohibition on touching `tests/test_converters.py` is explicit and
un-ambiguous; Article XIV's mirror rule was written for the ordinary case and states no exception
for "the one file you are forbidden to edit." Between reopening a file the story exists to prove
untouched and accepting one narrow, clearly-labelled exception to a structural convention, the
convention gives. The new module's docstring says why it exists rather than leaving the deviation
unexplained.

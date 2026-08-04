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

The cost is that the source must be readable more than once. That holds for a path and for an
uploaded file alike, and where it does not hold the import fails saying so rather than quietly
importing with macros unexpanded. Degrading silently there would reproduce the exact failure D2
rejects, a record that lands looking complete while missing what the source supplied.

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

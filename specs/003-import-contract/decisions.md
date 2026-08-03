# Decisions: A Standard Contract for Importing Bibliographic Files

Rationale too long to sit inline in `spec.md`, plus every point resolved without escalation.
Maintainer decisions are marked as such. Everything else was resolved from the intake
discussion and the governing documents, and is open to veto at the spec gate.

---

## D1 — The contract lands ahead of any concrete format

**Maintainer decision.**

Article III bars a base class or indirection without a present, concrete second use, and R5 says
the contract "ships together with the first importer rather than ahead of it". Issue #21 says the
opposite: that the surface is settled "before the first format arrives". Both were written the
same day, and the contradiction was raised at intake.

Resolved in favour of the contract landing first. The reasoning that makes it consistent with
Article III rather than an exception to it: the workflow is four stages and only the first two are
format-specific. Converting CSL JSON into an `Item` is existing, exercised code with real callers
today. So the contract is not a speculative wrapper around nothing. It is a seam drawn through a
pipeline whose downstream half already exists, with two concrete formats (#22, #23) queued
immediately behind it.

An alternative was considered and rejected: routing the existing CSL JSON conversion through the
new contract as its first registered format, so that something real used it on day one. Rejected
because CSL JSON is this feature's *intermediate representation*, not one format among many.
Registering it as a format would put the pipeline's own currency on the same footing as the file
syntaxes that convert into it, which is exactly the conceptual muddle the contract exists to
prevent.

## D2 — Terminology

Self-resolved. The maintainer asked for the most appropriate terms rather than nominating any.

| Term | Meaning | Rejected alternatives |
|---|---|---|
| **format** | A plug-in for one file syntax | *provider* (says nothing about what is provided), *importer* (conflates the syntax with the act of importing) |
| **entry** | One record as it appears in a source file, before it becomes an `Item` | *record*, since `CONTEXT.md` already retires "Record" as a synonym for an item, and reusing it for the source-side unit would collide with that |
| **outcome** | The fixed vocabulary value on an entry result | *status* (suggests something that changes over time) |
| **import result** / **entry result** | The report for a run, and for one entry within it | — |

`django-import-export` was the model raised at intake, and its `Format` concept maps cleanly. Its
`Resource` concept deliberately does **not** come across: a `Resource` exists so a caller can
configure how records map onto a model, and here that mapping is fixed by CSL JSON and not the
caller's to change.

## D3 — An entry is atomic

Self-resolved. Per-entry importing was settled at intake at the *file* level: one bad entry does
not stop the others. That leaves the level below unaddressed, because a single entry produces an
`Item` plus related `ItemName`, `ItemDate`, and `ItemIdentifier` rows, and a failure part-way
through could leave an item stripped of its contributors.

An entry is therefore all-or-nothing. Two reasons: the outcome vocabulary has no value that could
honestly describe a partial result, and Article XI treats bibliographic data as valuable and hard
to recreate, which a silently half-built item directly undermines. It is also the more useful
behaviour, because a wholly absent entry can be re-imported after the source is fixed, whereas
a partial one has to be found and repaired by hand.

## D4 — An entry is identified by index, plus a source handle where one exists

Self-resolved. The draft said "enough positional information", which is not testable.

An index is always available and is enough to locate an entry mechanically, but on its own it
serves a person badly: "entry 47 of 400 failed" gives them nothing to search for. Where the format
has a handle of its own, such as a BibTeX cite key or an RIS record number, that handle is what
its owner recognises, so it is carried too. It is optional because not every syntax has one, and requiring it
would push formats into inventing identifiers.

## D5 — The result is the reporting channel, and logging is additive

Self-resolved. Today `from_csl_json_list` skips invalid items with a `logger.warning` and returns
only the successes, which is the exact failure R5 names: a caller can tell something went wrong
only by comparing counts.

Every failure now appears in the returned result. Logging alongside it is permitted for operator
visibility but is never the sole channel. `from_csl_json_list` itself keeps its current behaviour
for callers using it directly. This feature does not change that function's contract, and
changing it would be a breaking change to a published API for no gain here.

## D6 — No throughput target

Self-resolved. R5's concern is correct handling of messy real-world files, not speed, and any
latency or throughput figure written here would be invented rather than derived from a requirement.

The one property worth constraining is memory: an import must not need a fully converted copy of
the whole file at once. Memory grows with the number of entries reported, which is unavoidable
given that the result accounts for every entry, and that growth is accepted.

## D7 — The glossary is updated in the same change

Self-resolved. The feature introduces four terms `CONTEXT.md` does not carry, and two informal
synonyms ("provider", "record") are already circulating. Article VI requires public API changes to
ship their documentation in the same PR, and `CONTEXT.md` is the file that stops vocabulary
drifting between specs. Leaving it to a follow-up is how a glossary goes stale.

## D8 — Dry run is in scope

**Maintainer decision**, taken after the feature statement was first proposed without it.

It changes the contract's shape rather than sitting on top of it, since a format must be able to
run every stage and report every outcome without anything being written. That is why it belongs in
this feature instead of being added later against a surface that did not anticipate it.

## D9 — De-duplication against stored records is out of scope

**Maintainer decision.**

Deciding when two records describe the same reference is its own problem, involving identifier
matching, disagreement between sources, and a policy on what wins. It has nothing to do with file
formats, and folding it in would make the contract carry a judgement the roadmap never asked for.

The contract still leaves room for it: because an entry's fate is one value from a fixed vocabulary
rather than a pass/fail flag, a later feature that can make that judgement reports its decisions as
*skipped* without reopening the shape settled here. Note the current behaviour this implies:
importing the same file twice today produces two copies of every entry, with citation keys
de-duplicated only within a single run.

## D10 — Detecting a file's format is out of scope

**Maintainer decision.** The caller names the format. Enumerating the registered set is in scope,
which is what lets a caller stay ignorant of the individual formats. Working out which format
a given file holds is guesswork over extensions and content, cannot be tested honestly with no real
formats registered, and is best decided wherever files are accepted from users.

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

## D11 — Reproducing the IntegrityError from research.md R2 needs a validation bypass

Self-resolved, during US1 implementation (T006).

research.md R2's probe demonstrated the transaction/savepoint mechanics using a raw
`ItemIdentifier.objects.create()` call that bypasses `full_clean()`. Reproducing a *real*
`IntegrityError` (rather than the `ValidationError` `full_clean()` normally raises first) through
the actual, unmodified `from_csl_json()` turns out to be structurally impossible from CSL JSON
content alone: every identifier write in that function is `full_clean()`-then-`save()`,
sequentially, and `full_clean()`'s `validate_unique()` already queries the database — so a second
identifier of a type already written for the same item is refused *before* it reaches the database,
every time. Confirmed empirically (a two-identifier probe against the real models) before writing
the test, rather than assumed.

Two things had to combine to reach the database at all, both confined to the test:

1. `DuplicateCustomIdentifier`, a `dict` subclass whose `.items()` yields the same key twice —
   something no real CSL JSON parse could ever produce (a Python `dict` cannot hold a duplicate
   key), standing in for two entries reaching `ItemIdentifier.save()` for the same `(item, type)`.
2. `bypass_identifier_validation`, a `monkeypatch`-scoped no-op for `ItemIdentifier.full_clean`,
   confined to the one test that asks for it — needed because even with (1), the *second* write's
   `full_clean()` would still catch the collision as a `ValidationError` before it reached the
   database.

Neither touches `converters.py` or any production code; both are test-only constructs, verified to
produce a genuine `sqlite3.IntegrityError` end to end through the unmodified `from_csl_json()`
before being used in `test_runner.py`. The alternative — treating research.md R2's probe as
sufficient on its own and only testing the `ValidationError` partial-failure path in T010 — was
rejected because the task explicitly asks for the `IntegrityError` path, and research.md itself
frames the two exception types as "neither can be assumed to be the only one": the runner's
`except (ValidationError, IntegrityError)` around the per-entry savepoint (`runner.py`) needs a test
that actually exercises the second branch, not only the first.

**Revisit if**: a future format-specific test needs the same trick — at that point this pairing is
worth promoting from `tests/test_importers/conftest.py` to a shared test-support module, since
duplicating the `monkeypatch` + fake-dict combination per format would be exactly the copy-paste
Article II discourages.

## D12 — The entry stays runner-local; `EntryError` is caught wherever a format raises it

**Decided at:** US1 convergence review.

Two things the US1 implementation shipped as tasks.md and plan.md asked for, both wrong on review.

**The `Entry` dataclass is removed.** T008 called for it and data-model.md described it, but nothing
in the workflow builds one — a format is handed `raw` and returns CSL JSON, and a caller gets back
an `EntryResult` that already carries the index and the handle. That leaves a public frozen
dataclass that no caller ever constructs or receives, which is the abstraction without a present
concrete use Article III bars, and exactly the kind of accumulation this feature exists to prevent.
The index, handle, and raw entry stay as three locals in the runner's loop. data-model.md is amended
to describe them as facts that travel with an entry rather than as a class.

**`EntryError` raised from `parse` no longer escapes.** exceptions.py and contracts/importers.md both
document `EntryError` as coming from `parse` as well as from `to_csl_json`, but the runner caught it
only around the convert stage, so a format that recognises a bad entry while reading the file raised
straight through `import_file` — against FR-014, which says bad file content is reported and never
raised. It is now caught alongside `ParseError`: the generator is finished either way, so the
failure is recorded against the next index and the entries already recovered are kept.

`handle_for` moved inside the same block for the same reason. It reads the same untrusted content as
`to_csl_json` (FR-023), so an entry whose handle cannot be read is now reported as a failure without
a handle rather than ending the run.

Both are covered by regression tests that were confirmed to fail against the pre-fix runner.

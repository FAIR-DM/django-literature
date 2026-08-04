# ADR-0006 — An imported entry is stored whole or not at all

- **Status:** Accepted
- **Context date:** spec 003 (FR-006, SC-008), `literature/importers/runner.py`, issue #21

## Context

Importing a bibliography file is per entry: one unreadable record must not stop the rest of the
file, because real exports from reference managers are messy and a four-hundred-entry library
should not be blocked by one hand-edited record from 2011. That much was settled at intake.

It left the level below it open. A single entry does not produce one row. It produces an `Item`
plus its related `ItemName`, `ItemDate`, and `ItemIdentifier` records, and `from_csl_json` saves
the `Item` first and then creates the related rows one at a time, calling `full_clean()` on each.
There is no transaction anywhere in the package — a grep for `transaction` across `literature/`
before this feature returned nothing.

So a contributor that failed validation left the already-saved `Item` behind, stripped of its
authors, with nothing to indicate it was incomplete. That is present in shipped code, not a
hypothetical: it is reachable today through `from_csl_json` and `from_csl_json_list`.

An item missing its contributors is worse than an absent one. It is indistinguishable from a
genuinely author-less record, it satisfies queries it should not, and the only way to find it is to
notice by eye. Article XI treats bibliographic data as valuable and hard to recreate, which a
silently half-built record directly undermines.

## Decision

**An entry is atomic.** Every entry runs inside its own `transaction.atomic()` block, so an entry
that fails part-way leaves nothing at all behind and is reported as one failure. The outcome
vocabulary has no value that could honestly describe a partial result, and none is added.

The atomic block lives in the import runner, wrapping the call, **not inside `from_csl_json`**. The
function and its published behaviour for direct callers are untouched.

A savepoint per entry is what makes per-entry importing work at all, not merely tidy. Django opens
a savepoint for a nested `atomic()`, and the exception must be caught *outside* that block: catching
it inside and continuing marks the whole transaction unusable, and every later query raises
`TransactionManagementError`. Verified against these models before the design was fixed — three
entries where the second violates the `(item, type)` unique constraint on `ItemIdentifier`, with
entries one and three storing normally and entry two leaving nothing.

## Consequences

- No import can produce an item missing its contributors, dates, or identifiers.
- A wholly absent entry can be re-imported once the source is fixed. A partial one would have to be
  found and repaired by hand.
- Every format inherits the guarantee. A format author writes a parser and a conversion and cannot
  weaken it, because the contract gives a format no route to the stage that stores anything.
- The pre-existing hazard **remains for direct callers of `from_csl_json`**, which is deliberate:
  changing that function's behaviour is a breaking change to a published API and was out of scope
  here. Closing it is its own change, with its own compatibility question.
- A dry run composes with this: the per-entry savepoints nest inside the outer rehearsal
  transaction, so a database-level failure on one entry still lets the entries after it be reported.

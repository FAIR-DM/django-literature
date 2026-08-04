# Research: A Standard Contract for Importing Bibliographic Files

Phase 0. Five questions the plan depends on, each answered against the code or the framework
rather than from recollection.

---

## R1 — What carries over from `django-import-export`, and what does not

That library was the model raised at intake, so the useful question is which of its ideas earn
their place here.

**Carries over:**

- One fixed workflow with the format-specific parts underneath, so callers never branch on file
  type.
- A result object holding one row-level outcome per input record, rather than a count or a bare
  list of successes.
- An outcome drawn from a fixed vocabulary rather than a boolean, which is what lets a later
  feature add "skipped because already present" without changing the shape.
- A dry run as a first-class mode of the same call, not a separate code path.

**Does not carry over:**

- `Resource`. It exists so a caller can declare how columns map onto model fields. Here that
  mapping is CSL JSON and is fixed by the package, so a `Resource` equivalent would be a
  configuration point with nothing to configure.
- Its `new / update / delete / skip / error / invalid` vocabulary. Update and delete need
  matching against stored records, which is out of scope by decision D9. Shipping unreachable
  values would be the speculation Article III forbids. Three values, all reachable: **created**,
  **skipped**, **failed**.
- Widget/field-level coercion. CSL JSON conversion already owns that.

## R2 — Transaction semantics for per-entry atomicity and the dry run

This is the mechanism the whole feature rests on, so it was verified by running it against this
package's models on SQLite rather than reasoned about.

**Question:** if each entry runs inside its own `transaction.atomic()` block nested in an outer
one, does a database-level failure in one entry leave the outer transaction usable for the entries
that follow?

**Answer: yes, and only when each entry has its own block.** Django opens a savepoint for a nested
`atomic()`. When the inner block raises, that savepoint alone is rolled back and the outer
transaction continues to accept work. The exception must be caught *outside* the inner block —
catching it inside and carrying on marks the whole transaction unusable and every later query
raises `TransactionManagementError`.

Probe result, three entries where the second violates the `(item, type)` unique constraint on
`ItemIdentifier`:

```
CAUGHT: IntegrityError
VISIBLE INSIDE: ['a', 'c']      # entry 2 left nothing behind; entry 3 still worked
AFTER ROLLBACK COUNT: 0         # outer set_rollback(True) discarded everything
```

Two consequences for the design:

1. **Per-entry atomicity is a savepoint per entry.** It is not optional book-keeping — without it
   the first entry that fails at the database level poisons the rest of the run.
2. **The dry run is the same code with an outer `atomic()` and `set_rollback(True)` at the end.**
   Every stage genuinely executes, so outcomes are real rather than predicted, and nothing
   survives. No separate rehearsal path to keep in step with the real one.

Worth noting: `full_clean()` catches most bad data as `ValidationError` before any SQL runs, but
not all of it. Uniqueness across related rows surfaces as `IntegrityError` at save time, as the
probe shows, so both have to be handled and neither can be assumed to be the only one.

## R3 — Where the public names live

`literature/__init__.py` is **empty**. Nothing is re-exported at the top level today, and
`from_csl_json` is reached as `literature.converters.from_csl_json`.

Article X requires everything public to be "importable from the `literature` namespace". The
established reading in this package is a named submodule under `literature.`, not a top-level
re-export, and that is what the new surface follows: `literature.importers`.

Top-level re-export was considered and rejected. A Django app's `__init__.py` is imported before
the app registry is populated, so re-exporting anything that reaches the models at import time
raises `AppRegistryNotReady` at startup. Working around that needs a module-level `__getattr__`,
which is machinery bought to solve a problem the package does not currently have — and it would
make this feature the only part of the package reachable from the top level, which is a worse
inconsistency than the one it fixes. If top-level exports are ever wanted, that is a change to the
whole public surface at once, not a side effect of adding an importer.

## R4 — Reusing `from_csl_json` without changing it

FR-004 requires the existing conversion to be reused and its behaviour for direct callers left
alone. Reading `literature/converters.py`, `from_csl_json` saves the `Item` first and then creates
names, dates, and identifiers one at a time, with **no transaction anywhere in the package** — a
grep for `transaction` across `literature/` returns nothing.

So today, a contributor that fails validation leaves the already-saved `Item` behind, stripped of
its authors. That is the concrete defect decision D3 anticipated, and it is present in shipped
code.

**The atomic block goes in the contract, wrapping the call, not inside `from_csl_json`.** Two
reasons. It satisfies FR-004 literally, since the function is untouched and every existing caller
behaves exactly as before. And it puts the guarantee where the guarantee is promised: the contract
says an entry is atomic, so the contract is what enforces it. Changing `from_csl_json` itself would
alter published behaviour for callers who never asked for it, which R5's scope does not cover.

`from_csl_json_list` is likewise left alone (decision D5). The contract does not call it — it calls
`from_csl_json` per entry, because the list wrapper's whole behaviour is the silent skipping this
feature exists to replace.

## R5 — Consuming entries one at a time

FR-024 requires that a format's entries are not all materialised before anything is stored.

A format yields entries as an iterator, and the runner consumes it with a `for` loop, storing each
entry as it arrives. Nothing about this is exotic — it is the default shape unless a list is built
deliberately — but stating it here is what stops a format from being written to return
`list[Entry]`, which would quietly make the requirement unmeetable from the outside.

The result still grows with the number of entries, since it accounts for every one. That is
accepted (decision D6) and is a different thing from holding the whole converted file.

The dry run holds one transaction open for the length of the file. On PostgreSQL that is a long
transaction for a large import. It is the price of a rehearsal that reports real outcomes rather
than guesses, and no alternative was found that keeps outcomes truthful.

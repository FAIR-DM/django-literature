# ADR-0009 — An import never matches against items already stored

- **Status:** Accepted
- **Context date:** spec 005 (Assumptions), `literature/converters.py` (`from_csl_json`), issue #23

## Context

Once a format mints citation keys from an entry's own content (ADR-0008), two entries with the same
content produce the same key. That invites an obvious question: if an incoming entry's key matches
one already in the table, is it the same reference?

The question generalises past keys. Any import could compare titles, DOIs or author lists against
stored items and decide it has seen this reference before.

## Decision

**No import compares an incoming entry against anything already stored.** Importing the same file
twice produces two sets of items.

Batch-scoped de-duplication is unaffected and is not this: it resolves key collisions *inside one
import* so a batch never writes two items with the same key (ADR-0001). It is a collision-resolution
mechanism, not a matching one, and it never consults rows from an earlier import.

## Consequences

- A caller who needs "did I already import this?" builds it themselves, on top of whatever field
  their data makes reliable. The package does not guess.
- Deciding when two records are the same reference is a hard problem that established reference
  managers do not solve either — importing the same citation into a desktop manager ten times yields
  ten entries. Neither the catalogue nor an importer is the place to solve it implicitly.
- Duplicate detection remains a plausible feature in its own right, with its own interface and its
  own choices about what counts as a match. Nothing here forecloses it.
- Re-importing a file is a safe way to observe what a format now does with it, because the result
  does not depend on what earlier runs left behind.

# ADR-0001 — citation_key is unique per import batch, not globally

- **Status:** Superseded by ADR 0023 (was: Accepted, confirmed 2026-07-23)
- **Superseded by:** [ADR 0023](0023-citation-key-uniqueness-is-the-readers-concern.md): uniqueness is the reader's concern, and a key is now stored exactly as it is given.
- **Context date:** observed in `literature/models.py` (`Item.citation_key`), `literature/converters.py` (`_resolve_citation_key`, `_generate_dedup_suffix`), spec 001

## Context

Every CSL JSON item carries an `id` / `citation-key`. A store could treat that key three ways:
(a) the primary key, (b) a globally unique column, or (c) a non-unique human label. Real-world
CSL data routinely reuses keys across sources, and two imports can legitimately contain the same
key for different items.

## Decision

`citation_key` is an indexed but **non-unique** `CharField`, and is not the primary key. On
import, `from_csl_json` resolves collisions *within the batch* by appending a generated suffix
(`_resolve_citation_key` / `_generate_dedup_suffix`), so a batch never produces two items with the
same key — but keys are free to repeat across separate imports.

## Consequences

- Items are identified internally by their surrogate primary key; `citation_key` is a display and
  lookup handle, not an identity.
- Callers must not assume a `citation_key` is unique across the table or stable across imports.
  Code that treats it as a key is wrong against this model.
- De-duplication is batch-scoped by design; cross-batch key coordination (if ever needed) is a new
  feature, not a change here.

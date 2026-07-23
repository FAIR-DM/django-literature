# ADR-0002 — Identifier types are open, not a closed enum

- **Status:** Accepted (confirmed by Sam 2026-07-23)
- **Context date:** observed in `literature/models.py` (`ItemIdentifier`), `literature/choices.py` (`IdentifierType`), spec 001 (FR-017)

## Context

CSL JSON promotes a handful of identifiers (DOI, ISBN, ISSN, PMID, PMCID, URL) to top-level
fields, but bibliographic sources carry many more (arXiv, Handle, ARK, and so on). A model could
restrict identifiers to a fixed `choices` set, or accept arbitrary types.

## Decision

`ItemIdentifier.type` is a plain `CharField` with **no `choices=` validation** — any identifier
type string is stored rather than rejected (FR-017). The `IdentifierType` enum lists the six known
types for lookup, documentation, and format validation only; it is not a constraint. Known-type
values are format-validated (`validators.py`); unknown types are stored as-is. Each item holds at
most one identifier per type (`unique(item, type)`).

## Consequences

- The store round-trips identifier types it has never heard of, which keeps import lossless.
- Adding `choices=` to `type` would break the store-unknown-types contract — don't.
- Format validation only applies to the six known types; unknown types are trusted verbatim.
- One identifier per `(item, type)` is a current limit (e.g. a single item can't hold both an
  ISBN-10 and an ISBN-13); widening it is a feature, not a fix.

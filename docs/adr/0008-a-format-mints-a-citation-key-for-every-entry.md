# ADR-0008 — A format mints a citation key for every entry it hands over

- **Status:** Accepted
- **Context date:** spec 005 (FR-019 through FR-023, SC-003, SC-004), `literature/importers/ris.py`, `literature/converters.py` (`_resolve_citation_key`), issue #23

## Context

`from_csl_json` refuses a record that supplies neither `citation-key` nor `id`. BibTeX made that
easy: every entry has a cite key by definition, so the format could pass the source's own value
through and never think about it.

RIS has no cite key. Some producers write an `ID` tag and some do not, and the two database exports
this package cares most about — Scopus and Web of Science — typically do not. On the existing
conversion path, a database download would fail entry by entry for want of a key, which is the exact
case the RIS support was asked for.

Three exits were available: refuse keyless entries, widen the conversion to accept records without a
key, or have the format supply one.

## Decision

**Supplying a citation key is the format's job, not the caller's and not the conversion's.** A
format hands over a record that already carries one, by whatever route suits its source:

- Where the source states a key, it is taken verbatim.
- Where the source states none, the key is minted from the entry's own bibliographic content, and
  minting is deterministic — the same entry yields the same key on every run, so re-importing a file
  is comparable to the import before it.
- Where the entry is too sparse to mint from, its position in the file is the last resort, so no
  entry is ever refused for want of a key.

A minted key is checked against the column's length limit before storage, with room left for the
de-duplication suffix that batch collision resolution may add (ADR-0001), because the conversion
does not validate that field.

## Consequences

- A format that reads a keyless source must decide what a minted key is made of, and say so in its
  own documentation. The RIS mapping page records the recipe it uses.
- A minted key is the package's invention rather than the researcher's. That is stated in the
  specification and in the user-facing documentation rather than left to be discovered.
- The conversion stays strict. Nothing was widened to accept a keyless record, so the guarantee that
  every stored item has a key still holds at the boundary where it is enforced.
- Key style is not configurable, and regenerating existing keys is a separate feature. Neither is
  foreclosed.

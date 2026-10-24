# ADR 0035 — The variables a citation processor generates are kept in `custom`

**Status:** accepted

## Context

CSL JSON defines five variables that a citation processor works out while it formats a document:
`citation-label`, `citation-number`, `first-reference-note-number`, `locator` and `year-suffix`.
They come from where a reference is cited in one document: its number in that bibliography, the
note it was first cited in, the letter that separates two works by the same author in the same
year, the page being cited. They describe one citation, not the reference.

`Item` stored each of them as a column. No document is formatted in this package, so the columns
held nothing a person could enter or read meaning from. The write form already left them out, and
the reference page showed them under a group of their own (#147).

Dropping them outright would have broken the constitution's round-trip guarantee: a CSL JSON file
carrying any of them would come back from an import and export without them.

## Decision

The five columns are removed from `Item`. The variables still travel through the package, in the
item's `custom` data under their CSL JSON names:

- `from_csl_json()` moves any of them it is given into `custom`, beside whatever `custom` already
  held, and keeps each value as given, a number staying a number.
- `to_csl_json()` writes any it finds in `custom` back out at the top level, and leaves them out of
  the exported `custom`.
- Migration `0004` moves every stored value into `custom` before dropping the columns. Reversing it
  moves them back.

The round-trip guarantee is kept as it was written, rather than restated to cover only the
variables that describe a reference.

## Consequences

- Importing then exporting gives the same CSL JSON whether or not the file carries these
  variables.
- They appear nowhere in the front end: not on the form, not on the reference page, not in the
  field groups.
- `custom` has to be a JSON object to hold them. An import carrying one beside a `custom` that is
  not an object is refused with a `ValidationError` (code `custom_not_an_object`), and the migration
  stops, naming the affected citation keys, rather than discard a stored value or rewrite the
  item's own `custom`.
- A file that already carries one of these names inside `custom` is read the same way, so its
  export writes the value at the top level.
- `tests/test_ui/test_fieldgroups.py`'s ceiling on how many fields a journal article leads with
  measured against every field in the groups, which included these five although they were never on
  the form. It now states its bound as the count it was set at, fewer than 30 fields, half of the 60
  the groups then held. No type's assignment changed, and a journal article still leads with 28.

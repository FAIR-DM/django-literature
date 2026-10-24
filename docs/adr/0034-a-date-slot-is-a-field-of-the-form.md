# ADR 0034 — A date slot is a field of the form, not a row of a set

**Status:** accepted

## Decision

The write form gives each of CSL JSON's six date slots a field of its own on `ItemForm`, a start and
an end, and writes each slot's `ItemDate` when the form saves. The dates are no longer an inline
set of rows each naming a slot.

The guarantees ADR-0032 states for related rows hold for dates in this shape:

- A slot holding a value is always shown, whatever the type mapping leads with.
- Only the start and end are on the form, so a save writes no other part of an `ItemDate`. A slot
  whose field is emptied loses its date, and keeps the original text of an imported date it also
  holds.
- A slot whose fields did not change is not written at all.

Removal of a date is now an empty field, not a row's deletion flag. ADR-0032's third part still
governs contributors and identifiers, which remain sets.

## Why

A reference has at most one date per slot, and there are six slots. A set of rows each choosing its
own slot made a fixed shape look open-ended: the person picked a slot from a list, a slot could be
offered twice and had to be refused, and the type mapping could only decide which rows were
pre-filled. Six named fields say what the record can hold, show and hide by the type as the scalar
sections do, and need no duplicate-slot check.

## Consequences

- `ItemDateForm`, `ItemDateFormSet` and `DateInline` are gone.
- A date's season, circa flag and raw parts stay outside the form, as before.
- The type-to-slot mapping, `TYPE_DATE_SLOTS`, now decides which fields are shown.

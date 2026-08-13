# ADR 0021 — Type scoping is presentation, never storage

**Status:** accepted

## Decision

The write form declares every scalar field of an item, always. Which fields a reader sees is decided
in the browser, by showing and hiding groups as the chosen item type changes. The server never
builds a narrower form.

Three consequences follow, and all three are guarantees rather than side effects:

- A hidden field keeps its value and posts it back, so changing a reference's item type cannot
  discard anything the reference already holds.
- A field holding a value is always shown, whatever the type says, so imported content can never be
  hidden behind the mapping.
- The two JSON fields the form does not carry are left exactly as they were by a save.

## Why

The alternative, building the form's field list from the item type, silently loses data. Django
assigns every field a form declares from its cleaned data, so a field omitted from the form is
written as empty rather than left alone. The guarantee would then rest on a rule someone has to
remember rather than on the shape of the code.

Rendering everything makes the guarantee structural. The cost is a form page carrying markup for
all sixty fields, which for a form nobody submits at volume is the right trade.

The limit is worth stating plainly: this holds for the rendered page, not for the endpoint. Any
request that omits a field still blanks it. That is why the demo's check posts the whole form back
with one field changed rather than posting the field it means to change.

## Revisit if

The form grows large enough that page weight becomes a real cost, or the write path gains a caller
that is not the rendered page: an API, an import through the interface, a partial update. Any of
those makes "the server never sees a narrower form" false, and the guarantee then needs to move
into the view.

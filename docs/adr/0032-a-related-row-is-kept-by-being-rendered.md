# ADR 0032 — A related row is kept by being rendered

**Status:** accepted

## Decision

ADR-0021 keeps a reference's scalar content safe by declaring every field on every form, so a
hidden field posts its own value back and a change of item type discards nothing. Rows of related
records (a reference's contributors, its dates, its identifiers) do not inherit that guarantee,
and it is upheld for them explicitly instead, in three parts:

- A slot holding a value is always rendered, whatever the type mapping would lead with. What the
  mapping decides is what is *offered*, never what can be *stored*.
- The parts of a related record the form does not offer are never declared on it, so a save through
  the form cannot write them.
- Removal is explicit, through the formset's own deletion, never implied by a row's absence from a
  submission.

## Why

ADR-0021 names its own revisit condition: a write path that is not the rendered page. Inline
formsets over related rows are that condition arriving, and the failure mode is not the one
ADR-0021 was built against.

The two are genuinely different. An omitted scalar field is *blanked*, because Django assigns every
declared field from cleaned data, so leaving one out writes empty rather than leaving it alone, and
declaring everything is what makes that impossible. An omitted row is simply *not there*. No
assignment happens, nothing is overwritten, and the row survives or does not depending on how the
formset was told to read the submission. Declaring everything does not help, because there is no
field to declare.

So the same guarantee needs a different mechanism, and the mechanism has to be stated rather than
inherited. Left implicit, each of the three parts fails quietly, and in a way no test notices
unless it is written to:

- A date in a slot the reference's current type does not lead with disappears from the page, and
  then from the record.
- A field the form never meant to touch gets written as empty, because it was declared for some
  unrelated reason.
- A row vanishes, because a submission did not mention it.

The third part is the one most worth spelling out. Treating absence as deletion means any
truncated, filtered or partial submission silently removes rows, which is exactly the class of
failure ADR-0021 exists to prevent, arriving through a different door.

## What this rules out

- Building a related-row set from the item type alone. The type decides the starting point, and
  every slot already holding a value is added to it.
- Declaring a related record's full field list on its row form for convenience. Fields the form does
  not offer stay undeclared, so they cannot be written.
- Reading a missing row as an instruction to delete.

## Revisit if

The write path gains a caller that is not the rendered page: an API, a partial update, or an import
that writes through these forms. As with ADR-0021, the guarantee then has to move again, and this
time there is no rendering step left to carry it.

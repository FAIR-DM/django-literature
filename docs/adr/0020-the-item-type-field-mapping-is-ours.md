# ADR 0020 — The item type to field mapping is this package's own artefact

**Status:** accepted

## Decision

`literature/ui/fieldgroups.py` holds a mapping from each of the 45 CSL item types to the fields a
form offers for that type, authored and maintained here. Fields are gathered into named groups and
each type declares which groups it uses.

The mapping governs presentation only. Every scalar field remains storable on every item type, the
form renders and posts all of them, and no stored value is ever discarded because a type says it
does not apply. A disputed entry produces a form that asks in an odd order, never a reference that
cannot be recorded.

Each type's entry carries a comment naming the criterion that decided it. The criteria, in order:

- the type definition names the group
- a variable definition is written in terms of that type
- a type that sits inside a container takes the container group
- the archival group, for types whose subject is a held object
- the numbering group, where the type is or sits inside a numbered sequence
- the original-publication group, where republication or translation is ordinary

A type matching none of these stays at the baseline, and its comment says what a person recording it
would enter instead.

## Why

CSL publishes no such mapping, and the absence is deliberate rather than an oversight.
`csl-data.json` declares all its properties flat, with the item type as a plain enumerated string
and no conditional construct anywhere, so every variable validates on every type. The specification
lists variables by data category and uses the type only to drive conditionals inside citation
styles. A request for a per-type variable list has been open on the specification's own tracker
since 2016, and one of the format's creators argues against having one on principle.

Nothing publishable fills the gap either. Style files encode rendering rather than applicability,
and both branches of a type split routinely emit the same variable. The nearest real mapping is
Zotero's schema, which covers 32 of the 45 types, omits 29 variables, reverses ambiguously in
eleven places, and, decisively, carries no licence at all, so redistributing it would mean
redistributing unlicensed material.

That leaves authoring one. What makes that acceptable rather than reckless is the limit above: this
is a decision about what a form asks first, not about what the store accepts. The evidence base is
the specification's own two appendices, which name variables for 14 of the 45 types directly and
carry type-bound language in roughly a third of the variable definitions.

Grouping rather than mapping field by field is what keeps it maintainable. Forty-five short lists
of groups can be read and argued with. Forty-five lists of sixty fields cannot.

## Revisit if

The citation format publishes a per-type variable mapping of its own, or one appears under a licence
this package can use. Either would make an authored mapping the wrong answer, and the groups would
become a presentation layer over a published source rather than the source itself.

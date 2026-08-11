# ADR-0017 — Identical stored names are not merged

- **Status:** Accepted
- **Context date:** spec 006 (D7), `literature/ui/views.py` (`ContributorDetailView`), issue #45

## Context

Names are stored once and shared across the items that credit them (ADR-0003). Giving a contributor
a page of their own makes a consequence of that visible for the first time: a person imported from
two files can hold two `Name` records with the same family and given values, and so has two pages,
each showing half of their work.

The interface is where a reader notices, so it is also where the temptation to fix it appears: collapse
records that look alike into one page.

## Decision

**Two contributor records holding identical names keep separate pages. Nothing in the interface
decides that two stored names are the same person.** The page reports what the catalogue holds.

## Consequences

- This extends ADR-0009's stance from import to presentation: the package does not guess that two
  records describe the same thing, at either end.
- Authorship disambiguation is a research problem, and established reference managers get it wrong
  regularly. A browse page that merged silently would assert something the catalogue does not hold,
  with no way for a reader to see the merge or correct it.
- De-duplication stays available as a feature in its own right, where the evidence that justifies a
  merge can be specified and a maintainer can decide it — rather than being an emergent property of
  a page template.

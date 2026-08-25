# ADR 0025 — One definition of what the catalogue narrows by

**Status:** accepted

## Decision

What the catalogue is searchable and filterable by is declared once, in `literature.ui.filters`, and
imported by every presentation that serves the catalogue. A view configures itself by pointing at
that definition. It does not restate the fields or redeclare the filters.

Any presentation added later follows the same rule, and a project that wants to narrow on something
else subclasses the filter set rather than adding a second definition beside it.

## Why

Two definitions drift, and the drift is silent. A field added to the table's search and not the card
list's produces two catalogues that disagree about what the library contains, and nothing fails. A
reader who finds a reference through one route and not through the other has no way to tell which of
the two is wrong.

The agreement is also testable this way. A test compares what the two presentations return for the
same query, which turns a convention that reviewers have to remember into a check that runs.

The page that lists one contributor's credited works is deliberately outside this. It answers a
single question and its reader has already narrowed by contributor, so it takes the catalogue's card
configuration without the search box and the filters. That is why the shared configuration lives in
a mixin the two card pages compose, rather than in an inheritance from the catalogue view.

## Revisit if

A presentation appears whose reader genuinely needs a different set — an embedded picker, or a
public reading list narrowing on something the catalogue does not. The rule then becomes one
definition per audience, each named, rather than one definition overall.

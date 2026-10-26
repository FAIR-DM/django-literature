# Decisions — FS-013

Rationale too long to inline in `spec.md`, plus every ambiguity resolved without escalating.
The spec stands alone. This file records why.

## D1 — The search answers anyone

**Resolved in the clarification scan.** The search follows the catalogue list's read rule
(FR-010), which ADR 0036 left open. Restricting the search alone would protect nothing: every
reference it can return is already on the open list, with more detail than an option label
carries. A project that wants the catalogue private closes reading, and the search follows.

The guarantee a restricted picker does need is about writing, not reading: a form must never
save a reference outside its picker's restriction, whatever is submitted (FR-013). That is
checked when the form validates, on the server, so a hand-crafted request cannot get round it.

## D2 — A bounded result, best match first

**Resolved in the clarification scan.** One letter typed into a catalogue of thousands matches
most of it. Returning every match recreates the full list the feature exists to replace, and
paging a picker's results is a poor substitute for typing one more letter. So a search returns a
bounded number (FR-007), and references whose title or citation key starts with what was typed
come before those that only contain it, because a person typing the start of a title is the
commonest case. The bound itself is a planning decision.

## D3 — DOIs match as stored

**Resolved in the clarification scan.** People copy DOIs from wherever they meet them: a
`https://doi.org/` link, a `doi:` citation, or the bare form. The package already normalises a
stored DOI (`Item.doi`, issue #159), so the search normalises what was typed the same way before
comparing (FR-005). Matching only the exact stored text would make the pasted link, the form
most likely to arrive, the one that fails.

## D4 — No offer to add, and no demo form

**Decided at review, 2026-10-26.** The draft carried two further stories: offering the catalogue's
add page when a search finds nothing, and a form in the demo project using both pickers. Both
were taken out at the specification's review as not wanted for now. A search that finds nothing
says so and offers nothing further.

Leaving the demo out departs from the constitution's Article XII, which keeps the demo current
when integration patterns change. The picker is covered by the package's own tests and its
documentation instead, and adding it to the demo is a later change.

## D5 — The fields and the search ship together

**Resolved in the clarification scan.** A field that needed the developer to mount a search
route of their own would fail SC-001 and leave every project writing the same URL entry. The
search is part of the catalogue's routes, so mounting the catalogue, which a project using the
front end already does, is the only wiring (FR-009). The fields find it by route name, so a
project's choice of prefix never matters.

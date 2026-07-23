# ADR-0004 — One date per CSL slot, stored as partial dates

- **Status:** Accepted (confirmed by Sam 2026-07-23)
- **Context date:** observed in `literature/models.py` (`ItemDate`), `literature/choices.py` (`DateType`), spec 001

## Context

CSL JSON dates are inherently partial (year-only, year-month, full date) and can be ranges. Each
item exposes several date *slots* (`issued`, `accessed`, `event-date`, …). A model must represent
partial precision faithfully and decide how many dates an item may hold per slot.

## Decision

Each date lives in an `ItemDate` row keyed to one `DateType` slot (six values), with **at most one
`ItemDate` per `(item, date_type)`**. Precision is stored with `django-partial-date`'s
`PartialDateField`: `begin` holds a single or start date, `end` holds the range end (never set
without `begin`). Un-normalizable source dates fall back to `season`, `circa`, `literal`, `raw`,
or the original `raw_date_parts` array, so no source date is lost.

## Consequences

- Year-only, year-month, full-date, and range dates all round-trip through the same field pair.
- One date per slot per item is a design limit (an item can't carry two distinct `issued` dates);
  widening it is a feature, not a fix.
- Dates that resist structured parsing are preserved verbatim rather than dropped, keeping import
  lossless at the cost of some rows carrying only `literal`/`raw` values.

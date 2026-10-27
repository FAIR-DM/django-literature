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

**ADR:** none — follows ADR 0036's read rule, which already records the decision.

## D2 — A bounded result, best match first

**Resolved in the clarification scan.** One letter typed into a catalogue of thousands matches
most of it. Returning every match recreates the full list the feature exists to replace, and
paging a picker's results is a poor substitute for typing one more letter. So a search returns a
bounded number (FR-007), and references whose title or citation key starts with what was typed
come before those that only contain it, because a person typing the start of a title is the
commonest case. The bound itself is a planning decision.

**ADR:** none — a local search behaviour, nothing downstream inherits it.

## D3 — DOIs match as stored

**Resolved in the clarification scan.** People copy DOIs from wherever they meet them: a
`https://doi.org/` link, a `doi:` citation, or the bare form. The package already normalises a
stored DOI (`Item.doi`, issue #159), so the search normalises what was typed the same way before
comparing (FR-005). Matching only the exact stored text would make the pasted link, the form
most likely to arrive, the one that fails.

**ADR:** none — local to the search, reusing the existing normaliser.

## D4 — No offer to add, and no demo form

**Decided at review, 2026-10-26.** The draft carried two further stories: offering the catalogue's
add page when a search finds nothing, and a form in the demo project using both pickers. Both
were taken out at the specification's review as not wanted for now. A search that finds nothing
says so and offers nothing further.

Leaving the demo out departs from the constitution's Article XII, which keeps the demo current
when integration patterns change. The picker is covered by the package's own tests and its
documentation instead, and adding it to the demo is a later change.

**ADR:** none — a scope decision for this feature, recorded here.

## D5 — The fields and the search ship together

**Resolved in the clarification scan.** A field that needed the developer to mount a search
route of their own would fail SC-001 and leave every project writing the same URL entry. The
search is part of the catalogue's routes, so mounting the catalogue, which a project using the
front end already does, is the only wiring (FR-009). The fields find it by route name, so a
project's choice of prefix never matters.

**ADR:** none — follows from the catalogue's existing route ownership.

## D6 — Design review applied in full

**Resolved at design review.** The review asked for two blocking changes and nine smaller ones, and
all eleven were cheap enough to apply to the plan rather than carry as watch items:

- The select draws its chosen options from one query for the chosen keys, never by walking the
  field's queryset, which would label the whole catalogue on every render.
- On a model form the picker is named through `Meta.field_classes`, so Django builds it from the
  model field and `required` and `limit_choices_to` follow the model.
- The restriction key is a digest of the restriction, so a page view does not write a new cache
  entry each time, and one class holds both directions of it.
- The DOI clause reuses the importers' `IdentifierNormalizer.normalize_doi` and drops out when
  nothing is left, so a bare prefix does not match every DOI.
- A non-integer submitted value redraws with an error, and a link outside the restriction opens
  showing its reference.

**ADR:** none — local to this feature's implementation, recorded in `plan.md`.

## D7 — Restriction through a cache key, replaced

**Replaced by D9.** The first build kept a restricted picker's query in Django's cache under a
signed key, so the shared search route could search only that restriction. Rebuilding on
django-tomselect removed it: the restriction now travels as django-tomselect's own filter
conditions, and no cache is used.

**ADR:** none — superseded before merge; D9's ADR records the design that shipped.

## D8 — The package's own picker script, removed

**Replaced by D9.** The first build carried its own script to wire Tom Select's remote loading,
and a fix to it from the browser check. Rebuilding on django-tomselect removed the script: that
package's own script loads the matches and shows the chosen references.

**ADR:** none — superseded before merge.

## D9 — The picker is a thin django-tomselect field

**Decided at the merge gate, 2026-10-26, at the maintainer's direction.** The first build drew the
control with django-mvp-forms' plain Tom Select widget and wrote its own script, widget and
restriction mechanism around it. django-mvp-forms already supports django-tomselect, which ships an
autocomplete view, model choice fields that point at a view by URL name, filter and exclude
conditions, and its own script. So:

- `ReferenceField` and `ReferenceMultipleField` subclass django-tomselect's
  `TomSelectModelChoiceField` and `TomSelectModelMultipleChoiceField`. Their only addition is a
  default config naming the package's search view, so one declaration still works (SC-001).
- The search route is a subclass of django-tomselect's `AutocompleteModelView`, carrying the
  matching, ranking, bound, label and open access this spec settled (D1–D3).
- A restriction is django-tomselect's `filter_by` / `exclude_by` config (FR-012). django-tomselect
  validates a submission against its view's unfiltered queryset, so the fields also apply the
  config's constant conditions when they clean a value, and the form refuses a reference outside
  them (FR-013, SC-004).
- Names: "reference" is used in the front end's public names, because that is the word the pages
  and docs use for an item. `Item` stays the model's name.

**ADR:** docs/adr/0037-the-reference-picker-is-a-django-tomselect-field.md

## D10 — The picker searches with the catalogue's filter set

**Decided at the merge gate, 2026-10-27, at the maintainer's direction.** The autocomplete view had
its own matching code beside `ItemFilterSet`, which ADR 0025 says must be the one definition of what
the catalogue is searchable by. The view now searches with `ItemFilterSet.q`, and what the picker
needed that the catalogue lacked was added there, so both gain it:

- identifiers are searched (`item_identifiers__value`), so a DOI or an ISBN finds its reference
- `CatalogueSearchFilter` reads each word as a DOI would be stored, so a pasted resolver address
  or `doi:` label still matches

The search now follows the catalogue's rule that any word typed may match, rather than the whole
text. Ranking a title or citation key that starts with the whole text first stays in the view,
because it is ordering, not filtering. The route moved to `autocomplete/`, named
`literature:item-autocomplete`.

**ADR:** none — applies ADR 0025, which already records the rule.

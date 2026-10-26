# Tasks — FS-013 A Reference Picker for a Project's Own Forms

**Branch**: `013-reference-picker` · **Plan**: [`plan.md`](plan.md) · **Research**: [`research.md`](research.md)

Every task is test-first per Article I. Tests for `literature/ui/picker.py` go in
`tests/test_ui/test_picker.py`. Tests for the search view go in `tests/test_ui/test_views.py`.
Documentation ships in the story that introduces the public name.

## User Story 1 — A developer adds a picker for one reference (P1)

- **T001** — `item_label(item)` in `literature/ui/picker.py` (plan P-2). Tests: title, year and
  first author; no year; no contributors; no title falls back to the citation key; an organisation
  as first contributor shows its literal name; first author is chosen over an editor credited
  first. Assert the parts, not a punctuation format. Query count: labelling a prefetched list of
  items issues no further queries.
- **T002** — `ItemSearchView` and the `item-search` route (plan P-1). Tests: matches by title,
  citation key, family name, literal name; a DOI found bare, with `https://doi.org/`, with
  `http://dx.doi.org/`, with `doi:`, in any letter case; empty `q` returns no results; no match
  returns an empty list with status 200; `%`, `_` and a quote match literally; a reference matched
  through two names appears once; at most `SEARCH_LIMIT` results from a larger catalogue; a title
  starting with the text ranks above one only containing it; an anonymous client gets 200; the
  route reverses under the test project's `catalogue/` prefix; the number of queries does not grow
  with the number of results.
- **T003** — `ItemSearchSelect` and `ItemChoiceField` (plan P-3). Tests: the rendered select holds
  only the chosen option, labelled with `item_label`, and none for an empty field; it carries
  `data-search-url` equal to the reversed route and `data-tom-select`; a valid submitted pk is
  cleaned to the `Item`; a pk that no longer exists is refused with the field's `invalid_choice`
  code; `required=False` accepts empty; on a `ModelForm` for a model with a foreign key to `Item`,
  declaring `ItemChoiceField()` as the field works and an existing instance renders its choice; in
  a formset, each row's select carries its own `data-search-url` and name. The test suite has no
  model of its own, so the `ModelForm` case uses `ItemName`, whose `item` is a foreign key to
  `Item`.
- **T004** — `literature/ui/static/literature/picker.js` (plan P-4) and its `Media` entry. Test:
  the widget's media lists `literature/picker.js` after `mvp_forms/tomselect.js`. The script's
  behaviour is checked in a headless browser at convergence, not here.
- **T005** — Documentation: `docs/choosing-a-reference.md` (how-to: install, the two Tom Select
  tags copied from `item_form.html`, declaring `ItemChoiceField` on a form and on a `ModelForm`,
  what the search matches, that the search follows the catalogue list's read access), added to the
  Getting Started toctree in `docs/index.md`. A short README section linking to it. `CHANGELOG.md`
  under Unreleased → Added. `CONTEXT.md` glossary entry **reference picker**.

## User Story 2 — A developer adds a picker for several references (P2)

- **T006** — `ItemSearchSelectMultiple` and `ItemMultipleChoiceField` (plan P-3). Tests: the select
  is `multiple` and holds every chosen option and no others; `remove_button` is on by default;
  several pks clean to the items; a repeated pk cleans to one item; a vanished pk is refused with
  `invalid_choice`; initial values render every choice. No model in the package has a many-to-many to `Item`, so
  the field is tested as a plain form field.
- **T007** — Documentation: the multiple field in `docs/choosing-a-reference.md`, CHANGELOG line.

## User Story 3 — A developer restricts which references a picker offers (P3)

- **T008** — The restriction key (plan P-5). Tests: an unrestricted field's select carries no
  `data-search-key`; a restricted field's does; the search with that key returns only references
  inside the restriction for a title shared inside and outside it; two restricted fields on one form
  carry different keys and each search returns only its own set; a tampered key answers 404 with
  empty results; a well-signed key absent from the cache answers 404 with empty results; a form
  submitted with a pk outside the restriction is refused with `invalid_choice` (Django's own
  behaviour, asserted because FR-013 depends on it). Use `LocMemCache` in tests.
- **T009** — Documentation: restricting a picker in `docs/choosing-a-reference.md`, including that a
  restricted picker needs a cache shared between processes in production, and what happens without
  one. CHANGELOG line.

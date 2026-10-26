# Tasks — FS-013 A Reference Picker for a Project's Own Forms

**Branch**: `013-reference-picker` · **Plan**: [`plan.md`](plan.md) · **Research**: [`research.md`](research.md)

Every task is test-first per Article I. Tests for `literature/ui/picker.py` go in
`tests/test_ui/test_picker.py`. Tests for the search view go in `tests/test_ui/test_views.py`.
Documentation ships in the story that introduces the public name. The stories run in order, US1,
US2, US3, each from the previous story's commit, because all three edit the same module, test
module and docs page.

## User Story 1 — A developer adds a picker for one reference (P1)

- **T001** — `item_label(item)` in `literature/ui/picker.py` (plan P-2). Tests: title, year and
  first author; no year; no contributors; no title falls back to the citation key; an organisation
  as first contributor shows its literal name; first author is chosen over an editor credited
  first. Assert the parts, not a punctuation format. Query count: labelling a prefetched list of
  items issues no further queries.
- **T002** — `ItemSearchView` and the `item-search` route (plan P-1). Tests: matches by title,
  citation key, family name, literal name; a DOI found bare, with `https://doi.org/`, with
  `http://dx.doi.org/`, with `https://dx.doi.org/`, with `doi:` and `DOI:`, in any letter case; a
  bare `doi:` or `https://doi.org/` matches nothing through the DOI clause; empty `q` returns no results; no match
  returns an empty list with status 200; `%`, `_` and a quote match literally; a reference matched
  through two names appears once; at most `SEARCH_LIMIT` results from a larger catalogue; a title
  starting with the text ranks above one only containing it, and so does a citation key starting
  with it; an anonymous client gets 200; the
  route reverses under the test project's `catalogue/` prefix; the number of queries does not grow
  with the number of results.
- **T003** — `ItemSearchSelect` and `ItemChoiceField` (plan P-3). Tests: the rendered select holds
  only the chosen option, labelled with `item_label`, and none for an empty field; it carries
  `data-search-url` equal to the reversed route and `data-tom-select`; a valid submitted pk is
  cleaned to the `Item`; a pk that no longer exists is refused with the field's `invalid_choice`
  code; `required=False` accepts empty; a bound form submitted with `abc` redraws with the field's
  error rather than failing; drawing the field issues the same number of queries for one chosen
  reference as for several, and never iterates the queryset (`django_assert_num_queries`); on a
  `ModelForm`, naming the field through `Meta.field_classes` gives an `ItemChoiceField` drawn with
  `ItemSearchSelect` whose `required` follows the model field (`ItemName.item` for `blank=False`,
  `ForeignKey(Item, blank=True).formfield(form_class=ItemChoiceField)` for the optional side), and
  an existing instance renders its choice; in
  a formset, each row's select carries its own `data-search-url` and name. The test suite has no
  model of its own, so the `ModelForm` case uses `ItemName`, whose `item` is a foreign key to
  `Item`.
- **T004** — `literature/ui/static/literature/picker.js` (plan P-4) and its `Media` entry. Test:
  the widget's media lists `literature/picker.js` after `mvp_forms/tomselect.js`. The script's
  behaviour is checked in a headless browser at convergence, not here.
- **T005** — Documentation: `docs/how-to/choosing-a-reference.md` (how-to: install, the two Tom Select
  tags copied from `item_form.html`, declaring `ItemChoiceField` on a plain form and, through `Meta.field_classes`, on a `ModelForm`,
  what the search matches, that the search follows the catalogue list's read access and is closed with the catalogue's other
  read routes by guarding the include), added to the
  Getting Started toctree in `docs/index.md`. A short README section linking to it. `CHANGELOG.md`
  under Unreleased → Added. `CONTEXT.md` glossary entry **reference picker**.

## User Story 2 — A developer adds a picker for several references (P2)

- **T006** — `ItemSearchSelectMultiple` and `ItemMultipleChoiceField` (plan P-3). Tests: the select
  is `multiple` and holds every chosen option and no others; `remove_button` is on by default;
  several pks clean to the items; a repeated pk cleans to one item; a vanished pk is refused with
  `invalid_choice`; initial values render every choice; drawing it issues the same number of queries for one chosen
  reference as for several; through `field_classes`, `required` follows a many-to-many's `blank`
  (`ManyToManyField(Item, blank=True).formfield(form_class=ItemMultipleChoiceField)`). No model in the package has a many-to-many to `Item`, so
  the field is tested as a plain form field.
- **T007** — Documentation: the multiple field in `docs/how-to/choosing-a-reference.md`, with its
  `ModelForm` example through `field_classes`, CHANGELOG line.

## User Story 3 — A developer restricts which references a picker offers (P3)

- **T008** — `SearchRestriction` and the restriction key (plan P-5). Tests: an unrestricted field's select carries no
  `data-search-key`; a restricted field's does; the search with that key returns only references
  inside the restriction for a title shared inside and outside it; two restricted fields on one form
  carry different keys and each search returns only its own set; the same restriction rendered twice
  carries the same key; a queryset assigned in the form's `__init__` is the one the key restricts
  to; an initial value outside the restriction is drawn as chosen, and submitting it unchanged is
  refused with `invalid_choice`; a tampered key answers 404 with
  empty results; a well-signed key absent from the cache answers 404 with empty results; a form
  submitted with a pk outside the restriction is refused with `invalid_choice` (Django's own
  behaviour, asserted because FR-013 depends on it). Use `LocMemCache` in tests.
- **T009** — Documentation: restricting a picker in `docs/how-to/choosing-a-reference.md`, including that a
  restricted picker needs a cache shared between processes in production, and what happens without
  one. CHANGELOG line.

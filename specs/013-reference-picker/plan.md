# Implementation Plan: A Reference Picker for a Project's Own Forms

**Branch**: `013-reference-picker` · **Spec**: [`spec.md`](spec.md) · **Research**: [`research.md`](research.md)

## Summary

Two form fields, `ItemChoiceField` and `ItemMultipleChoiceField`, subclass Django's
`ModelChoiceField` and `ModelMultipleChoiceField` and draw their select with django-mvp-forms'
Tom Select widgets. The select holds only the chosen references. A small script, in the pattern of
`creatable.js`, gives each control a `load` function that fetches matches from a new JSON route,
`literature:item-search`. Validation on submit is Django's own, against the field's queryset. A
restricted picker carries a signed key to its queryset, stored in Django's cache, so the shared
search route searches only that queryset.

## Technical Context

- **Language/Version**: Python ≥3.11, Django 5.2 / 6.0 / 6.1
- **Primary dependencies**: django-mvp-forms 0.8.0 (`TomSelect`, `TomSelectMultiple`, its starting
  script), Tom Select 2.5.2 loaded by the page. Nothing new is added to `pyproject.toml`.
- **Storage**: none. No model, no migration.
- **Testing**: pytest-django. View and field behaviour through the test client and form classes.
  The script's hooks (`data-` attributes) are asserted on the rendered select. The script's
  behaviour is checked once in a headless browser before review (it is not a unit-tested surface).
- **Constraints**: lives in `literature.ui` only (FR-016). A search costs a fixed number of
  queries whatever the result count.

## Constitution Check

- **I Testing**: test-first per task. **II Simplicity / III Anti-abstraction**: the fields are
  thin subclasses of Django's, the widget a thin subclass of mvp-forms'. **V Security**: the search
  is read-only and open like the list it mirrors. The restriction key is signed and resolved
  server-side, and nothing from the request is ever unpickled. Submissions are validated by Django
  against the field's own queryset. **VI Documentation**: a how-to page ships in the same stories.
  **VII Dependencies**: none added. **VIII i18n**: the only new strings are placeholder defaults,
  wrapped. **X Embeddable**: nothing a models-only install sees. **XII Demo**: not extended, by
  Sam's decision (`decisions.md` D4).

## Project Structure

### Source code

```
literature/ui/
├── picker.py                     # NEW: item_label(), ItemSearchSelect(Multiple), ItemChoiceField,
│                                 #      ItemMultipleChoiceField, store/resolve of a restriction key
├── views.py                      # + ItemSearchView
├── urls.py                       # + path("search/", …, name="item-search")
└── static/literature/picker.js   # NEW: gives each picker control its load function
docs/how-to/choosing-a-reference.md      # NEW how-to, added to the Getting Started toctree
README.md, CHANGELOG.md, CONTEXT.md
tests/test_ui/test_picker.py      # NEW, mirrors picker.py
tests/test_ui/test_views.py       # + the search view
```

## Design decisions

### P-1 — The search answers `{"results": [{"value", "text"}]}`, 20 at most

`ItemSearchView(View)` with `get()` only. Text from `?q=`, stripped. Empty text → empty results.
Matching and ranking as research R3. The DOI clause matches against
`IdentifierNormalizer.normalize_doi(text)` (`literature/importers/normalizers.py`), and is left out
when that is empty, so typing a bare `doi:` or `https://doi.org/` does not match every reference
with a DOI. Prefetch `item_dates` and `item_names__name`. The bound is a
module constant, `SEARCH_LIMIT = 20`. `JsonResponse` with `results`. No permission mixin, with a
comment pointing at ADR 0036, so the search follows the list's rule.

### P-2 — One label function, used everywhere

`item_label(item)`: title (or citation key when there is no title), then ` (year)` when there is
one, then `, <first contributor>` when there is one. The first contributor is the first author by
`order`, else the first credited name of any role, read from prefetched `item_names`. A name shows
its `family`, else its `literal`. The fields' `label_from_instance()` returns it, and the search
view uses it, so a chosen reference reads the same before and after saving.

### P-3 — The widget draws only the chosen options

`ItemSearchSelect(mvp_forms.widgets.TomSelect)` and `ItemSearchSelectMultiple(ItemSearchSelect,
TomSelectMultiple)`. **`optgroups()` never iterates `self.choices`**, which would run the field's
whole queryset and label every reference. It builds the chosen options from one query for the
selected primary keys alone, with `item_dates` and `item_names__name` prefetched, labelled with
`item_label`. Values the primary key field's `to_python` refuses (a submitted `abc`) are dropped
before the query. The lookup goes through `Item.objects`, not the restricted queryset, so a record
linked outside its picker's restriction opens showing that reference. Validation on submit stays
Django's, against the field's own queryset, so saving it unchanged is still refused. `build_attrs()` adds
`data-search-url` (`reverse("literature:item-search")`, resolved at render, so the mount prefix
never matters) and, for a restricted field, `data-search-key`. `Media` adds
`literature/picker.js` after mvp-forms' own script. The multiple widget defaults to
`remove_button=True`.

### P-4 — The script

`picker.js` listens for `mvp-forms:tomselect`, ignores selects without `data-search-url`, and sets
on the instance: `valueField: "value"`, `labelField: "text"`, `searchField: []`, a `score` function
that keeps every option the server returned, `shouldLoad` true for any non-empty text, and `load`,
which fetches `<url>?q=<text>[&key=<key>]` and passes `results` to the callback. Before each load it
clears options that are not chosen, and resets the control's record of queries it has loaded, so
stale matches do not linger and retyping an earlier search loads it again. A failed fetch calls the
callback with nothing.

### P-5 — A restricted picker carries a signed key to its queryset

One class in `picker.py`, `SearchRestriction`, holds both directions as classmethods and has no
base class: `key_for(queryset)` and `queryset_for(key)`. The widget calls the first, the search
view the second.

The widget reads the restriction from `self.choices.queryset` at render, so a queryset assigned in
a form's `__init__` is the one used. When it has filters (`queryset.query.has_filters()`), the key
is a digest of the model label and the query's SQL and parameters, so one restriction has one key,
and `key_for` stores the queryset's `query` in the default cache under `literature:picker:<digest>`
for a day, refreshed on every render. The key on the select is that digest, signed with
`django.core.signing` (salt `literature.picker`), so a malformed key is refused before the cache is
touched. An absent key searches the whole catalogue. A key that fails to unsign, or whose entry is
not in the cache, answers 404 with empty results, never the whole catalogue. Nothing unpickled ever
comes from the request.

### P-6 — Inline formsets

Nothing of our own. mvp-forms' observer starts each added select, which sends the event the script
listens for. A test asserts each rendered row's select carries its own `data-search-url`, and the
headless check adds a row and searches it.

### P-7 — On a model form, the picker is named through `Meta.field_classes`

A field declared on a `ModelForm` is used as written, so a declared `ItemChoiceField()` would be
required whatever the model field's `blank` says and would drop its `limit_choices_to`. The how-to
names the picker through `Meta.field_classes = {"reference": ItemChoiceField}`, still one line,
which makes Django build it from the model field. On a plain `Form` it is declared as usual.

### P-8 — Order of the stories

US2 and US3 both build on US1's module, test module and docs page, so the stories run in order
US1, US2, US3, each from the previous story's commit.

## Complexity Tracking

| Addition | Why it is needed |
|---|---|
| The cache key for restricted pickers | FR-013 requires the search to offer only the restriction. A query string cannot carry a queryset, and one URL per restriction breaks SC-001. Unrestricted pickers, the common case, do without it. |

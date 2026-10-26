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
docs/choosing-a-reference.md      # NEW how-to, added to the Getting Started toctree
README.md, CHANGELOG.md, CONTEXT.md
tests/test_ui/test_picker.py      # NEW, mirrors picker.py
tests/test_ui/test_views.py       # + the search view
```

## Design decisions

### P-1 — The search answers `{"results": [{"value", "text"}]}`, 20 at most

`ItemSearchView(View)` with `get()` only. Text from `?q=`, stripped. Empty text → empty results.
Matching and ranking as research R3. Prefetch `item_dates` and `item_names__name`. The bound is a
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
TomSelectMultiple)`. `optgroups()` keeps only options whose value is selected. `build_attrs()` adds
`data-search-url` (`reverse("literature:item-search")`, resolved at render, so the mount prefix
never matters) and, for a restricted field, `data-search-key`. `Media` adds
`literature/picker.js` after mvp-forms' own script. The multiple widget defaults to
`remove_button=True`.

### P-4 — The script

`picker.js` listens for `mvp-forms:tomselect`, ignores selects without `data-search-url`, and sets
on the instance: `valueField: "value"`, `labelField: "text"`, `searchField: []`, a `score` function
that keeps every option the server returned, `shouldLoad` true for any non-empty text, and `load`,
which fetches `<url>?q=<text>[&key=<key>]` and passes `results` to the callback. Before each load it
clears options that are not chosen, so stale matches from the last search do not linger. A failed
fetch calls the callback with nothing.

### P-5 — A restricted picker carries a signed key to its queryset

When the field's queryset has filters (`queryset.query.has_filters()`), the widget is given a key
on first render: `secrets.token_urlsafe()`, the queryset's `query` stored in the default cache under
`literature:picker:<key>` for a day, and the key signed with `django.core.signing` (salt
`literature.picker`). The view unsigns it, loads the query into `Item.objects.none()`'s queryset,
and searches that. An absent key searches the whole catalogue. A key that fails to unsign or is
not in the cache answers 404 with empty results, never the whole catalogue. Restriction on submit
needs nothing new: the field validates against its own queryset.

### P-6 — Inline formsets

Nothing of our own. mvp-forms' observer starts each added select, which sends the event the script
listens for. A test asserts each rendered row's select carries its own `data-search-url`, and the
headless check adds a row and searches it.

## Complexity Tracking

| Addition | Why it is needed |
|---|---|
| The cache key for restricted pickers | FR-013 requires the search to offer only the restriction. A query string cannot carry a queryset, and one URL per restriction breaks SC-001. Unrestricted pickers, the common case, do without it. |

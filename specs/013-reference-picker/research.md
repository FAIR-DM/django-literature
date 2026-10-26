# Research — FS-013 reference picker

No `planning-notes.md` and no sketch for this feature, so the research answers the plan's own
questions against main at `dec3164`.

## R1 — What draws the control

django-mvp-forms 0.8.0, already a dependency of the `ui` extra, ships `TomSelect` and
`TomSelectMultiple` widgets (`mvp_forms/widgets.py`) and the script that starts them
(`mvp_forms/static/mvp_forms/tomselect.js`). The script starts a control on every
`select[data-tom-select]` on the page, including selects added later (a `MutationObserver`), and
sends `mvp-forms:tomselect` with the Tom Select instance once each control has started.

The package already extends that control once: `literature/ui/static/literature/creatable.js`
listens for the event and changes the instance's settings for selects marked `data-create`. The
picker's script does the same for selects marked with a search address: it gives the instance a
`load` function that fetches matches from the search route, turns off Tom Select's own client-side
filtering and scoring (the server has already matched and ranked), and clears the options between
searches. Rows an inline formset adds after the page has loaded are started by the same observer,
so FR-011 needs nothing of its own.

**Decision:** subclass `mvp_forms.widgets.TomSelect` and `TomSelectMultiple`, mark the select with
`data-search-url`, and add one small script in the pattern of `creatable.js`.

## R2 — Which options the select holds

A `ModelChoiceField`'s `Select` draws every row of its queryset as an `<option>`. That is the
problem this feature removes, so the widget draws only the chosen value or values. The field still
validates the submitted primary key against its full queryset, so a submission is checked exactly
as Django checks any choice field (FR-013, the deleted-reference case, and the no-script case all
fall out of this).

**Decision:** the widget overrides `optgroups()` to draw options only for the selected values,
labelled with the field's `label_from_instance()`.

## R3 — The search route

The catalogue's routes live in `literature/ui/urls.py` under the `literature` namespace. A route
named `literature:item-search` returning JSON is located by `reverse()`, so the mount prefix never
matters (FR-009). The catalogue list is open to everyone (ADR 0036, `ItemListView` declares no
permission), so the search view declares none either (FR-010).

Response: `{"results": [{"value": <pk>, "text": <label>}, …]}`, at most 20 entries.

Matching (FR-004, FR-005), case-insensitive, any one of:

- `title__icontains`
- `citation_key__icontains`
- `item_names__name__family__icontains`
- `item_names__name__literal__icontains`
- a DOI identifier (`item_identifiers__type="DOI"`) whose value contains the typed text with any
  `https://doi.org/`, `http://dx.doi.org/` or `doi:` prefix removed

Ranking (FR-007): an annotation that is 0 when `title` or `citation_key` starts with the text and 1
otherwise, then title. `.distinct()` because the name joins multiply rows, as
`ItemFilterSet.filter_queryset()` already does for the same reason.

**What already exists for this:** `mvp.filters.SearchFilter` matches *any word of the term* across
fields. That is the catalogue page's semantics and the wrong one here: typing "Smith 2021" into a
picker should narrow, not widen. The search is a short queryset in the view, not a reuse of the
filter.

## R4 — How a restricted picker's search knows its restriction

The field's `queryset` is the restriction (FR-012). Validation on submit is Django's own and needs
nothing. The search route, though, is shared by every picker in the project and has to know which
queryset to search.

Prior art:

- **django-select2** (`ModelSelect2Widget`) stores the widget's queryset in Django's cache under a
  signed key written on the select, and its view reads it back.
- **django-autocomplete-light** needs one view and one URL per restriction, written by the developer.
- **django-tomselect** registers named autocomplete views, again one per restriction.

The second and third make a restricted picker something the developer wires up, which SC-001 rules
out. The first is the established mechanism that keeps a field declaration self-contained.

The cache matters for deployments: Django's default `LocMemCache` is per process, so a key stored
by one worker is unknown to another. That must not break the common case, so:

- **An unrestricted picker** (`queryset` is every `Item`) sends no key and searches the whole
  catalogue. It needs no cache at all.
- **A restricted picker** stores its queryset's `query` in the default cache under a random key,
  signed onto the select as `data-search-key`. The search view resolves it and searches only that
  queryset.
- **A key the view cannot resolve** (tampered, expired, or stored by another process's local
  memory) returns an empty result with status 404, never the unrestricted catalogue. The picker
  then offers nothing rather than offering too much.
- The installation docs say a restricted picker needs a cache shared between processes in
  production.

**Decision:** adopt django-select2's mechanism for restricted pickers only. Querysets are stored
with `pickle`, server-side, as django-select2 does. Nothing unpickled ever comes from the request.

## R5 — The option label (FR-006)

`Item.year` (added in #159) reads prefetched `item_dates`. The first contributor is the first
`ItemName` by role then `order`, preferring `author`. A label reads title, then year in
parentheses, then the first contributor's family or literal name, omitting what is missing, and
falling back to the citation key with no title. Both the search route and the widget's chosen
options use the same function, so a choice reads the same before and after saving.

Queries: the search prefetches `item_dates` and `item_names__name`, so labelling 20 results costs a
fixed number of queries.

## R6 — Tom Select itself

The library is not bundled. The catalogue's own form page loads Tom Select 2.5.2 from jsDelivr with
SRI hashes in its `head` block (`item_form.html`). A host project's form page must load it too, or
the picker stays a select holding only the chosen reference. Putting it in the widget's `Media`
would lose the SRI hashes and load it twice on a page that also links it.

**Decision:** follow the catalogue's own precedent. The docs give the two tags to add to the page,
copied from `item_form.html`. SC-001 says "no view, URL or JavaScript of their own", and adding
two published tags is neither.

## What already exists

| New piece | Where the search stopped |
|---|---|
| Searchable select control | installed package: `mvp_forms.widgets.TomSelect`, `TomSelectMultiple` |
| Starting controls on new formset rows | installed package: `mvp_forms/static/mvp_forms/tomselect.js` |
| Remote loading of options | installed package: Tom Select's own `load` setting, via the existing `mvp-forms:tomselect` event (pattern: `literature/ui/static/literature/creatable.js`) |
| Validating a submitted choice against a restriction | Django: `ModelChoiceField`, `ModelMultipleChoiceField` |
| Year of a reference | this repo: `Item.year` |
| Search route | new code: one view and one route in `literature/ui/` |
| Option label | new code: one function, shared by view and widget |
| Restricted-search key | new code, following django-select2's cache mechanism |
| Picker script | new code: one file of about 40 lines beside `creatable.js` |

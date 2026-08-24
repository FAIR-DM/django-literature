# `literature.ui`

The views a project routes to, and the search and filter definition behind them.

## `literature.ui.filters`

One module declares what the catalogue is searchable and filterable by, so both the
table and the card presentation narrow to the same set of references.

- `SEARCH_FIELDS` — the ORM paths a search matches: citation key, the three title
  fields, container title, and every credited contributor's family, given and literal
  name. Both views assign it to their own `search_fields`.
- `ItemFilterSet` — the four filters: item type, contributor, language and issued
  year. It lists every filter explicitly and pins `Meta.fields` to an empty list, so
  nothing is generated over fields the catalogue does not filter on.
- `LanguageFilter` — offers the language values the catalogue actually holds, read
  from stored data on each request rather than from a fixed list a project has to keep
  in step.
- `annotate_issued` — annotates a queryset with `issued`, taken from the issued date
  slot. The year filter narrows on it and the table sorts on it.
- `get_active_filters` — the filters in force on a request, which both views report to
  their template so a narrowed catalogue can say what narrowed it.
- `ScalarOrListSelectMultiple` — the item-type widget. It accepts either one stored
  value or several, so choosing two types widens the result to either of them.

To change what a project's catalogue filters on, subclass `ItemFilterSet` and point
both views at the subclass.

Two decisions behind this module are recorded as ADRs: why the searched fields carry
no database index ([ADR 0024](../adr/0024-the-catalogue-search-adds-no-index.md)),
and why the search and filter definition lives in exactly one place
([ADR 0025](../adr/0025-one-definition-of-what-the-catalogue-narrows-by.md)).

```{eval-rst}
.. automodule:: literature.ui.filters
   :members:
   :undoc-members: False
   :show-inheritance:
```

## `literature.ui.views`

`ItemTableView` serves the catalogue as a table and `ItemListView` serves it as cards.
Either can back the catalogue route, chosen through the `LITERATURE` settings key
described in the README.

`CatalogueListMixin` carries the card configuration that `ItemListView` and
`ContributorDetailView` share — the model, the card template, the page title and the
prefetching a row needs. The contributor page composes it without the search box and
filters, which belong to the catalogue alone.

```{eval-rst}
.. automodule:: literature.ui.views
   :members:
   :undoc-members: False
   :show-inheritance:
```

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

`ItemImportView` serves the import page, reached from the Import action on either
catalogue presentation. It renders the format choice and file control on a `GET`. On a
valid `POST` it runs the chosen format over the uploaded file and renders the report
directly rather than redirecting — as a preview by default, which reports every entry
and leaves the catalogue untouched, or as a real import where the reader ticked the
skip-preview control.

`ItemImportConfirmView` carries out the import a preview described. It takes no file and
no token from the page: both come from the reader's own session, so a request can only
confirm a file that same session staged. A `GET` has nothing to show without a prior
preview and redirects back to the import page.

See [Importing a bibliography file](../importing-through-the-interface.md) for what a
reader sees.

```{eval-rst}
.. automodule:: literature.ui.views
   :members:
   :undoc-members: False
   :show-inheritance:
```

## `literature.ui.forms`

`ImportForm` is the format choice, file control and skip-preview checkbox the import page renders
— a plain `forms.Form`, not a `ModelForm`, since nothing on it maps to `Item` directly. The format
resolves the file into entries and the entries into items, never this form. Its format choices are
read from `available_formats()` when the form is instantiated, not when the class is defined, so a
format configured after import time still appears. The skip-preview checkbox is unticked by
default, so a plain submission previews rather than imports. `ItemForm` is the
one write form every create and update page shares — see the README's "Adding, editing and
removing a reference" section for what it does.

`ConfirmImportForm` declares no field at all. It exists so that carrying out a previewed
import is a `POST` protected against cross-site request forgery like any other, and
nothing more: the staged file and the format it was staged as are read from the session,
never posted back.

```{eval-rst}
.. automodule:: literature.ui.forms
   :members:
   :undoc-members: False
   :show-inheritance:
```

## `literature.ui.staging`

`StagedUpload` holds an uploaded file between a preview and the confirmation that carries
it out, since a browser will not re-populate a file input and asking for the file again
would defeat the point of previewing. It saves through Django's storage API, so a project
already configuring remote storage gets staging on it without further work, and it names
each file by a random token that carries no relationship to the file's own name or
contents.

Four operations: `save` stages a file and returns its token, `open` reads it back or
returns `None` where the token names nothing staged, `discard` removes it once the import
it was staged for has run, and `sweep` removes anything left behind by a preview that was
never confirmed. `RETENTION_WINDOW` is how long an abandoned staging survives a sweep,
24 hours by default.

Which reader staged which file is deliberately not this class's concern — the token lives
in the session, held by the view.

```{eval-rst}
.. automodule:: literature.ui.staging
   :members:
   :undoc-members: False
   :show-inheritance:
```

## `literature.ui.importing`

`ImportReport` turns one `ImportResult` into what the import report page renders — `rows`, one
`ImportReportRow` per entry in source order, plus the same `created`, `skipped`, `failed` and
`total` counts the result already carries. `ImportReportRow` is the frozen row itself: a position
numbered from one, the entry's outcome, its citation key where the source supplies one, its reason
where it has one — a failure's, or a skip's own reason for what it recognised and set aside —
and the URL of the reference it created where it created one.

```{eval-rst}
.. automodule:: literature.ui.importing
   :members:
   :undoc-members: False
   :show-inheritance:
```

## `literature.ui.tables`

`ItemTable` is the catalogue's table presentation — the columns `ItemTableView` renders,
and the ordering it sorts by.

`ImportReportTable` renders an import report's rows. It takes a plain list rather than a
queryset, since a report is built from one import's result and never queried. Its outcome column
renders each row's outcome as a colour-coded badge, created, skipped and failed each their own
variant. A created row's position number links to the reference it produced, and a skipped or
failed row's does not.

```{eval-rst}
.. automodule:: literature.ui.tables
   :members:
   :undoc-members: False
   :show-inheritance:
```

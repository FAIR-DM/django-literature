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
valid `POST` it stages the uploaded file and redirects to the preview. Where the reader
ticked the skip-preview control it instead runs the chosen format immediately and
renders the report in that same response, which is the only path that still does.

`ItemImportPreviewView` serves the preview at an address of its own. It holds no result:
every `GET` reads the staged file back and runs the format over it again with
`dry_run=True`, so reloading the address reports the same outcomes and writes nothing
either time. It carries no import form. The rows it hands the table each carry the
outcome the filter below matches on, and the counts it renders above the table come
straight off the report, so narrowing the table never changes them. Reaching the address
with nothing staged sets `nothing_staged` in the context and renders a notice rather than
raising.

`ItemImportRestartView` discards the staged file, clears what the session held about it,
and redirects to an empty import form. It answers `POST` only.

`ItemImportConfirmView` carries out the import a preview described, then redirects to the
catalogue with a message stating the counts. It renders no template of its own and there
is no success page: the per-entry detail was on the preview, and the message here
confirms what that preview said would happen. It takes no file and no token from the
page, both coming from the reader's own session, so a request can only confirm a file
that same session staged. A confirmation naming a preview the session has since replaced,
or one whose file is gone, returns to the catalogue with a message saying there was
nothing to confirm and imports nothing. A `GET` has nothing to show without a prior
preview and redirects back to the import page.

The routes these views are reachable at, all within the `literature` namespace:

- `literature:item-import` — the format choice and file control.
- `literature:item-import-preview` — the preview page.
- `literature:item-import-restart` — discard the staged file and start again.
- `literature:item-import-confirm` — carry out the previewed import.

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

`ConfirmImportForm` names nothing the staged file can be found by. The file and the format it
was staged as are read from the session, never posted back. Its one hidden field names which
preview the page was describing, which is checked against the confirming session's own value —
a page still showing a preview that has since been replaced confirms nothing rather than
carrying out the later one. Carrying out a previewed import is a `POST` protected against
cross-site request forgery like any other.

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

The preview builds the same table with per-row attributes, one expression per row naming that
row's outcome, which is what lets the filter above the table hide rows without a request. The
one-step report builds it without them, so its rows carry nothing that would need a filter on the
page to make sense of.

`OutcomeColumn` is that column. It is a template column, so the badge is rendered by a template
and escaped like any other, rather than built as a marked-safe string in Python. It maps each
outcome to its own badge variant and wraps the outcome's own translated label, which is what the
cell carried before it was a badge — the colour is added to the label, never substituted for it.
The mapping is a class attribute, `VARIANTS`, so a project that renders the report itself can
subclass the column and map the three outcomes to different variants.

```{eval-rst}
.. automodule:: literature.ui.tables
   :members:
   :undoc-members: False
   :show-inheritance:
```

## Components

`<c-filter>` is the outcome filter above the preview's table. It takes one attribute,
`outcomes`, a sequence of value and label pairs, and renders a radio button per outcome
plus a reset back to all of them. Choosing one writes the value into `outcome` on the
surrounding scope, which every table row reads to decide whether to show itself, so
narrowing the table issues no request and reloads nothing.

The component opens no scope of its own and wraps itself in no form, both deliberately: it
reads and writes the scope the page around it opens, and it has no server to submit to.
Anything on a page that reads `outcome` narrows with it, and the counts the preview renders
above it do not read it, which is what keeps them describing the whole file while the table
beneath shows part of one.

A project rendering its own import report can use the component the same way, by opening a
scope holding `outcome` and giving its rows something that reads it.

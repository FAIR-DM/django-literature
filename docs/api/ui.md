# `literature.ui`

The views a project routes to, and the search and filter definition behind them.

## `literature.ui.filters`

One module declares what the catalogue is searchable and filterable by, so both the
table and the card presentation narrow to the same set of references.

- `SEARCH_FIELDS` — the ORM paths a search matches: citation key, the three title
  fields, container title, every credited contributor's family, given and literal
  name, and every identifier's value. `ItemFilterSet.q` searches them with
  `CatalogueSearchFilter`, django-mvp's `SearchFilter` reading each word as a DOI would be
  stored. The catalogue and the reference picker's autocomplete view share it.
- `ItemFilterSet` — the search and the three filters: item type, issued year and
  language. It lists every filter explicitly and pins `Meta.fields` to an empty list,
  so nothing is generated over fields the catalogue does not filter on. A contributor
  is found through the search, which matches every credited name.
- `ItemTableFilterSet` — `ItemFilterSet` plus a hidden `sort` field that carries the
  table's column order through the filter form, so applying a filter keeps the sort.
- `LanguageFilter` — offers the language values the catalogue actually holds, read
  from stored data on each request rather than from a fixed list a project has to keep
  in step.
- `YearFilter` — offers the years the catalogue's issued dates fall in, newest first,
  read from stored data on each request. Its field, `YearChoiceField`, still accepts a
  year that is not on offer, so an old address carrying one narrows to nothing rather
  than being ignored.
- `annotate_issued` — annotates a queryset with `issued`, taken from the issued date
  slot. The year filter narrows on it and the table sorts on it.
- `TypeFilter` — the item-type filter, any of several types. Its field,
  `TypeChoiceField`, declares `ScalarOrListSelectMultiple` as its own default widget,
  which is what lets django-mvp's toolbar draw it as a checkbox dropdown.
- `ScalarOrListSelectMultiple` — the item-type widget. It accepts either one stored
  value or several, so choosing two types widens the result to either of them.

To change what a project's catalogue filters on, subclass `ItemFilterSet` and
`ItemTableFilterSet` (or only the one whose view the project uses) and set the
subclass as the view's `filterset_class`.

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

## `literature.ui.picker`

The reference picker for a project's own forms. `ReferenceField` chooses one reference and
`ReferenceMultipleField` chooses several. Both are django-tomselect model fields whose default
configuration points at the catalogue's autocomplete route, `literature:item-autocomplete`. A `config` passed to
either is merged over that default. Both inherit that default and the restriction check from
`ReferencePickerMixin`, which is not used on its own. They also refuse a chosen reference outside the configuration's
constant `filter_by` and `exclude_by` conditions. `item_label` names a reference the same way in the
control and in the search results: its title or citation key, its year and its first contributor.
How to use them is in
[How to choose a reference in your own form](../how-to/choosing-a-reference.md).

```{eval-rst}
.. automodule:: literature.ui.picker
   :members:
   :undoc-members: False
   :show-inheritance:
```

## `literature.ui.views`

`ItemTableView` serves the catalogue as a table and `ItemListView` serves it as cards.
Either can back the catalogue route, chosen through the `LITERATURE` settings key
described in the README — see [ADR 0033](../adr/0033-the-catalogue-view-is-chosen-by-a-setting.md)
for why the choice is made this way rather than by routing.

`ReferenceAutocompleteView` is a django-tomselect `AutocompleteModelView` that answers the
reference picker's searches as JSON, at most `SEARCH_LIMIT` references at a time, each with its `id`
and `label`, under the route name `literature:item-autocomplete`. It is open to everyone, like the
catalogue list. Text containing a NUL character answers 400. No text answers the first page of
the catalogue by title.

`CatalogueListMixin` carries the card configuration that `ItemListView` and
`ContributorDetailView` share — the model, the card template, the page title and the
prefetching a row needs. The contributor page composes it without the search box and
filters, which belong to the catalogue alone.

`ItemTableView` draws the search box and every filter in its toolbar, and leaves out a
choice filter the catalogue holds nothing for, such as Language when no reference
records one. Its template, `literature/ui/item_table_page.html`, redraws django-mvp's
toolbar row to put Import at the end of it, since django-mvp offers no block in that row
(django-mvp/django-mvp#579). `ItemListView` renders django-mvp's list page as it ships,
with the filters in a drawer opened from the toolbar at every screen width.

`ItemImportView` serves the import page, reached from the Import action on the table
catalogue. It renders the format choice and file control on a `GET`. On a
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

### Permissions

Every view that changes the catalogue uses Django's `PermissionRequiredMixin`, with
`permission_required` set to one of three module constants
([ADR 0036](../adr/0036-writing-asks-for-a-model-permission.md)):

| Views | Constant | Permission |
|---|---|---|
| `ItemCreateView`, and the four import views | `ADD_PERMISSION` | `literature.add_item` |
| `ItemUpdateView` | `CHANGE_PERMISSION` | `literature.change_item` |
| `ItemDeleteView` | `DELETE_PERMISSION` | `literature.delete_item` |

The list, detail and contributor views check nothing. Their Add, Import, Edit and Delete
actions are drawn through `HasPermission`, a callable `show_<action>_action` flag that
django-mvp calls with the request user, so a user sees only the actions their
permissions open. To apply a different rule, subclass the view and set
`permission_required`, or override `has_permission()`:

```python
from literature.ui.views import ItemDeleteView


class StaffOnlyDeleteView(ItemDeleteView):
    def has_permission(self):
        return self.request.user.is_staff
```

```{eval-rst}
.. automodule:: literature.ui.views
   :members:
   :undoc-members: False
   :show-inheritance:
```


The write pages hand their template `form_problems()`: every error on the form and its sets, in
page order, each with the id of the field to fix, for the summary drawn above the tabs.

## `literature.ui.fields` and `literature.ui.links`

The reference page, `ItemDetailView`, reads its content from two small modules, and from
`Item.year` and `Item.doi_url` on the model.

`field_sections` returns the fields a reference carries, grouped under the same headings
the edit form uses (see [Field groups](../field-groups.md)), in the same order. Each
section is a dict of `label` and `rows`, a row being a label and value pair. A field
holding nothing is left out, and so is a group left with no rows. The four fields the
page shows in its header, the type, citation key, title and abstract, are never repeated
in a section.

`web_url` returns a stored identifier as a link target only when it is an `http` or
`https` address, so a value such as `javascript:` is shown as text and never followed. A
DOI stored without its resolver is linked through `literature.utils.doi.doi_url` instead.

```{eval-rst}
.. automodule:: literature.ui.fields
   :members:
   :undoc-members: False

.. automodule:: literature.ui.links
   :members:
   :undoc-members: False
```

## `literature.ui.forms`

`ImportForm` is the format choice, file control and skip-preview checkbox the import page renders
— a plain `forms.Form`, not a `ModelForm`, since nothing on it maps to `Item` directly. The format
resolves the file into entries and the entries into items, never this form. Its format choices are
read from `available_formats()` when the form is instantiated, not when the class is defined, so a
format configured after import time still appears. The skip-preview checkbox is unticked by
default, so a plain submission previews rather than imports. `ItemForm` is the
one write form every create and update page shares — see the README's "Adding, editing and
removing a reference" section for what it does. Besides every scalar field of `Item`, it declares one date field per CSL date slot, named by
`date_field_name()` in the order `DATE_SLOTS` gives, and writes each slot's `ItemDate` when it
saves. `StoredPartialDateField` shows a stored partial date as the text it saves as.
`KeywordsField` takes keywords as tags and stores them as the one comma-separated string CSL JSON
keeps, offering every keyword the catalogue already uses through `keyword_choices()`.
`ItemIdentifierForm` takes its identifier type through an `OpenChoiceField`, which accepts a type
outside its choices. `CreatableSelect` and `CreatableSelectMultiple` are the Tom Select controls
that let a person type a value in beside the choices offered.

## `literature.ui.formlayout`

`ItemFormLayout` builds the write form's crispy layout: the four tabs, the type-scoped sections in
`SECTION_ORDER`, the dates and the contributor sets. Each section, date slot and role set is shown
or hidden in the browser by the condition `shown_when()`, `date_shown_when()` or
`role_shown_when()` writes for it, and `rows_of()` lays a run of fields out in equal columns. `TYPE_CHOICE_GROUPS` sorts the 45 item types
into the groups the type control offers them in, and `FIELD_LABELS` and `FIELD_HELP` hold the copy
a person reads in place of the model's own CSL notes. The contributor sets themselves are
`CONTRIBUTOR_INLINES` in `literature.ui.inlines`, one per role in `ROLE_ORDER`, and which roles each
type leads with is `TYPE_ROLES` in `literature.ui.fieldgroups`.

```{eval-rst}
.. automodule:: literature.ui.formlayout
   :members:
   :undoc-members: False
```

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
`outcomes`, a sequence of value, label and variant triples, and renders a radio button per
outcome plus a reset back to all of them. Choosing one writes the value into `outcome` on the
surrounding scope, which every table row reads to decide whether to show itself, so
narrowing the table issues no request and reloads nothing.

The variant is the badge variant that outcome already uses, passed in rather than decided
here, so a button and the badges it will leave behind carry the same colour. A project that
subclasses `OutcomeColumn` to remap the outcomes moves the filter with it and cannot end up
with the two disagreeing. The reset carries no outcome's colour, because it names no outcome.

The component opens no scope of its own and wraps itself in no form, both deliberately: it
reads and writes the scope the page around it opens, and it has no server to submit to.
Anything on a page that reads `outcome` narrows with it, and the counts the preview renders
above it do not read it, which is what keeps them describing the whole file while the table
beneath shows part of one.

A project rendering its own import report can use the component the same way, by opening a
scope holding `outcome` and giving its rows something that reads it.

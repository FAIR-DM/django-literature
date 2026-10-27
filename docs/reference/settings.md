# Settings

django-literature reads one Django setting, `LITERATURE`, a dict whose keys are listed below. Every
key is optional.

```python
# settings.py
LITERATURE = {
    "BIB_FORMATS": [
        "literature.importers.bibtex.BibTeXFormat",
        "literature.importers.ris.RISFormat",
        "myproject.formats.EndNoteXMLFormat",
    ],
    "CATALOGUE_VIEW": "literature.ui.views.ItemListView",
}
```

`LITERATURE` itself must be a dict. Anything else raises `ImproperlyConfigured`.

## `BIB_FORMATS`

- **Type:** a list or tuple of dotted paths to `BibFormat` subclasses.
- **Default:** `["literature.importers.bibtex.BibTeXFormat", "literature.importers.ris.RISFormat"]`.
- **What it does:** declares the file formats the installation can import, through
  `literature.importers.available_formats()` and `get_format()` and on the front end's import form.
  Setting it replaces the default list, so a project that adds a format and keeps BibTeX and RIS
  lists all three.
- **What it accepts:** each path must import to a `BibFormat` subclass with a `name`. Paths are
  resolved on first read and cached. A path that does not import, or imports to something else,
  raises `ImproperlyConfigured` naming it, and so does a format that leaves a stage unimplemented
  or sets no `name`. A single path not wrapped in a list also raises `ImproperlyConfigured`.

## `CATALOGUE_VIEW`

- **Type:** a dotted path to a class-based view.
- **Default:** `"literature.ui.views.ItemTableView"`, the catalogue as a table.
- **What it does:** chooses the view the catalogue route, `literature:item-list`, serves. The other
  routes are unaffected. Requires the `literature.ui` app.
- **What it accepts:** `literature.ui.views.ItemListView` for the catalogue as cards, or a subclass
  of either view. It is read on each request. A path that is not a string, does not import, or is
  not a class-based view raises `ImproperlyConfigured` naming it.

# Importing

Django Literature imports references from CSL JSON, BibTeX and RIS. CSL JSON is read by the
converters, record by record. BibTeX and RIS files are read by import formats, which report what
happened to every entry, and can be run from code or from the front end's import page. New formats
can be added.

## Import CSL JSON

Pass a record to `from_csl_json()`:

```python
from literature.converters import from_csl_json

csl = {
    "id": "Jennings2019",
    "type": "article-journal",
    "title": "A new compositionally based thermal conductivity model",
    "author": [
        {"family": "Jennings", "given": "S"},
        {"family": "Hasterok", "given": "D"},
    ],
    "issued": {"date-parts": [[2019, 8, 16]]},
    "DOI": "10.1093/gji/ggz376",
}

item = from_csl_json(csl)
```

To give the new item a primary key it already had elsewhere, as when moving references from
another store, pass `pk`:

```python
item = from_csl_json(csl, pk=42)
```

Each record is stored with its contributors, dates and identifiers in one transaction, so a record
that fails stores nothing. `from_csl_json()` raises `ValidationError` when:

- `type` is absent or not a known CSL item type,
- both `citation-key` and `id` are absent or blank,
- an identifier value fails its format check, such as a malformed DOI.

```python
from django.core.exceptions import ValidationError

try:
    item = from_csl_json({"type": "article-journal"})  # no id or citation-key
except ValidationError as exc:
    print(exc.message_dict)
```

To import a list, pass it to `from_csl_json_list()`. It skips a record it cannot store, logs a
warning for it, and returns the items it did store:

```python
import json

from literature.converters import from_csl_json_list

with open("references.json") as f:
    items = from_csl_json_list(json.load(f))
```

The citation key is stored as given, even when another reference already has it. See
[Citation keys](topics/citation-keys.md).

## Import a bibliography file in code

Look the format up by name with `get_format()`, then import the file. Rehearse first with
`dry_run=True`: every stage runs and nothing is written.

```python
from literature.importers import get_format

with open("library.bib") as handle:
    preview = get_format("bibtex")().import_file(handle, dry_run=True)

if preview.ok:
    with open("library.bib") as handle:
        result = get_format("bibtex")().import_file(handle)
```

Every entry the file held is in the result, under `created`, `skipped` or `failed`. One unreadable
entry does not stop the rest of the file:

```python
print(f"{len(result.created)} stored, {len(result.failed)} could not be read")

for entry in result.failed:
    label = entry.handle or f"entry {entry.index}"
    print(f"  {label}: {entry.reason}")
```

A name that is not configured raises `UnknownFormat`. How BibTeX and RIS fields land in the models
is listed in the [BibTeX mapping](../reference/bibtex-mapping.md) and the
[RIS mapping](../reference/ris-mapping.md).

## Import a bibliography file from the front end

With the front end installed, people holding the `literature.add_item` permission can import from
the catalogue:

1. On the table catalogue, choose **Import** at the end of the toolbar.
2. Choose the file's format, attach the file, and submit. The format is chosen, never worked out
   from the file.
3. Read the preview. It lists every entry with what would happen to it: created, skipped or failed,
   with a reason for each skip and failure. Choose an outcome's button above the table to see only
   those entries.
4. Choose **Confirm import**, or **Restart import** to start again with another file.

Tick "Skip the preview and import immediately" at step 2 to import in one step. You return to the
catalogue with a message saying how many entries were created, skipped and failed.

Nothing checks whether a file has already been imported, so importing the same file twice creates
its references twice. The card catalogue has no Import action, so a project serving the catalogue
as cards links to the `literature:item-import` route from its own navigation. Every page and
control is described in [Import pages](../reference/import-pages.md).

## Add an import format

1. Subclass `BibFormat`, and give it a `name` and a `label`:

   ```python
   from django.utils.translation import gettext_lazy as _

   from literature.importers import BibFormat, SkipEntry


   class EndNoteXMLFormat(BibFormat):
       name = "endnote-xml"
       label = _("EndNote XML")

       def parse(self, file):
           yield from iter_records(file)

       def handle_for(self, raw):
           return raw.label

       def to_csl_json(self, raw):
           if raw.is_note:
               raise SkipEntry(_("not a bibliographic entry"))
           return csl_json_from_record(raw)
   ```

   `parse()` yields the file's entries one at a time, and `to_csl_json()` turns one entry into a
   CSL JSON record. `handle_for()` is optional: override it when entries have names of their own,
   such as a cite key. Raise `SkipEntry` for something recognised that is not a reference, and
   `EntryError` for an entry that cannot be read.

2. Add its dotted path to the `BIB_FORMATS` key of the `LITERATURE` setting. The list replaces the
   default, so keep the formats you still want:

   ```python
   # settings.py
   LITERATURE = {
       "BIB_FORMATS": [
           "literature.importers.bibtex.BibTeXFormat",
           "literature.importers.ris.RISFormat",
           "myproject.formats.EndNoteXMLFormat",
       ],
   }
   ```

`get_format("endnote-xml")` now returns the class, and the import page offers its label. The
format gets the whole workflow from `BibFormat`: the loop, the per-entry transaction, the dry run
and the report. Each step is an ordinary method that can be overridden. What that takes on is
recorded in [ADR 0006](../adr/0006-an-imported-entry-is-atomic.md) and
[ADR 0007](../adr/0007-the-import-runner-catches-everything.md). The setting is described in
[Settings](../reference/settings.md), and the classes in
[`literature.importers`](../reference/api/importers.md).

# `literature.importers`

The plug-in contract for importing bibliographic files. Every `BibFormat` runs through the same
fixed workflow and returns one outcome per entry the file contained. How to run an import is in
[How to import a bibliography file in code](../../how-to/import-a-bibliography-file-in-code.md),
and how to add a format is in [How to add an import format](../../how-to/add-an-import-format.md).
Which formats an installation can read is the `BIB_FORMATS` key of the
[`LITERATURE` setting](../settings.md).

## Discovering the configured formats

```python
from literature.importers import available_formats, get_format
from literature.importers.exceptions import UnknownFormat

for name, format_class in available_formats().items():
    print(name, "—", format_class.label)

try:
    get_format("bibtex")
except UnknownFormat as exc:
    print(exc)  # "No import format named 'bibtex'. No import formats are configured."
```

## Exceptions

| Exception | Raised by | Meaning |
|---|---|---|
| `SkipEntry` | a format, from `to_csl_json` | Recognised, not a bibliographic record. Becomes `SKIPPED` |
| `EntryError` | a format, from `parse` or `to_csl_json` | This entry is bad. Becomes `FAILED` with its reason |
| `ParseError` | a format, from `parse` | The file cannot be read at all. Becomes a one-entry failed result |
| `UnknownFormat` | `get_format` | The name is not configured. Message lists the names that are. **Reaches the caller** |

`SkipEntry`, `EntryError` and `ParseError` are the format's vocabulary for talking to the workflow
and never reach the caller. `UnknownFormat` is the caller's problem and does.

## Reference

```{eval-rst}
.. automodule:: literature.importers
   :members:
   :undoc-members: False
   :show-inheritance:
```

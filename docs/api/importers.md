# `literature.importers`

The plug-in contract for importing bibliographic files. One call, `import_file`, runs any
registered `Format` through the same fixed workflow and returns one outcome per entry the file
contained. See `specs/003-import-contract/quickstart.md` for the full walkthrough and
`specs/003-import-contract/contracts/importers.md` for the signatures.

## Running an import

```python
from literature.importers import import_file

with open("library.bib") as handle:
    result = import_file(handle, format="bibtex")

print(f"{len(result.created)} stored, {len(result.failed)} could not be read")

for entry in result.failed:
    label = entry.handle or f"entry {entry.index}"
    print(f"  {label}: {entry.reason}")
```

Importing is per entry. One unreadable entry does not stop the rest of the file, and every entry
is accounted for in the result whether it was stored or not.

Rehearse it first if you like. Every stage runs, nothing is written:

```python
with open("library.bib") as handle:
    preview = import_file(handle, format="bibtex", dry_run=True)

if not preview.ok:
    print(f"{len(preview.failed)} entries need attention first")
```

## Writing a format

```python
from django.utils.translation import gettext_lazy as _

from literature.importers import Format, SkipEntry, register


@register
class BibTeXFormat(Format):
    name = "bibtex"
    label = _("BibTeX")

    def parse(self, file):
        for block in iter_bibtex_blocks(file):   # yields, one at a time
            yield block

    def handle_for(self, raw):
        return raw.cite_key

    def to_csl_json(self, raw):
        if raw.entry_type in {"comment", "string", "preamble"}:
            raise SkipEntry(_("not a bibliographic entry"))
        return csl_json_from_bibtex(raw)
```

Two stages to supply and one to override if the syntax has entry names of its own. A format has no
say in how an `Item` is built from the CSL JSON it returns, and no way to reach that stage.
Registering the same name twice raises `FormatAlreadyRegistered` rather than silently replacing
the first format.

## Discovering registered formats

```python
from literature.importers import available_formats, get_format
from literature.importers.exceptions import UnknownFormat

for name, format_class in available_formats().items():
    print(name, "—", format_class.label)

try:
    get_format("bibtex")
except UnknownFormat as exc:
    print(exc)  # "No import format named 'bibtex'. No import formats are registered."
```

The caller does not need to know what it will get back, which is the point of asking.

## Exceptions

| Exception | Raised by | Meaning |
|---|---|---|
| `SkipEntry` | a format, from `to_csl_json` | Recognised, not a bibliographic record. Becomes `SKIPPED` |
| `EntryError` | a format, from `parse` or `to_csl_json` | This entry is bad. Becomes `FAILED` with its reason |
| `ParseError` | a format, from `parse` | The file cannot be read at all. Becomes a one-entry failed result |
| `UnknownFormat` | `get_format` | The name is not registered. Message lists the names that are. **Reaches the caller** |
| `FormatAlreadyRegistered` | `register` | That name is taken |

`SkipEntry`, `EntryError` and `ParseError` are the format's vocabulary for talking to the runner
and never reach the caller. `UnknownFormat` and `FormatAlreadyRegistered` are the caller's problem
and do.

## Reference

```{eval-rst}
.. automodule:: literature.importers
   :members:
   :undoc-members: False
   :show-inheritance:
```

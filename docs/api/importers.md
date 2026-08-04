# `literature.importers`

The plug-in contract for importing bibliographic files. Every `BibFormat` runs through the same
fixed workflow and returns one outcome per entry the file contained. See
`specs/003-import-contract/quickstart.md` for the full walkthrough and
`specs/003-import-contract/contracts/importers.md` for the signatures.

## Running an import

```python
from literature.importers import get_format

with open("library.bib") as handle:
    result = get_format("bibtex")().import_file(handle)

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
    preview = get_format("bibtex")().import_file(handle, dry_run=True)

if not preview.ok:
    print(f"{len(preview.failed)} entries need attention first")
```

## Writing a format

```python
from django.utils.translation import gettext_lazy as _

from literature.importers import BibFormat, SkipEntry


class BibTeXFormat(BibFormat):
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

Two stages to supply and one to override if the syntax has entry names of its own. A format that
implements only those gets the whole workflow — the loop, the per-entry transaction, the dry run
and the report — from `BibFormat`.

The other steps (`import_file`, `import_entries`, `import_entry`, `get_result`, and the
`entry_created` / `entry_skipped` / `entry_failed` helpers) are ordinary methods. Override any of
them if your syntax needs something the default does not do. Nothing stops you, and nothing checks.
What you take on by doing it is recorded in ADR-0006 and ADR-0007.

## Declaring which formats an installation can read

```python
# settings.py
LITERATURE = {
    "BIB_FORMATS": [
        "myproject.formats.BibTeXFormat",
    ],
}
```

A list of dotted paths, resolved on first read and cached. A path that does not import, or that
imports to something which is not a usable `BibFormat` with a name, raises `ImproperlyConfigured`
naming the offending entry rather than failing later from inside somebody's import run.

The shape of the setting is checked the same way. Both the wrapper dict and the list around a
single path are required, and writing either of them the other plausible way — `LITERATURE = [...]`,
or `"BIB_FORMATS": "one.path"` — raises `ImproperlyConfigured` naming what it found.

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

The caller does not need to know what it will get back, which is the point of asking.

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

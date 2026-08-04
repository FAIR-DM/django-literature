# Quickstart: importing a bibliographic file

Phase 1, amended 2026-08-04 for the maintainer's Phase 7 rework. What using the contract looks
like. Nothing here runs until a format is configured — the first one arrives with BibTeX support
(#22).

---

## Configure a format

```python
# settings.py
LITERATURE = {
    "BIB_FORMATS": [
        "myapp.formats.BibTeXFormat",
    ],
}
```

## Import a file

```python
from literature.importers import get_format

with open("library.bib") as handle:
    result = get_format("bibtex")().import_file(handle)

print(f"{len(result.created)} stored, {len(result.failed)} could not be read")

for entry in result.failed:
    label = entry.handle or f"entry {entry.index}"
    print(f"  {label}: {entry.reason}")
```

Every entry in the file is attempted. One bad entry does not stop the rest, and every one of them
is accounted for in `result.entries` whether it was stored or not.

## Rehearse it first

```python
bibtex = get_format("bibtex")()

with open("library.bib") as handle:
    preview = bibtex.import_file(handle, dry_run=True)

if preview.ok:
    with open("library.bib") as handle:
        bibtex.import_file(handle)
else:
    print(f"{len(preview.failed)} entries need attention before importing")
```

The rehearsal runs every stage, so its outcomes are observed rather than guessed. Nothing is stored.
`preview.entries[n].item` is `None` throughout, because the rows a dry run creates do not survive
it.

## Ask what this installation can read

```python
from literature.importers import available_formats

for name, format_class in available_formats().items():
    print(name, "—", format_class.label)
```

The caller does not need to know what it will get back, which is the point of asking.

## Write a format

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

Two stages and an optional third. Everything else — `import_file`, `import_entries`,
`import_entry`, `get_result`, and the `entry_created`/`entry_skipped`/`entry_failed` helpers — is
provided by `BibFormat` as ordinary methods, so this is enough to get correct behaviour without
writing any of them. List the class's dotted path in `LITERATURE["BIB_FORMATS"]` and it is
reachable by name.

`parse` **yields**. Returning a list would read the whole file into memory before anything is
stored, which the contract does not allow.

**An unusual format may override any of the provided methods.** Nothing in `BibFormat` tries to
stop that — see contracts/importers.md "Writing a format" for the maintainer's ruling on why, and
ADR-0006/ADR-0007 for the two guarantees (per-entry atomicity, catching every exception) a subclass
takes over when it replaces `import_entry`.

## Where the pieces live

| You want | Read |
|---|---|
| What the feature does and why | [spec.md](spec.md) |
| Why it is shaped this way | [decisions.md](decisions.md) |
| The signatures | [contracts/importers.md](contracts/importers.md) |
| The objects and their fields | [data-model.md](data-model.md) |

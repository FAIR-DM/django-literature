# Quickstart: importing a bibliographic file

Phase 1. What using the contract looks like. Nothing here runs until a format is registered — the
first one arrives with BibTeX support (#22).

---

## Import a file

```python
from literature.importers import import_file

with open("library.bib") as handle:
    result = import_file(handle, format="bibtex")

print(f"{len(result.created)} stored, {len(result.failed)} could not be read")

for entry in result.failed:
    label = entry.handle or f"entry {entry.index}"
    print(f"  {label}: {entry.reason}")
```

Every entry in the file is attempted. One bad entry does not stop the rest, and every one of them
is accounted for in `result.entries` whether it was stored or not.

## Rehearse it first

```python
with open("library.bib") as handle:
    preview = import_file(handle, format="bibtex", dry_run=True)

if preview.ok:
    with open("library.bib") as handle:
        import_file(handle, format="bibtex")
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

from literature.importers import BibFormat, SkipEntry, register


@register
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

Two stages and an optional third. A format has no say in how an `Item` is built from the CSL JSON
it returns, and no way to reach that stage.

`parse` **yields**. Returning a list would read the whole file into memory before anything is
stored, which the contract does not allow.

## Where the pieces live

| You want | Read |
|---|---|
| What the feature does and why | [spec.md](spec.md) |
| Why it is shaped this way | [decisions.md](decisions.md) |
| The signatures | [contracts/importers.md](contracts/importers.md) |
| The objects and their fields | [data-model.md](data-model.md) |

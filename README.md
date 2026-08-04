# django-literature

A Django app for storing, managing, and converting bibliographic references using the [CSL JSON 1.0.2](https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html) standard.

[![Tests](https://github.com/FAIR-DM/django-literature/actions/workflows/tests.yml/badge.svg)](https://github.com/FAIR-DM/django-literature/actions)
[![codecov](https://codecov.io/gh/FAIR-DM/django-literature/branch/main/graph/badge.svg)](https://codecov.io/gh/FAIR-DM/django-literature)
[![PyPI](https://img.shields.io/pypi/v/django-literature.svg)](https://pypi.org/project/django-literature/)
[![Python](https://img.shields.io/pypi/pyversions/django-literature.svg)](https://pypi.org/project/django-literature/)
[![Django](https://img.shields.io/pypi/djversions/django-literature.svg)](https://pypi.org/project/django-literature/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Features

- **Normalized data model** — five Django models (`Item`, `Name`, `ItemName`, `ItemDate`, `ItemIdentifier`) that faithfully represent the CSL JSON 1.0.2 specification.
- **Full CSL JSON coverage** — all 45 item types, 26 name roles, 6 date-variable slots, and 6 known identifier types.
- **Bidirectional conversion** — import CSL JSON dicts into the database and export model instances back to valid CSL JSON with full round-trip fidelity.
- **Partial date support** — year-only, year-month, full year-month-day, and date ranges via `django-partial-date`.
- **Identifier validation** — model-layer validators for DOI, ISBN, ISSN, URL, PMID, and PMCID formats.
- **Ordered contributors** — author, editor, and translator order is preserved independently within each role on an item.
- **i18n ready** — all user-facing strings wrapped with `gettext_lazy`; ships a pre-generated `locale/en/LC_MESSAGES/django.po` catalog.

---

## Scope & philosophy

**What it is.** Two Django apps that ship together. The core (`literature`) stores bibliographic
references as a normalized relational representation of CSL JSON 1.0.2 and converts between the two
in both directions with round-trip fidelity. It is headless: add `literature` to `INSTALLED_APPS`,
point a `ForeignKey` at an `Item`, and the host project owns its reference catalogue with no front
end pulled in. Layered on top is an opt-in UI app (`literature.ui`, built on
[django-mvp](https://github.com/django-mvp)) that provides a full front end, which is the intended
way to use the package in full. Install the core on its own, or add the UI when you want it.

**What it deliberately is not.**

- **Not a citation renderer in the core.** The core stores and converts CSL JSON. Formatting
  citations and bibliographies is added over time through a downstream CSL processor, never baked
  into the store.
- **Not a bundled admin.** No admin-based management ships with the package. A host that wants one
  registers its own; the UI app is where reference management lives.
- **Not a set of generic, restylable views.** The only views provided are the ones in
  `literature.ui`. Anything beyond that, a host builds against the models.
- **Not a host-styled UI.** `literature.ui` follows its own design system (django-mvp), not the
  host project's. It will not blend into your app's styling, and that is a deliberate trade for a UI
  that is complete and consistent on its own terms.
- **Not an external-registry client.** It does not sync with CrossRef, PubMed, or similar services
  at runtime.

**Tie-break principles**, when a design choice is contested:

1. **CSL JSON faithfulness wins.** The option closest to the CSL JSON structure and naming is
   preferred; any deviation is documented and mapped back to its CSL JSON equivalent.
2. **The core stays UI-free.** The store carries no front-end dependencies. Anything heavy, django-mvp
   included, sits behind the opt-in `literature.ui`, so embedding the core never drags in the UI stack.
3. **Relational integrity over convenience.** Known, stable fields (names, dates, identifiers) live
   in queryable relational structures, never JSON blobs.
4. **Translatable by default.** User-facing strings are always wrapped for i18n.

---

## Requirements

- Python 3.12+
- Django 5.2 or 6.0
- [django-partial-date](https://github.com/ktowen/django_partial_date)

---

## Installation

```bash
pip install django-literature
```

Add `literature` to `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "literature",
]
```

Apply migrations:

```bash
python manage.py migrate
```

---

## Quick Start

### Import from CSL JSON

```python
from literature.converters import from_csl_json

item = from_csl_json({
    "id": "Jennings2019",
    "type": "article-journal",
    "title": "A new compositionally based thermal conductivity model",
    "author": [
        {"family": "Jennings", "given": "S"},
        {"family": "Hasterok", "given": "D"},
    ],
    "issued": {"date-parts": [[2019, 8, 16]]},
    "DOI": "10.1093/gji/ggz376",
    "container-title": "Geophysical Journal International",
    "volume": "219",
    "issue": "2",
    "page": "1377-1394",
})

print(item.citation_key)  # "Jennings2019"
print(item.title)         # "A new compositionally based thermal conductivity model"
```

### Export to CSL JSON

```python
from literature.converters import to_csl_json

csl = to_csl_json(item)
# csl is a standards-compliant dict ready for citeproc-js or any CSL processor
```

### Batch import

```python
import json
from literature.converters import from_csl_json_list

with open("references.json") as f:
    items = from_csl_json_list(json.load(f))

print(f"Imported {len(items)} references")
```

### Import a bibliography file

CSL JSON is what this package stores, but researchers keep their libraries in BibTeX and RIS. The
import contract reads any configured format through one call and tells you what happened to every
entry in the file. Declare which formats your project reads in settings:

BibTeX is read out of the box and needs no configuration. Declare `BIB_FORMATS` only to add a
format of your own, which replaces the default list rather than extending it:

```python
# settings.py
LITERATURE = {
    "BIB_FORMATS": [
        "literature.importers.bibtex.BibTeXFormat",
        "myapp.formats.RISFormat",
    ],
}
```

Then import by name:

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
is accounted for in the result whether it was stored or not — you never have to compare counts to
find out something went wrong. An entry is stored in full or not at all, so a rejected contributor
never leaves an item behind without its authors.

Rehearse it first if you like. Every stage runs, nothing is written:

```python
with open("library.bib") as handle:
    preview = get_format("bibtex")().import_file(handle, dry_run=True)

if not preview.ok:
    print(f"{len(preview.failed)} entries need attention first")
```

To find out which formats an installation can read:

```python
from literature.importers import available_formats

for name, format_class in available_formats().items():
    print(name, "—", format_class.label)
```

#### Reading BibTeX

`bibtex` reads a `.bib` file in either dialect — classic BibTeX, which is what a publisher's
"export citation" link and most academic databases emit, and BibLaTeX, which is what current
Zotero and JabRef write. You do not have to know which one you were given.

An export is rarely clean, so the format recovers before it refuses. A DOI written as a resolver
URL is normalized to the bare identifier, LaTeX-encoded text becomes the characters it stands for,
XML escaping left over from a publisher's pipeline is resolved, and a value that cannot be
recovered is kept with the record instead of costing you the whole entry. `@string` macros are
expanded and `crossref` inheritance is resolved, including a reference to an entry defined further
down the file.

Fields that no bibliographic standard defines — the `file`, `owner` and `timestamp` bookkeeping
every reference manager writes into its exports — have no CSL equivalent and are not thrown away
either. They are stored on the item under `custom["bibtex"]` and can be read back:

```python
item = result.created[0].item
print(item.custom["bibtex"])   # {'file': ':papers/curie1898.pdf:PDF', 'owner': 'sam', ...}
```

[What maps to what](https://django-literature.readthedocs.io/en/latest/bibtex-mapping.html) is
generated from the mapping tables themselves, so it cannot fall out of step with the code.

RIS follows. Adding a format means writing a `BibFormat` subclass with a parser and a conversion
to CSL JSON, then listing its dotted path in `LITERATURE["BIB_FORMATS"]` — the workflow above does
not change. A format with an unusual need may override any of the workflow's other steps
(`import_entries`, `import_entry`, `get_result`); the base class only has to get the job done when
its two required stages are supplied, not stop you from replacing the rest.

### Query

```python
from literature.models import Item

# All journal articles
articles = Item.objects.filter(type="article-journal")

# Items authored by a specific person
by_jennings = Item.objects.filter(
    item_names__name__family="Jennings",
    item_names__role="author",
)
```

---

## Data Model Overview

```
Item ──< ItemName >── Name
  │
  ├──< ItemDate
  │
  └──< ItemIdentifier
```

| Model | Purpose | CSL JSON equivalent |
|---|---|---|
| `Item` | Core bibliographic entry | Top-level item object |
| `Name` | Person or organization | Name-variable object |
| `ItemName` | Associates names with items in a role and order | Name-variable array entry |
| `ItemDate` | Structured date per CSL date-variable slot | Date-variable object |
| `ItemIdentifier` | Typed identifier (DOI, ISBN, etc.) | Top-level string fields |

See the [data model documentation](docs/data-model.md) for the full field reference.

---

## Documentation

Full documentation is available in [docs/](docs/).

To build locally:

```bash
poetry install --with docs
poetry run sphinx-build -b html docs docs/_build/html
```

---

## Development

```bash
git clone https://github.com/FAIR-DM/django-literature.git
cd django-literature
poetry install
poetry run pytest
```

---

## License

MIT — see [LICENSE](LICENSE).

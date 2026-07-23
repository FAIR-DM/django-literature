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
- **Ordered contributors** — author/editor/translator order preserved per item and role via `django-ordered-model`.
- **i18n ready** — all user-facing strings wrapped with `gettext_lazy`; ships a pre-generated `locale/en/LC_MESSAGES/django.po` catalog.

---

## Scope & philosophy

**What it is.** A reusable Django app that stores bibliographic references as a faithful, normalized relational representation of CSL JSON 1.0.2, with round-trip import and export. It is embeddable — add it to `INSTALLED_APPS`, point a `ForeignKey` at an `Item`, and the host project owns its own reference catalogue.

**What it deliberately is not.**

- **Not a citation renderer.** It stores and converts CSL JSON; formatting citations and bibliographies against CSL styles is left to a downstream processor.
- **Not a standalone reference manager.** There is no end-user portal — just models, admin, and conversion for host projects to build on.
- **Not a multi-format importer.** BibTeX, RIS, PubMed XML, and CrossRef ingestion are out of scope for the core; they belong in extensions.
- **Not an external-registry client.** It does not sync with CrossRef, PubMed, or similar services at runtime.

**Tie-break principles**, when a design choice is contested:

1. **CSL JSON faithfulness wins.** The option closest to the CSL JSON structure and naming is preferred; deviations are documented and mapped back to their CSL JSON equivalent.
2. **Embeddability over features.** A change that would impose structure on the host project loses to one that keeps the app a drop-in.
3. **Relational integrity over convenience.** Known, stable fields (names, dates, identifiers) live in queryable relational structures, never JSON blobs.
4. **Translatable by default.** User-facing strings are always wrapped for i18n.

---

## Requirements

- Python 3.11+
- Django 4.2+
- [django-partial-date](https://github.com/ktowen/django_partial_date)
- [django-ordered-model](https://github.com/django-ordered-model/django-ordered-model) 3.7+

---

## Installation

```bash
pip install django-literature
```

Add `literature` and `ordered_model` to `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "ordered_model",
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

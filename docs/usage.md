# Usage Guide

This guide covers the most common tasks when working with `django-literature`.

## Creating items manually

### Minimal item

```python
from literature.models import Item

item = Item.objects.create(
    citation_key="Smith2024",
    type="article-journal",
    title="Thermal conductivity of the lithosphere",
)
```

### Full journal article

```python
from literature.models import Item, Name, ItemName, ItemDate, ItemIdentifier
from partial_date import PartialDate

# 1. Create the item
item = Item.objects.create(
    citation_key="Jennings2019",
    type="article-journal",
    title="A new compositionally based thermal conductivity model",
    container_title="Geophysical Journal International",
    volume="219",
    issue="2",
    page="1377-1394",
    language="en",
)

# 2. Add authors (order is preserved automatically)
jennings = Name.objects.create(family="Jennings", given="S")
hasterok = Name.objects.create(family="Hasterok", given="D")

ItemName.objects.create(item=item, name=jennings, role="author")
ItemName.objects.create(item=item, name=hasterok, role="author")

# 3. Add the publication date
ItemDate.objects.create(
    item=item,
    date_type="issued",
    begin=PartialDate("2019-08-16"),
)

# 4. Add identifiers
ItemIdentifier.objects.create(item=item, type="DOI", value="10.1093/gji/ggz376")
ItemIdentifier.objects.create(item=item, type="ISSN", value="0956-540X")
```

### Literal (organization) name

When a contributor is an organization rather than a person, use the `literal` field
and leave `family`/`given` empty:

```python
org = Name.objects.create(literal="World Health Organization")
ItemName.objects.create(item=item, name=org, role="author")
```

### Date range

For events or items that span a date range, set both `begin` and `end`:

```python
ItemDate.objects.create(
    item=item,
    date_type="event-date",
    begin=PartialDate("2024-06-10"),
    end=PartialDate("2024-06-14"),
)
```

### Year-only date

```python
ItemDate.objects.create(
    item=item,
    date_type="accessed",
    begin=PartialDate("2024"),
)
```

---

## Importing from CSL JSON

### Single item

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

`from_csl_json()` validates the record, resolves the citation key (deduplicating with a
letter suffix if needed), creates all related `Name`, `ItemDate`, and `ItemIdentifier`
records atomically, and calls `full_clean()` on every model object before saving.

### Validation errors

`from_csl_json()` raises `django.core.exceptions.ValidationError` if the dict is
invalid:

```python
from django.core.exceptions import ValidationError

try:
    item = from_csl_json({"type": "article-journal"})  # missing id/citation-key
except ValidationError as exc:
    print(exc.message_dict)
```

Common rejection reasons:

- `type` field is absent or not a known CSL item type.
- Both `citation-key` and `id` are absent or blank.
- An identifier value fails format validation (e.g. malformed DOI).

### Citation key deduplication

If an item with the same `citation_key` already exists, the importer automatically
appends a letter suffix:

```
Smith2009 → Smith2009b → Smith2009c → … → Smith2009z → Smith2009aa → …
```

Existing records are **never** overwritten.

### Batch import

```python
import json
from literature.converters import from_csl_json_list

with open("references.json") as f:
    data = json.load(f)

items = from_csl_json_list(data)
print(f"Imported {len(items)} items")
```

`from_csl_json_list()` skips invalid items (logging a warning for each) and returns
only the successfully created instances.

---

## Exporting to CSL JSON

```python
from literature.converters import to_csl_json

item = Item.objects.get(citation_key="Jennings2019")
csl = to_csl_json(item)
```

The returned dict:

- Always contains `"id"` (set to `citation_key`) and `"type"`.
- Omits blank/null fields — no empty strings or `null` values are emitted.
- Serializes names in their original order per role.
- Known identifiers (DOI, ISBN, ISSN, PMID, PMCID, URL) are top-level keys.
- Unknown identifier types are placed under the `"custom"` key.

Example output:

```json
{
  "id": "Jennings2019",
  "type": "article-journal",
  "title": "A new compositionally based thermal conductivity model",
  "container-title": "Geophysical Journal International",
  "volume": "219",
  "issue": "2",
  "page": "1377-1394",
  "language": "en",
  "author": [
    {"family": "Jennings", "given": "S"},
    {"family": "Hasterok", "given": "D"}
  ],
  "issued": {"date-parts": [[2019, 8, 16]]},
  "DOI": "10.1093/gji/ggz376",
  "ISSN": "0956-540X"
}
```

---

## Querying

```python
from literature.models import Item

# By item type
Item.objects.filter(type="article-journal")
Item.objects.filter(type="book")

# By author family name
Item.objects.filter(
    item_names__name__family="Jennings",
    item_names__role="author",
)

# By DOI
from literature.models import ItemIdentifier
doi = ItemIdentifier.objects.get(type="DOI", value="10.1093/gji/ggz376")
item = doi.item

# Published after 2015
from literature.models import ItemDate
recent = Item.objects.filter(
    item_dates__date_type="issued",
    item_dates__begin__gte="2015-01-01",
)

# All items with a DOI
with_doi = Item.objects.filter(item_identifiers__type="DOI")
```

---

## Round-trip fidelity

`to_csl_json()` followed by `from_csl_json()` produces a record with identical field
values (aside from the standard citation-key deduplication suffix, if triggered):

```python
from literature.converters import from_csl_json, to_csl_json

original = Item.objects.get(citation_key="Jennings2019")
csl = to_csl_json(original)
reimported = from_csl_json(csl)

assert reimported.title == original.title
assert reimported.type == original.type
```

---

## Django admin interface

`django-literature` ships a ready-made Django admin that lets you browse, create, and
edit all bibliographic data through the standard Django admin site.

### Required `INSTALLED_APPS` entries

```python
INSTALLED_APPS = [
    # Django built-ins required by the admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Third-party
    "ordered_model",
    # This app
    "literature",
    ...
]
```

### Timezone note

`PartialDateField` stores dates as naive datetime objects. Set `TIME_ZONE = "UTC"` in
your settings (or `USE_TZ = False`) to ensure that year-based filters in the admin
work correctly across all timezones.

### Features

- **Items** (`/admin/literature/item/`)
  - 12 organised fieldsets covering all CSL JSON fields
  - Inline editing of contributors (with drag-and-drop ordering), dates, and identifiers
  - Changelist columns: title, type, year, citation key
  - Search by title or citation key
  - Sidebar filters by item type, issued year, and publisher

- **Names** (`/admin/literature/name/`)
  - Changelist showing family, given, and literal fields
  - Search by family name, given name, or literal

For a step-by-step integration walkthrough see [quickstart.md](quickstart.md).

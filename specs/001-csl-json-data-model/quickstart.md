# Quickstart: CSL JSON Data Model

**Feature**: 001-csl-json-data-model

## Installation

```bash
pip install django-literature
```

Or with Poetry:

```bash
poetry add django-literature
```

## Configuration

Add `literature` and `ordered_model` to your `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "ordered_model",
    "literature",
]
```

Run migrations:

```bash
python manage.py migrate
```

## Creating Items Programmatically

### Basic Item

```python
from literature.models import Item

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
```

### Adding Names (Authors, Editors, etc.)

```python
from literature.models import Name, ItemName

# Create name records
jennings = Name.objects.create(family="Jennings", given="S")
hasterok = Name.objects.create(family="Hasterok", given="D")

# Link to item with role and order
ItemName.objects.create(item=item, name=jennings, role="author")
ItemName.objects.create(item=item, name=hasterok, role="author")
# django-ordered-model manages the order automatically
```

### Adding Dates

```python
from literature.models import ItemDate
from partial_date import PartialDate

# Full date
ItemDate.objects.create(
    item=item,
    date_type="issued",
    begin=PartialDate("2019-08-16"),
)

# Year-only date
ItemDate.objects.create(
    item=item,
    date_type="accessed",
    begin=PartialDate("2024"),
)

# Date range
ItemDate.objects.create(
    item=item,
    date_type="event-date",
    begin=PartialDate("2019-08-12"),
    end=PartialDate("2019-08-16"),
)
```

### Adding Identifiers

```python
from literature.models import ItemIdentifier

ItemIdentifier.objects.create(
    item=item,
    type="DOI",
    value="10.1093/gji/ggz376",
)

ItemIdentifier.objects.create(
    item=item,
    type="ISSN",
    value="0956-540X",
)
```

## Importing from CSL JSON

```python
from literature.converters import from_csl_json

csl_data = {
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
}

item = from_csl_json(csl_data)
print(item.citation_key)  # "Jennings2019"
print(item.title)          # "A new compositionally based thermal conductivity model"
```

### Batch Import

```python
import json
from literature.converters import from_csl_json_list

with open("references.json") as f:
    csl_items = json.load(f)

items = from_csl_json_list(csl_items)
print(f"Imported {len(items)} items")
```

## Exporting to CSL JSON

```python
from literature.converters import to_csl_json

item = Item.objects.get(citation_key="Jennings2019")
csl_dict = to_csl_json(item)

import json
print(json.dumps(csl_dict, indent=2))
```

Output:

```json
{
  "id": "Jennings2019",
  "type": "article-journal",
  "title": "A new compositionally based thermal conductivity model",
  "container-title": "Geophysical Journal International",
  "volume": "219",
  "issue": "2",
  "page": "1377-1394",
  "author": [
    {"family": "Jennings", "given": "S"},
    {"family": "Hasterok", "given": "D"}
  ],
  "issued": {
    "date-parts": [[2019, 8, 16]]
  },
  "DOI": "10.1093/gji/ggz376"
}
```

## Querying

```python
# All journal articles
Item.objects.filter(type="article-journal")

# Items by a specific author
Item.objects.filter(
    item_names__name__family="Jennings",
    item_names__role="author",
)

# Items with DOI
Item.objects.filter(
    identifiers__type="DOI",
)

# Items published in 2019
from partial_date import PartialDate
Item.objects.filter(
    dates__date_type="issued",
    dates__begin__gte=PartialDate("2019"),
)
```

## Round-Trip Fidelity

```python
from literature.converters import from_csl_json, to_csl_json

# Import → export → verify
original = {"type": "book", "id": "test1", "title": "My Book", ...}
item = from_csl_json(original)
exported = to_csl_json(item)

assert exported["type"] == original["type"]
assert exported["title"] == original["title"]
# All stored fields are preserved through round-trip
```

# How to import CSL JSON

Store a reference, or a list of them, from CSL JSON, the format citeproc-js, Pandoc and most
reference managers exchange. To import a BibTeX or RIS file, see
[How to import a bibliography file in code](import-a-bibliography-file-in-code.md).

## Import one record

1. Pass the record to `from_csl_json()`:

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

2. Catch the `ValidationError` it raises for a record it cannot store:

   ```python
   from django.core.exceptions import ValidationError

   try:
       item = from_csl_json({"type": "article-journal"})  # no id or citation-key
   except ValidationError as exc:
       print(exc.message_dict)
   ```

   A record is refused when:

   - `type` is absent or not a known CSL item type,
   - both `citation-key` and `id` are absent or blank,
   - an identifier value fails its format check, such as a malformed DOI.

## Import a list of records

Pass the list to `from_csl_json_list()`:

```python
import json

from literature.converters import from_csl_json_list

with open("references.json") as f:
    data = json.load(f)

items = from_csl_json_list(data)
print(f"Imported {len(items)} items")
```

## The result

Each record is stored with its contributors, dates and identifiers in one transaction, so a record
that fails stores nothing. `from_csl_json_list()` skips a record it cannot store, logs a warning
for it, and returns the items it did store.

The citation key is stored as given, even when another reference already has it. See
[Citation keys](../explanation/citation-keys.md).

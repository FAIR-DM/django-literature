# Exporting

A stored reference exports to a CSL JSON record, ready for citeproc-js, Pandoc or any other CSL
processor. Importing the record again gives back the same values.

## Export a reference as CSL JSON

Pass the item to `to_csl_json()`:

```python
from literature.converters import to_csl_json
from literature.models import Item

item = Item.objects.get(pk=12)
csl = to_csl_json(item)
```

`csl` is a dict:

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

## What the record holds

- `id`, set to the citation key, and `type` are always present.
- A blank field is left out rather than written as an empty string or `null`.
- Names are listed in their stored order within each role.
- DOI, ISBN, ISSN, PMID, PMCID and URL are top-level keys. An identifier of any other type is
  written under `custom`.


## What survives a round trip

The models are a relational translation of CSL JSON 1.0.2, so a reference can travel from CSL JSON
into the database and back out again.

### From the models to CSL JSON and back

`to_csl_json()` followed by `from_csl_json()` gives a record with the same field values, the
citation key included:

```python
from literature.converters import from_csl_json, to_csl_json
from literature.models import Item

original = Item.objects.get(pk=12)
reimported = from_csl_json(to_csl_json(original))

assert reimported.title == original.title
assert reimported.type == original.type
```

### From CSL JSON to the models and back

Importing CSL JSON and exporting it again gives the same CSL JSON, less five variables a citation
processor assigns: `citation-label`, `citation-number`, `first-reference-note-number`, `locator` and
`year-suffix`. Those describe one citation in one document rather than the reference itself, so an
import drops them and an export never writes them. The decision is recorded in
[ADR 0035](../adr/0035-citation-processor-variables-are-not-stored.md).

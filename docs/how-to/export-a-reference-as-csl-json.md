# How to export a reference as CSL JSON

Turn a stored reference into a CSL JSON record, to hand to citeproc-js, Pandoc or any other CSL
processor.

## Steps

1. Pass the item to `to_csl_json()`:

   ```python
   from literature.converters import to_csl_json
   from literature.models import Item

   item = Item.objects.get(pk=12)
   csl = to_csl_json(item)
   ```

## The result

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

- `id`, set to the citation key, and `type` are always present.
- A blank field is left out rather than written as an empty string or `null`.
- Names are listed in their stored order within each role.
- DOI, ISBN, ISSN, PMID, PMCID and URL are top-level keys. An identifier of any other type is
  written under `custom`.

Importing the record again gives back the same values. See
[Round-trip fidelity](../explanation/round-trip-fidelity.md).

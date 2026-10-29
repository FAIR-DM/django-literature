# Round-trip fidelity

The models are a relational translation of CSL JSON 1.0.2, so a reference can travel from CSL JSON
into the database and back out again. This page covers what survives that journey and what does
not.

## From the models to CSL JSON and back

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

## From CSL JSON to the models and back

Importing CSL JSON and exporting it again gives the same CSL JSON, less five variables a citation
processor assigns: `citation-label`, `citation-number`, `first-reference-note-number`, `locator` and
`year-suffix`. Those describe one citation in one document rather than the reference itself, so an
import drops them and an export never writes them. The decision is recorded in
[ADR 0035](../adr/0035-citation-processor-variables-are-not-stored.md).

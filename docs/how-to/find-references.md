# Find references

Find stored references by type, contributor, identifier or date with ordinary Django queries.
Contributors, dates and identifiers are related records, so a query reaches them through
`item_names`, `item_dates` and `item_identifiers`.

## By type

```python
from literature.models import Item

Item.objects.filter(type="article-journal")
```

## By contributor

```python
Item.objects.filter(
    item_names__name__family="Jennings",
    item_names__role="author",
)
```

## By identifier

```python
from literature.models import ItemIdentifier

item = ItemIdentifier.objects.get(type="DOI", value="10.1093/gji/ggz376").item

with_doi = Item.objects.filter(item_identifiers__type="DOI")
```

## By date

```python
recent = Item.objects.filter(
    item_dates__date_type="issued",
    item_dates__begin__gte="2015-01-01",
)
```

## By citation key

A citation key does not have to be unique, so use `filter()` rather than `get()`, which raises
`MultipleObjectsReturned` when two references share a key:

```python
Item.objects.filter(citation_key="Jennings2019")
```

The model fields, roles and date slots are listed in the [data model](../reference/data-model.md).

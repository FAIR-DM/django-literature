# Storing references

A reference is an `Item`. Its contributors, dates and identifiers are related records, so each
holds as much as the source knows and can be queried like any other Django model. This page covers
creating references through the models, finding them, and reading the values a page usually needs.
To create a reference from a CSL JSON record or a bibliography file instead, see
[Importing](importing.md). Every field, role and date slot is listed in the
[data model](../reference/data-model.md).

## Create a reference

1. Create the `Item`. A citation key and a type are all it needs:

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

2. Credit its contributors. Each person is a `Name`, credited in a role through `ItemName`, and the
   order they are credited in is kept within each role:

   ```python
   from literature.models import ItemName, Name

   jennings = Name.objects.create(family="Jennings", given="S")
   hasterok = Name.objects.create(family="Hasterok", given="D")

   ItemName.objects.create(item=item, name=jennings, role="author")
   ItemName.objects.create(item=item, name=hasterok, role="author")
   ```

   An organisation, or a name to print exactly as written, goes in `literal`, with `family` and
   `given` left empty:

   ```python
   org = Name.objects.create(literal="World Health Organization")
   ItemName.objects.create(item=item, name=org, role="author")
   ```

3. Add its dates. A date holds only the precision you know, so `PartialDate("2024")` is a year
   alone:

   ```python
   from partial_date import PartialDate

   from literature.models import ItemDate

   ItemDate.objects.create(
       item=item,
       date_type="issued",
       begin=PartialDate("2019-08-16"),
   )
   ```

   An event that spans several days takes an `end` as well:

   ```python
   ItemDate.objects.create(
       item=item,
       date_type="event-date",
       begin=PartialDate("2024-06-10"),
       end=PartialDate("2024-06-14"),
   )
   ```

4. Add its identifiers:

   ```python
   from literature.models import ItemIdentifier

   ItemIdentifier.objects.create(item=item, type="DOI", value="10.1093/gji/ggz376")
   ItemIdentifier.objects.create(item=item, type="ISSN", value="0956-540X")
   ```

A malformed DOI, ISBN, ISSN, URL, PMID or PMCID is refused when it is saved. How names and roles
are modelled is recorded in [ADR 0003](../adr/0003-names-are-role-neutral-and-shared.md).

## Find references

Contributors, dates and identifiers are reached through `item_names`, `item_dates` and
`item_identifiers`:

```python
from literature.models import Item, ItemIdentifier

# By type
Item.objects.filter(type="article-journal")

# By contributor
Item.objects.filter(item_names__name__family="Jennings", item_names__role="author")

# By identifier
item = ItemIdentifier.objects.get(type="DOI", value="10.1093/gji/ggz376").item
Item.objects.filter(item_identifiers__type="DOI")

# By date
Item.objects.filter(item_dates__date_type="issued", item_dates__begin__gte="2015-01-01")
```

A citation key does not have to be unique, so look one up with `filter()` rather than `get()`,
which raises `MultipleObjectsReturned` when two references share a key:

```python
Item.objects.filter(citation_key="Jennings2019")
```

Why keys may repeat is explained [below](#why-citation-keys-may-repeat).

## Link to a reference and cite its DOI

An `Item` carries the values a page usually shows about a reference:

```python
item.get_absolute_url()  # "/catalogue/12/": its page in the catalogue
item.doi                 # "10.1093/gji/ggz376", or None
item.doi_url             # "https://doi.org/10.1093/gji/ggz376", or None
item.year                # 2019, from the issued date, or None
```

Each is `None` when the reference does not hold it, so a template can leave the link or the year
out with `{% if %}`. `get_absolute_url()` resolves only in a project that mounts
`literature.ui.urls`.

On a list, prefetch the identifiers and dates, so each row costs no extra query:

```python
items = Item.objects.prefetch_related("item_identifiers", "item_dates")
```

To show the whole reference rather than single values, use the component described in
[Displaying references](../ui/displaying.md).

## Why citation keys may repeat

A citation key is the short name a reference is cited by in a manuscript, such as `Jennings2019`.
The package stores a key exactly as it arrives and never keeps keys distinct. How the BibTeX and RIS
importers find or make a key is in their format mappings,
[BibTeX](../reference/format-mapping/bibtex.md) and [RIS](../reference/format-mapping/ris.md).

### A key is stored as given

`from_csl_json()`, the file importers and the front end's forms all store a key exactly as it
arrives. If a reference with the same key already exists, the new one is stored under that key
too. Nothing warns, nothing refuses, and nothing rewrites the key to keep the two apart. Existing
records are never overwritten.

### Keeping keys distinct is the reader's business

`citation_key` is not declared unique, and two references may share a key. A key exists so a
person can point at the right reference in their own manuscript, so keeping keys distinct is their
business, as it is in every other reference manager.

Enforcing it would also go wrong. A check across the whole store assumes one bibliography per
installation, which separate bibliographies per user, or per article being written, would break.
And rewriting a clashing key, as the package once did by storing `smith2020` as `smith2020-2`,
quietly changes the key the person cites. The decision is recorded in
[ADR 0023](../adr/0023-citation-key-uniqueness-is-the-readers-concern.md).

### A reference is addressed by its primary key

Because a key may be shared, it does not pick out one reference. A reference's page in the
catalogue is addressed by its primary key for this reason
([ADR 0015](../adr/0015-a-reference-page-is-addressed-by-primary-key.md)).
`Item.objects.get(citation_key=...)` can raise `MultipleObjectsReturned`, so a lookup by key uses
`filter()` wherever a duplicate is possible.

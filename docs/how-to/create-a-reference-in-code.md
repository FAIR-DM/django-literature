# How to create a reference in code

Create a reference, its contributors, its dates and its identifiers directly through the models,
as a data migration or a script would. To create one from a CSL JSON record instead, see
[How to import CSL JSON](import-csl-json.md).

## Steps

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

## The result

The reference is stored with its contributors, dates and identifiers. A malformed DOI, ISBN, ISSN,
URL, PMID or PMCID is refused when it is saved. The fields, roles, date slots and identifier types
are listed in the [data model](../reference/data-model.md).

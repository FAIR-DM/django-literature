# Link to a reference and cite its DOI

Link to a reference's page in the catalogue, and show its DOI and year, on a page of your own. To
show the whole reference, see
[Show a reference on your own page](show-a-reference-on-your-own-page.md).

## Steps

1. Read what you need from the item:

   ```python
   item.get_absolute_url()  # "/catalogue/12/": its page in the catalogue
   item.doi                 # "10.1093/gji/ggz376", or None
   item.doi_url             # "https://doi.org/10.1093/gji/ggz376", or None
   item.year                # 2019, from the issued date, or None
   ```

   `get_absolute_url()` resolves only in a project that mounts `literature.ui.urls`.

2. On a list, prefetch the identifiers and dates, so each row costs no extra query:

   ```python
   items = Item.objects.prefetch_related("item_identifiers", "item_dates")
   ```

## The result

Each value is `None` when the reference does not hold it, so a template can leave the link or the
year out with `{% if %}`.

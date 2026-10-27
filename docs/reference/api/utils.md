# `literature.utils`

`literature.utils` holds two helper functions that no model owns.

- `parse_date_parts` turns one CSL JSON `date-parts` entry, such as `[2019, 8]`, into a
  `PartialDate` with the same precision, or returns `None` for a value it cannot read.
- `doi_url` turns a DOI stored without its resolver, such as `10.1002/abc`, into a
  `https://doi.org/` address, or returns `None` for a value not shaped like a DOI. The scheme and
  host are fixed, so the stored text can only ever become the path of the link. `Item.doi_url` and
  the reference page both use it.

```{eval-rst}
.. automodule:: literature.utils
   :members:
   :undoc-members: False
```

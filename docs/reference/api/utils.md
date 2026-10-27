# `literature.utils`

## `literature.utils.doi`

`doi_url` turns a DOI stored without its resolver, such as `10.1002/abc`, into a
`https://doi.org/` address, or returns `None` for a value not shaped like a DOI. The scheme and
host are fixed, so the stored text can only ever become the path of the link. `Item.doi_url` and
the reference page both use it.

```{eval-rst}
.. automodule:: literature.utils.doi
   :members:
   :undoc-members: False
```

## `literature.utils.date`

```{eval-rst}
.. automodule:: literature.utils.date
   :members:
   :undoc-members: False
   :show-inheritance:
```

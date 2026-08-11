"""Scalar-field iteration for the reference page — D-6.

Lives beside its only caller, ``item_detail.html``'s view, rather than in
``literature/utils/``: the core stays free of a helper an optional app is
the sole consumer of (FR-006).
"""

DEFAULT_SKIP = frozenset({"created", "modified", "categories", "custom"})


def scalar_fields(item, skip=DEFAULT_SKIP):
    """Yield ``(verbose_name, value)`` for ``item``'s non-empty scalar fields.

    Excludes relations (fields without ``attname``), the primary key, and any
    field named in ``skip``. A field whose value is ``None``, an empty string,
    or ``False`` is treated as not carried, so it is omitted rather than
    yielded with a blank value (FR-021).
    """
    for field in item._meta.get_fields():
        if not hasattr(field, "attname"):
            continue  # relation
        if field.primary_key:
            continue
        if field.name in skip:
            continue
        value = getattr(item, field.name, None)
        if value is None or value == "" or value is False:
            continue
        yield field.verbose_name, value

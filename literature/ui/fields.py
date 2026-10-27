"""Field sections for the reference page."""

from literature.ui.fieldgroups import FieldGroups

#: Fields the reference page shows in its own header, not in a details table.
HEADER_FIELDS = frozenset({"type", "citation_key", "title", "abstract"})


def field_sections(item):
    """Return the item's carried fields as ``{label, rows}`` sections.

    One section per field group (``literature/ui/fieldgroups.py``), in the
    order the edit form uses, so a reader finds a value under the same heading
    on both pages. A group holding no value is left out, and so is every field
    the page header already shows.

    A value of ``None``, an empty string or ``False`` counts as not carried.
    This lives here rather than in ``literature/utils/`` so the core carries no
    helper that only the optional app uses (FS-006, #55).

    Args:
        item: The item whose fields to group.

    Returns:
        One ``{"label": ..., "rows": [(verbose_name, value), ...]}`` dict per
        non-empty group.
    """
    sections = []
    for group, names in FieldGroups.GROUPS.items():
        rows = []
        for name in names:
            if name in HEADER_FIELDS:
                continue
            value = getattr(item, name, None)
            if value is None or value == "" or value is False:
                continue
            rows.append((item._meta.get_field(name).verbose_name, value))
        if rows:
            sections.append({"label": FieldGroups.GROUP_LABELS[group], "rows": rows})
    return sections

"""Field sections for the reference page.

Lives beside its only caller, ``item_detail.html``'s view, rather than in
``literature/utils/``: the core stays free of a helper an optional app is
the sole consumer of (FS-006, #55).
"""

from literature.choices import DateType
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


def issued_year(item):
    """Return the year the item was issued, or ``None`` when no year is stored."""
    for item_date in item.item_dates.all():
        if item_date.date_type == DateType.ISSUED and item_date.begin:
            return item_date.begin.date.year
    return None

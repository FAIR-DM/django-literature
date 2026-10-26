"""A searchable picker for choosing one reference in a project's own form."""

from literature.choices import NameRole
from literature.models import Item


def item_label(item: Item) -> str:
    """Return the text that names a reference wherever the picker shows it.

    The title (the citation key when there is none), then the issued year in
    brackets, then the first contributor. Whatever a reference lacks is left out.
    Reads ``item_dates`` and ``item_names`` through ``.all()``, so items loaded
    with those prefetched are labelled without a query.

    Args:
        item: The reference to label.

    Returns:
        The label.
    """
    label = item.title or item.citation_key
    year = item.year
    if year is not None:
        label = f"{label} ({year})"
    links = sorted(item.item_names.all(), key=lambda link: link.order)
    authors = [link for link in links if link.role == NameRole.AUTHOR]
    credited = authors or links
    if credited:
        name = credited[0].name.family or credited[0].name.literal
        if name:
            label = f"{label}, {name}"
    return label

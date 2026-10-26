"""Turn a stored DOI into its resolver link.

Lives in the core rather than beside the reference page that first needed it,
because ``Item.doi_url`` gives every host project the same link the catalogue
draws.
"""

from urllib.parse import quote


def doi_url(value: str | None) -> str | None:
    """Return the doi.org address for a bare DOI, or ``None`` if it is not one.

    The scheme and host are fixed here, so the stored text can only ever
    become the path of an https link. Anything not shaped like a DOI
    (``10.`` followed by a registrant and a ``/``) stays plain text.
    """
    if not value or not str(value).startswith("10.") or "/" not in str(value):
        return None
    return "https://doi.org/" + quote(str(value), safe="/:;()._-")

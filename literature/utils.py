"""Helper functions for CSL JSON dates and DOIs."""

from __future__ import annotations

from urllib.parse import quote

from partial_date import PartialDate


def parse_date_parts(date_parts: list) -> PartialDate | None:
    """Convert a single CSL JSON date-parts entry to a PartialDate.

    A ``date-parts`` array holds one or two date arrays of 1-3 integers:
    ``[year]``, ``[year, month]`` or ``[year, month, day]``. Month is 1-based.

    Args:
        date_parts: A single date array from CSL JSON ``date-parts``,
            e.g. ``[2019]``, ``[2019, 8]``, or ``[2019, 8, 16]``.

    Returns:
        A date with precision matching the number of
        components provided, or ``None`` if parsing fails (empty list,
        invalid values, etc.).

    Examples:
        >>> parse_date_parts([2019])
        PartialDate('2019')
        >>> parse_date_parts([2019, 8])
        PartialDate('2019-08')
        >>> parse_date_parts([2019, 8, 16])
        PartialDate('2019-08-16')
        >>> parse_date_parts([]) is None
        True
    """
    if not date_parts:
        return None

    try:
        parts = [int(p) for p in date_parts]
        year = parts[0]
        month = parts[1] if len(parts) >= 2 else None
        day = parts[2] if len(parts) >= 3 else None

        if month is not None and day is not None:
            return PartialDate(f"{year:04d}-{month:02d}-{day:02d}")
        elif month is not None:
            return PartialDate(f"{year:04d}-{month:02d}")
        else:
            return PartialDate(f"{year:04d}")
    except (ValueError, TypeError, IndexError):
        return None


def doi_url(value: str | None) -> str | None:
    """Return the doi.org address for a bare DOI, or ``None`` if it is not one.

    The scheme and host are fixed here, so the stored text can only ever
    become the path of an https link. Anything not shaped like a DOI
    (``10.`` followed by a registrant and a ``/``) stays plain text. It lives in
    the core because ``Item.doi_url`` gives every host project the same link.

    Args:
        value: The stored DOI text, or ``None``.

    Returns:
        The ``https://doi.org/`` link, or ``None`` if ``value`` is not a DOI.
    """
    if not value or not str(value).startswith("10.") or "/" not in str(value):
        return None
    return "https://doi.org/" + quote(str(value), safe="/:;()._-")

"""Helper functions for CSL JSON dates and DOIs."""

from __future__ import annotations

from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from partial_dates import PartialDate


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
        values that are not numbers, etc.).

    Raises:
        ValidationError: The numbers name no date, such as month 13.

    Examples:
        >>> str(parse_date_parts([2019]))
        '2019'
        >>> str(parse_date_parts([2019, 8]))
        '2019-08'
        >>> str(parse_date_parts([2019, 8, 16]))
        '2019-08-16'
        >>> parse_date_parts([]) is None
        True
    """
    if not date_parts:
        return None

    try:
        parts = [int(p) for p in date_parts]
    except (ValueError, TypeError):
        return None

    try:
        return PartialDate(*parts[:3])
    except ValueError as error:
        raise ValidationError(
            _("%(parts)s is not a valid date."), params={"parts": date_parts}
        ) from error


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

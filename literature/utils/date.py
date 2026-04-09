"""Date parsing utilities for CSL JSON date-parts conversion.

Provides helpers to convert CSL JSON ``date-parts`` arrays to
``partial_date.PartialDate`` objects for storage in ``ItemDate.begin``
and ``ItemDate.end`` fields.

CSL JSON date-parts spec:
  A ``date-parts`` array contains one or two date arrays. Each date array
  contains 1-3 integers: ``[year]``, ``[year, month]``, or
  ``[year, month, day]``. Month is 1-based (1=January).

  Examples:
    ``[[2019]]``            → year-only
    ``[[2019, 8]]``         → year + month
    ``[[2019, 8, 16]]``     → full date
    ``[[2019, 8, 12], [2019, 8, 16]]``  → date range
"""

from __future__ import annotations

from partial_date import PartialDate


def parse_date_parts(date_parts: list) -> PartialDate | None:
    """Convert a single CSL JSON date-parts entry to a PartialDate.

    Args:
        date_parts: A single date array from CSL JSON ``date-parts``,
            e.g. ``[2019]``, ``[2019, 8]``, or ``[2019, 8, 16]``.

    Returns:
        A ``PartialDate`` with precision matching the number of components
        provided, or ``None`` if parsing fails (empty list, invalid values,
        etc.).

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
            # Full date precision
            return PartialDate(f"{year:04d}-{month:02d}-{day:02d}")
        elif month is not None:
            # Year + month precision
            return PartialDate(f"{year:04d}-{month:02d}")
        else:
            # Year-only precision
            return PartialDate(f"{year:04d}")
    except (ValueError, TypeError, IndexError):
        return None

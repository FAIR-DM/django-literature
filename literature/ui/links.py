"""Decide whether a stored value may be rendered as a link."""

from urllib.parse import urlsplit

#: Linkified on an allowlist, never a substring: identifier values are arbitrary
#: text, and autoescaping leaves a ``javascript:`` scheme intact in an ``href``.
LINKABLE_SCHEMES = frozenset({"http", "https"})


def web_url(value):
    """Return *value* if it is an ``http``/``https`` URL, otherwise ``None``.

    Anything else — a bare DOI, an ISBN, a ``javascript:`` or ``data:``
    payload, an unparseable string — returns ``None`` and is rendered as
    plain text instead of a link.

    Args:
        value: The stored text to check.

    Returns:
        ``value`` unchanged if it is a web URL, otherwise ``None``.
    """
    if not value:
        return None
    try:
        scheme = urlsplit(str(value)).scheme
    except ValueError:
        # A malformed authority (an unclosed IPv6 bracket) is not linkable.
        return None
    return value if scheme in LINKABLE_SCHEMES else None

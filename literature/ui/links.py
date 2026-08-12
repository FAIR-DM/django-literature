"""Deciding whether a stored value may be rendered as a link — RS-001.

``ItemIdentifier.type`` carries no ``choices`` by design: an unknown type
skips format validation entirely so nothing is lost on import (FR-017,
``validators.validate_identifier``). An identifier value is therefore
arbitrary stored text, and the reference page must not put arbitrary text
into an ``href``. Autoescaping does not help here — it escapes the
characters in a URI, not the scheme it names, so ``javascript:`` survives
it intact.

So the reference page linkifies on an allowlist, never on a substring.
"""

from urllib.parse import urlsplit

LINKABLE_SCHEMES = frozenset({"http", "https"})


def web_url(value):
    """Return *value* if it is an ``http``/``https`` URL, otherwise ``None``.

    Anything else — a bare DOI, an ISBN, a ``javascript:`` or ``data:``
    payload, an unparseable string — returns ``None`` and is rendered as
    plain text instead of a link.
    """
    if not value:
        return None
    try:
        scheme = urlsplit(str(value)).scheme
    except ValueError:
        # A malformed authority (an unclosed IPv6 bracket, say) is not a
        # URL we are willing to link to.
        return None
    return value if scheme in LINKABLE_SCHEMES else None

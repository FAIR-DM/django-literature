"""Value normalization shared across bibliographic formats.

Exactly two of ``bibtex.py``'s cleaning functions are format-neutral: recovering a DOI or an
ISBN written in a form the catalogue would reject into the bare value it accepts. RIS carries the
same two malformations BibTeX does — a DOI resolver URL, a ``doi:`` label — so this is the one
module the RIS and BibTeX formats share (plan.md "Shared normalization", spec 005 T005).

Everything else in ``bibtex.py``'s cleaning layer stays there. ``_clean_text``,
``_unescape_entities`` and ``_clean_identifier`` decode LaTeX and XML character escaping that
only a ``.bib`` file carries — RIS has no such escape layer, and running that decoder over an RIS
value would silently rewrite genuine content (a DOI or URL containing ``~``, ``_``, ``^``, ``%``
or braces comes out altered), against FR-024 and FR-025.
"""

import re


class IdentifierNormalizer:
    """Normalization for identifier values recoverable into a form the catalogue accepts.

    Grouped per Article XV: both methods share a subject — cleaning one identifier value ahead of
    validation — so they belong on a class rather than as two module-level functions.
    """

    #: A DOI written with its resolver URL prefix (FR-025's named case).
    _DOI_URL_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)

    #: A DOI carrying a plain ``doi:`` label rather than a bare identifier.
    _DOI_LABEL_RE = re.compile(r"^doi:\s*", re.IGNORECASE)

    #: An ISBN carrying a redundant ``isbn:`` / ``isbn-13:`` label, the same shape of
    #: malformation the DOI case is named for.
    _ISBN_LABEL_RE = re.compile(r"^isbn(?:-1[03])?:?\s*", re.IGNORECASE)

    @classmethod
    def normalize_doi(cls, value: str) -> str:
        """Strip a resolver URL prefix or a ``doi:`` label, leaving the bare DOI.

        A value carrying neither is returned unchanged — normalization only removes what it
        recognises, and cleaning that cannot recover a value leaves it for preservation rather
        than guessing at it.
        """
        text = value.strip()
        # Both wrappers, in either order and in combination: a `doi:` label in front of a
        # resolver URL is what a hand-maintained file and some export pipelines produce, and
        # stripping only one leaves a URL where a bare DOI belongs. Bounded rather than
        # `while True`, since each pass must remove something for the next to run.
        for _pass in range(4):
            stripped = cls._DOI_LABEL_RE.sub("", cls._DOI_URL_RE.sub("", text)).strip()
            if stripped == text:
                break
            text = stripped
        return text

    @classmethod
    def normalize_isbn(cls, value: str) -> str:
        """Strip a redundant ``isbn:`` label.

        Hyphens and spaces are the validator's own job (``validate_isbn`` strips them before
        checking).
        """
        return cls._ISBN_LABEL_RE.sub("", value.strip()).strip()

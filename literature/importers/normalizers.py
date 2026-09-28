"""Identifier normalization shared by the BibTeX and RIS formats.

Only DOI and ISBN recovery is shared. The LaTeX and XML unescaping in
``bibtex.py`` stays there: RIS has no such escape layer, and running that
decoder over an RIS value would rewrite genuine content, such as a DOI or URL
containing ``~``, ``_``, ``^``, ``%`` or braces.
"""

import re


class IdentifierNormalizer:
    """Normalization for identifier values recoverable into a form the catalogue accepts.

    Both methods clean one identifier value ahead of validation, so they share a
    class rather than sitting as two module-level functions.
    """

    #: A DOI written with its resolver URL prefix.
    _DOI_URL_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)

    #: A DOI carrying a plain ``doi:`` label rather than a bare identifier.
    _DOI_LABEL_RE = re.compile(r"^doi:\s*", re.IGNORECASE)

    #: An ISBN carrying a redundant ``isbn:`` / ``isbn-13:`` label.
    _ISBN_LABEL_RE = re.compile(r"^isbn(?:-1[03])?:?\s*", re.IGNORECASE)

    @classmethod
    def normalize_doi(cls, value: str) -> str:
        """Strip a resolver URL prefix or a ``doi:`` label, leaving the bare DOI.

        A value carrying neither is returned unchanged: normalization removes
        only what it recognises and never guesses.

        Args:
            value: The DOI as the source wrote it.

        Returns:
            The bare DOI, or the stripped input if nothing was recognised.
        """
        text = value.strip()
        # A `doi:` label in front of a resolver URL is common in hand-maintained
        # files, so both wrappers are stripped in any order. Bounded, since each
        # pass must remove something for the next to run.
        for _pass in range(4):
            stripped = cls._DOI_LABEL_RE.sub("", cls._DOI_URL_RE.sub("", text)).strip()
            if stripped == text:
                break
            text = stripped
        return text

    @classmethod
    def normalize_isbn(cls, value: str) -> str:
        """Strip a redundant ``isbn:`` label.

        Hyphens and spaces are left for ``validate_isbn``, which strips them
        itself.

        Args:
            value: The ISBN as the source wrote it.

        Returns:
            The ISBN without its label.
        """
        return cls._ISBN_LABEL_RE.sub("", value.strip()).strip()

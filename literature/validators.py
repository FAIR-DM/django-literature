"""Format-specific validators for the literature app's known identifier types.

Each function follows the Django validator protocol — raises
``django.core.exceptions.ValidationError`` for invalid values and returns
``None`` for valid ones. :func:`validate_identifier` dispatches on identifier
type and is the single entry point both ``ItemIdentifier.clean()`` and
``ItemIdentifier.save()`` use, so every write path applies the same rules.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _

from literature.choices import IdentifierType

_DOI_RE = re.compile(r"^10\.\d{4,}/\S+$")


def validate_doi(value: str) -> None:
    """Validate a DOI string.

    A valid DOI starts with ``10.`` followed by at least four digits, a
    forward slash, and at least one non-whitespace character.

    Args:
        value: The DOI string to validate.

    Raises:
        ValidationError: if the value does not match the DOI pattern.
    """
    if not _DOI_RE.match(value):
        raise ValidationError(
            _("Enter a valid DOI (e.g. 10.1000/xyz123)."),
            code="invalid_doi",
            params={"value": value},
        )


_ISBN_STRIP_RE = re.compile(r"[-\s]")


def _isbn10_valid(digits: str) -> bool | None:
    """Check *digits* against ISBN-10's shape and, only if it matches, its check digit.

    Args:
        digits: The candidate ISBN-10 with hyphens and spaces already stripped.

    Returns:
        bool | None: ``True`` if *digits* is a valid ISBN-10, ``False`` if it
        has ISBN-10's shape but the wrong check digit, ``None`` if it does
        not have ISBN-10's shape at all — the three-way return lets
        :func:`validate_isbn` tell "malformed" from "one mistyped digit"
        apart (FS-012).
    """
    if not re.match(r"^\d{9}[\dX]$", digits, re.IGNORECASE):
        return None
    values = [10 if c.upper() == "X" else int(c) for c in digits]
    return sum(v * (10 - i) for i, v in enumerate(values)) % 11 == 0


def _isbn13_valid(digits: str) -> bool | None:
    """Check *digits* against ISBN-13's shape and, only if it matches, its check digit.

    Args:
        digits: The candidate ISBN-13 with hyphens and spaces already stripped.

    Returns:
        bool | None: ``True`` if valid, ``False`` if it has ISBN-13's shape
        but the wrong check digit, ``None`` if it does not have ISBN-13's
        shape at all. See :func:`_isbn10_valid` for why the return is
        three-way rather than a plain bool.
    """
    if not re.match(r"^\d{13}$", digits):
        return None
    return (
        sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits)) % 10 == 0
    )


def validate_isbn(value: str) -> None:
    """Validate an ISBN-10 or ISBN-13 value (hyphens and spaces ignored).

    A value that matches neither shape at all and a value that matches one
    shape but carries the wrong check digit are reported apart (FS-012): the
    latter is the commonest real error — a single mistyped character — and
    the case a well-formed example helps least with.

    Args:
        value: The ISBN string to validate.

    Raises:
        ValidationError: ``invalid_isbn_checksum`` if *value* matches an ISBN-10 or ISBN-13
            shape but its check digit does not; ``invalid_isbn`` if it matches neither shape.
    """
    stripped = _ISBN_STRIP_RE.sub("", value)
    isbn10 = _isbn10_valid(stripped)
    isbn13 = _isbn13_valid(stripped)
    if isbn10 or isbn13:
        return
    if isbn10 is False or isbn13 is False:
        raise ValidationError(
            _(
                "This ISBN's check digit does not match. Check the number for a mistyped character."
            ),
            code="invalid_isbn_checksum",
            params={"value": value},
        )
    raise ValidationError(
        _("Enter a valid ISBN-10 or ISBN-13 (e.g. 978-0-306-40615-7)."),
        code="invalid_isbn",
        params={"value": value},
    )


_ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dX]$", re.IGNORECASE)


def _issn_valid(value: str) -> bool | None:
    """Check *value* against ISSN's shape and, only if it matches, its check digit.

    Args:
        value: The candidate ISSN string.

    Returns:
        bool | None: ``True`` if valid, ``False`` if it has ISSN's shape but
        the wrong check digit, ``None`` if it does not have ISSN's shape at
        all. Mirrors :func:`_isbn10_valid`'s three-way return for the same
        reason (#118).
    """
    if not _ISSN_RE.match(value):
        return None
    digits = value.replace("-", "")
    values = [10 if c.upper() == "X" else int(c) for c in digits]
    return sum(v * (8 - i) for i, v in enumerate(values)) % 11 == 0


def validate_issn(value: str) -> None:
    """Validate an ISSN string (#118).

    A valid ISSN has the format ``NNNN-NNNX`` where ``X`` is a digit or the letter X (check
    character), and the eight characters together satisfy the standard's modulo-11 checksum.
    A value that matches the shape but not the checksum is reported apart from a value that
    does not match the shape at all — the same distinction :func:`validate_isbn` already
    reports.

    Args:
        value: The ISSN string to validate.

    Raises:
        ValidationError: ``invalid_issn_checksum`` if *value* matches ISSN's shape but its
            check digit does not; ``invalid_issn`` if it does not match the shape at all.
    """
    valid = _issn_valid(value)
    if valid:
        return
    if valid is False:
        raise ValidationError(
            _(
                "This ISSN's check digit does not match. Check the number for a mistyped character."
            ),
            code="invalid_issn_checksum",
            params={"value": value},
        )
    raise ValidationError(
        _("Enter a valid ISSN (e.g. 1742-2094)."),
        code="invalid_issn",
        params={"value": value},
    )


_url_validator = URLValidator(schemes=["http", "https", "ftp"])


def validate_url(value: str) -> None:
    """Validate an HTTP, HTTPS, or FTP URL using Django's URLValidator.

    Args:
        value: The URL string to validate.

    Raises:
        ValidationError: if the value is not a valid absolute URL with an
            allowed scheme.
    """
    try:
        _url_validator(value)
    except ValidationError as err:
        raise ValidationError(
            _("Enter a valid URL (http, https, or ftp)."),
            code="invalid_url",
            params={"value": value},
        ) from err


_NUMERIC_RE = re.compile(r"^\d+$")
_PMCID_RE = re.compile(r"^(PMC)?\d+$")


def validate_pmid(value: str) -> None:
    """Validate a PubMed ID (PMID): must be a non-empty numeric string.

    Args:
        value: The PMID string to validate.

    Raises:
        ValidationError: if the value contains non-digit characters.
    """
    if not _NUMERIC_RE.match(value):
        raise ValidationError(
            _("Enter a valid PubMed ID (numeric string, e.g. 12345678)."),
            code="invalid_pmid",
            params={"value": value},
        )


def validate_pmcid(value: str) -> None:
    """Validate a PubMed Central ID (PMCID).

    Accepts the canonical NCBI form (``PMC`` followed by digits, e.g.
    ``PMC2728067``) and a bare digit string, which is how some sources record
    the same identifier.

    Args:
        value: The PMCID string to validate.

    Raises:
        ValidationError: if the value is neither form.
    """
    if not _PMCID_RE.match(value):
        raise ValidationError(
            _("Enter a valid PubMed Central ID (e.g. PMC2728067 or 2728067)."),
            code="invalid_pmcid",
            params={"value": value},
        )


_IDENTIFIER_VALIDATORS: dict[str, Callable[[str], None]] = {
    IdentifierType.DOI: validate_doi,
    IdentifierType.ISBN: validate_isbn,
    IdentifierType.ISSN: validate_issn,
    IdentifierType.URL: validate_url,
    IdentifierType.PMID: validate_pmid,
    IdentifierType.PMCID: validate_pmcid,
}


def validate_identifier(identifier_type: str, value: str) -> None:
    """Validate *value* against the format rules for *identifier_type*.

    Unknown identifier types carry no format constraint and pass through
    unvalidated, so nothing is lost. Delegates to the matching ``validate_*``
    function, which raises ``ValidationError`` for a malformed value.

    Args:
        identifier_type: The identifier type to look up a validator for.
        value: The identifier value to validate.
    """
    validator = _IDENTIFIER_VALIDATORS.get(identifier_type)
    if validator is not None:
        validator(value)

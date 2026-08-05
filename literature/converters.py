"""CSL JSON serialization and deserialization for the literature app.

Provides bidirectional conversion between Django ``Item`` model instances
(with related ``ItemName``, ``ItemDate``, ``ItemIdentifier`` records) and
CSL JSON 1.0.2 Python dicts.

Public API:
    to_csl_json(item)         — serialize Item → CSL JSON dict
    from_csl_json(data)       — deserialize CSL JSON dict → saved Item
    from_csl_json_list(data)  — batch version of from_csl_json

Reference: https://resource.citationstyles.org/schema/v1.0/input/json/csl-data.json
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Iterator
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from literature.choices import DateType, IdentifierType, ItemType, NameRole
from literature.utils.date import parse_date_parts

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Field name mappings
# ---------------------------------------------------------------------------

# Django field name → CSL JSON key
# Most fields follow a snake_case → hyphen-case pattern; exceptions listed here.
_DJANGO_TO_CSL: dict[str, str] = {
    "citation_key": "citation-key",  # exported as both "citation-key" and "id"
    "title_short": "title-short",
    "original_title": "original-title",
    "container_title": "container-title",
    "container_title_short": "container-title-short",
    "collection_title": "collection-title",
    "volume_title": "volume-title",
    "volume_title_short": "volume-title-short",
    "part_title": "part-title",
    "reviewed_title": "reviewed-title",
    "reviewed_genre": "reviewed-genre",
    "publisher_place": "publisher-place",
    "original_publisher": "original-publisher",
    "original_publisher_place": "original-publisher-place",
    "event_title": "event-title",
    "event_place": "event-place",
    "page_first": "page-first",
    "number_of_pages": "number-of-pages",
    "number_of_volumes": "number-of-volumes",
    "chapter_number": "chapter-number",
    "collection_number": "collection-number",
    "call_number": "call-number",
    "archive_place": "archive-place",
    # CSL JSON uses underscores for these two
    "archive_collection": "archive_collection",
    "archive_location": "archive_location",
    "journal_abbreviation": "journalAbbreviation",
    "citation_label": "citation-label",
    "citation_number": "citation-number",
    "first_reference_note_number": "first-reference-note-number",
    "year_suffix": "year-suffix",
}

# CSL JSON key → Django field name (for import)
_CSL_TO_DJANGO: dict[str, str] = {v: k for k, v in _DJANGO_TO_CSL.items()}
# Additional mappings for deprecated / alternate CSL keys
_CSL_TO_DJANGO.update(
    {
        "id": "citation_key",
        "shortTitle": "title_short",  # deprecated CSL key
        "event": "event_title",  # deprecated CSL key
    }
)

# Fields that are NOT scalar CSL JSON fields (handled separately)
_SKIP_FIELDS = frozenset(
    {
        "id",
        "citation_key",
        "type",
        "categories",
        "custom",
        "created",
        "modified",
        # These are handled via related models
        *[r.value for r in NameRole],
        *[d.value for d in DateType],
        *[i.value for i in IdentifierType],
    }
)

# Known CSL identifier top-level keys
_KNOWN_IDENTIFIER_TYPES = frozenset(i.value for i in IdentifierType)

# CSL name-variable keys that map to NameRole values
_NAME_VARIABLE_KEYS = frozenset(r.value for r in NameRole)

# CSL date-variable keys that map to DateType values
_DATE_VARIABLE_KEYS = frozenset(d.value for d in DateType)


def _csl_key_to_django_field(csl_key: str) -> str | None:
    """Convert a CSL JSON field name to the corresponding Django model field name.

    Returns None if the key should not be mapped to a scalar Item field.
    """
    # Direct mapping table lookup
    if csl_key in _CSL_TO_DJANGO:
        return _CSL_TO_DJANGO[csl_key]
    # Most CSL hyphenated keys → snake_case by replacing hyphens
    # e.g. "publisher-place" → "publisher_place"
    candidate = csl_key.replace("-", "_")
    return candidate


def _django_field_to_csl_key(field_name: str) -> str:
    """Convert a Django model field name to its CSL JSON key."""
    if field_name in _DJANGO_TO_CSL:
        return _DJANGO_TO_CSL[field_name]
    # Default: replace underscores with hyphens
    return field_name.replace("_", "-")


def _partial_date_to_parts(pd: Any) -> list[int]:
    """Convert a PartialDate to a CSL JSON date-parts single array.

    Returns a list of 1-3 integers based on the PartialDate's precision.
    PartialDate.YEAR=0, MONTH=1, DAY=2.
    """
    from partial_date import PartialDate

    date_obj = pd.date if hasattr(pd, "date") else pd
    precision = getattr(pd, "precision", PartialDate.DAY)

    if precision == PartialDate.YEAR:
        return [date_obj.year]
    elif precision == PartialDate.MONTH:
        return [date_obj.year, date_obj.month]
    else:
        return [date_obj.year, date_obj.month, date_obj.day]


def _name_to_dict(name: Any) -> dict[str, Any]:
    """Convert a Name instance to a CSL JSON name object (omitting empty fields)."""
    result: dict[str, Any] = {}
    if name.family:
        result["family"] = name.family
    if name.given:
        result["given"] = name.given
    if name.dropping_particle:
        result["dropping-particle"] = name.dropping_particle
    if name.non_dropping_particle:
        result["non-dropping-particle"] = name.non_dropping_particle
    if name.suffix:
        result["suffix"] = name.suffix
    if name.literal:
        result["literal"] = name.literal
    if name.comma_suffix:
        result["comma-suffix"] = name.comma_suffix
    if name.static_ordering:
        result["static-ordering"] = name.static_ordering
    if name.parse_names:
        result["parse-names"] = name.parse_names
    return result


# ---------------------------------------------------------------------------
# to_csl_json
# ---------------------------------------------------------------------------


def to_csl_json(item: Any) -> dict[str, Any]:
    """Serialize a saved Item instance to a CSL JSON 1.0.2 compatible dict.

    Args:
        item: A saved ``Item`` model instance (must have a primary key).

    Returns:
        A Python dict conforming to the CSL JSON 1.0.2 schema.

    Guarantees:
        - Always contains ``"id"`` (= ``item.citation_key``) and ``"type"``.
        - Omits blank/null optional fields.
        - Name arrays are ordered by ``ItemName.order`` within each role.
        - Known identifier types (DOI, ISBN, ISSN, PMID, PMCID, URL) are
          top-level keys; unknown types are placed in ``custom``.
        - String-or-number CSL fields are always exported as strings.

    CSL JSON mapping: top-level item object
    """
    from literature.models import ItemName

    result: dict[str, Any] = {
        "id": item.citation_key,
        "type": item.type,
    }

    # --- Scalar fields ---
    # Iterate over the Item model's fields and export non-empty values
    scalar_skip = {
        "id",
        "pk",
        "citation_key",
        "type",
        "categories",
        "custom",
        "created",
        "modified",
    }
    for field in item._meta.get_fields():
        if not hasattr(field, "attname"):
            continue  # Skip relation fields
        fname = field.name
        if fname in scalar_skip:
            continue
        value = getattr(item, fname, None)
        if value is None or value == "" or value is False:
            continue
        csl_key = _django_field_to_csl_key(fname)
        result[csl_key] = value

    # --- JSONFields (categories, custom) ---
    if item.categories:
        result["categories"] = item.categories

    # We'll merge custom identifiers with existing custom below
    _custom: dict[str, Any] = {}
    if item.custom:
        _custom.update(item.custom)

    # --- Identifiers ---
    for ident in item.item_identifiers.all():
        if ident.type in _KNOWN_IDENTIFIER_TYPES:
            result[ident.type] = ident.value
        else:
            _custom[ident.type] = ident.value

    if _custom:
        result["custom"] = _custom

    # --- Names ---
    from literature.models import ItemName  # noqa: F811

    roles_present: dict[str, list[dict]] = {}
    for item_name in ItemName.objects.filter(item=item).order_by("role", "order"):
        role = item_name.role
        name_dict = _name_to_dict(item_name.name)
        if name_dict:  # skip entirely empty name objects
            roles_present.setdefault(role, []).append(name_dict)

    result.update(roles_present)

    # --- Dates ---
    for item_date in item.item_dates.all():
        date_obj: dict[str, Any] = {}

        if item_date.begin is not None:
            parts = [_partial_date_to_parts(item_date.begin)]
            if item_date.end is not None:
                parts.append(_partial_date_to_parts(item_date.end))
            date_obj["date-parts"] = parts
        elif item_date.raw_date_parts:
            date_obj["date-parts"] = item_date.raw_date_parts

        if item_date.literal:
            date_obj["literal"] = item_date.literal
        if item_date.season:
            date_obj["season"] = item_date.season
        if item_date.circa:
            date_obj["circa"] = item_date.circa

        if date_obj:
            result[item_date.date_type] = date_obj

    return result


# ---------------------------------------------------------------------------
# from_csl_json
# ---------------------------------------------------------------------------


def _generate_dedup_suffix(base: str) -> Iterator[str]:
    """Generate successive deduplication suffixes: b, c, ..., z, aa, ab, ..., zz, aaa, ...

    An odometer over increasing lengths, unbounded and never repeating (issue #41): past the
    676th two-letter suffix this used to start the two-letter product over from 'aa' again, so
    ``_resolve_citation_key`` never terminated past 701 items sharing one base key. The first 701
    values (single letters, then every two-letter pair) are unchanged, since
    ``tests/test_converters.py`` pins them.
    """
    # Start at 'b' (ord 98), skip 'a' which would be confusingly close to base
    chars = "bcdefghijklmnopqrstuvwxyz"
    # Single-letter suffixes: b, c, ..., z
    yield from chars
    # Two-letter suffixes, then three, then four, ... — never repeating.
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    length = 2
    while True:
        for combo in itertools.product(alphabet, repeat=length):
            yield "".join(combo)
        length += 1


def _resolve_citation_key(data: dict) -> str:
    """Extract and deduplicate the citation key from a CSL JSON dict.

    Raises ValidationError if both citation-key and id are absent/empty.
    """
    from literature.models import Item

    raw_key = data.get("citation-key") or str(data.get("id", ""))
    if not raw_key:
        raise ValidationError(_("CSL JSON item missing both 'citation-key' and 'id' fields"))

    # Check for conflicts and deduplicate
    if not Item.objects.filter(citation_key=raw_key).exists():
        return raw_key

    gen = _generate_dedup_suffix(raw_key)
    while True:
        suffix = next(gen)
        candidate = f"{raw_key}{suffix}"
        if not Item.objects.filter(citation_key=candidate).exists():
            return candidate


def _import_name_variable(data: dict, item: Any, role: str, order: int) -> None:
    """Create or get a Name and link it to item with the given role and order."""
    from literature.models import ItemName, Name

    # Handle string names (stored as literal)
    name_data = {"literal": data} if isinstance(data, str) else data

    family = name_data.get("family", "")
    given = name_data.get("given", "")
    literal = name_data.get("literal", "")
    dropping_particle = name_data.get("dropping-particle", "")
    non_dropping_particle = name_data.get("non-dropping-particle", "")
    suffix = name_data.get("suffix", "")

    # Find-or-create Name using composite lookup key
    name, _ = Name.objects.get_or_create(
        family=family,
        given=given,
        literal=literal,
        dropping_particle=dropping_particle,
        non_dropping_particle=non_dropping_particle,
        suffix=suffix,
        defaults={
            "comma_suffix": name_data.get("comma-suffix", False),
            "static_ordering": name_data.get("static-ordering", False),
            "parse_names": name_data.get("parse-names", False),
        },
    )
    name.full_clean()

    item_name = ItemName(item=item, name=name, role=role, order=order)
    item_name.full_clean()
    item_name.save()


def _import_date_variable(data: dict, item: Any, date_type: str) -> None:
    """Create an ItemDate record from a CSL JSON date-variable object."""
    from literature.models import ItemDate

    date_parts = data.get("date-parts", [])
    begin = None
    end = None
    raw_date_parts_fallback = None

    if date_parts:
        begin_parts = date_parts[0] if len(date_parts) >= 1 else []
        end_parts = date_parts[1] if len(date_parts) >= 2 else []

        begin = parse_date_parts(begin_parts)
        if begin is None and begin_parts:
            raw_date_parts_fallback = date_parts

        if end_parts:
            end = parse_date_parts(end_parts)

    item_date = ItemDate(
        item=item,
        date_type=date_type,
        begin=begin,
        end=end,
        season=data.get("season", ""),
        circa=bool(data.get("circa", False)),
        literal=data.get("literal", "") or "",
        raw=data.get("raw", "") or "",
        raw_date_parts=raw_date_parts_fallback,
    )
    item_date.full_clean()
    item_date.save()


def from_csl_json(data: dict) -> Any:
    """Deserialize a CSL JSON dict into a new saved Item with all related records.

    Args:
        data: A Python dict containing CSL JSON data for a single bibliographic item.

    Returns:
        A saved ``Item`` instance with all related ``ItemName``, ``ItemDate``,
        and ``ItemIdentifier`` records created.

    Raises:
        ValidationError: If ``data["type"]`` is missing or not a recognized CSL type.
        ValidationError: If both ``data["citation-key"]`` and ``data["id"]`` are absent.

    Behavior:
        1. Validates ``type`` (required, must be in ItemType choices).
        2. Resolves ``citation_key`` from ``citation-key`` → ``id`` fallback.
        3. Deduplicates citation key by appending suffix b→c→…→z→aa→ab…
        4. Maps all CSL JSON scalar fields to Django model fields.
        5. Creates Name/ItemName records (find-or-create by composite key).
        6. Creates ItemDate records (parse date-parts → PartialDate; fallback to raw_date_parts).
        7. Creates ItemIdentifier records (known types top-level; unknown from custom with warning).
        8. Calls full_clean() on every model instance before saving.

    CSL JSON mapping: top-level item object → Item + related records
    """
    from literature.models import Item, ItemIdentifier

    # --- Validate type ---
    csl_type = data.get("type")
    if not csl_type:
        raise ValidationError(_("CSL JSON item missing required 'type' field"))
    if csl_type not in ItemType.values:
        raise ValidationError(_("Unknown CSL JSON item type: '{type}'").format(type=csl_type))

    # --- Resolve citation key ---
    citation_key = _resolve_citation_key(data)

    # --- Build scalar field dict ---
    item_fields: dict[str, Any] = {
        "citation_key": citation_key,
        "type": csl_type,
    }

    # Fields that are NOT scalar Item fields
    non_scalar = (
        _NAME_VARIABLE_KEYS
        | _DATE_VARIABLE_KEYS
        | _KNOWN_IDENTIFIER_TYPES
        | {"type", "citation-key", "id", "shortTitle", "event"}
    )

    # Collect all Item field names for validation
    from literature.models import Item  # noqa: F811

    valid_item_fields = {f.name for f in Item._meta.get_fields() if hasattr(f, "attname")}

    for csl_key, value in data.items():
        if csl_key in non_scalar:
            continue
        if csl_key in ("categories", "custom"):
            item_fields[csl_key] = value
            continue

        django_field = _csl_key_to_django_field(csl_key)
        if django_field and django_field in valid_item_fields:
            # Convert numbers to strings for string-or-number fields
            if isinstance(value, (int, float)) and django_field not in ("categories", "custom"):
                value = str(value)
            item_fields[django_field] = value

    # Handle deprecated aliases
    if "shortTitle" in data and "title_short" not in item_fields:
        item_fields["title_short"] = data["shortTitle"]
    if "event" in data and "event_title" not in item_fields:
        item_fields["event_title"] = data["event"]

    # --- Create Item ---
    item = Item(**item_fields)
    item.full_clean(exclude=["citation_key"])  # citation_key is app-level unique, not DB unique
    item.save()

    # --- Names ---
    for role_key in _NAME_VARIABLE_KEYS:
        names_data = data.get(role_key, [])
        for order, name_data in enumerate(names_data):
            _import_name_variable(name_data, item, role_key, order)

    # --- Dates ---
    for date_key in _DATE_VARIABLE_KEYS:
        date_data = data.get(date_key)
        if date_data is not None:
            _import_date_variable(date_data, item, date_key)

    # --- Identifiers ---
    # Known types from top-level keys
    for id_type in _KNOWN_IDENTIFIER_TYPES:
        value = data.get(id_type)
        if value:
            ident = ItemIdentifier(item=item, type=id_type, value=str(value))
            ident.full_clean()
            ident.save()

    # Unknown identifiers from custom dict
    custom_data = data.get("custom") or {}
    if isinstance(custom_data, dict):
        for key, value in custom_data.items():
            if key not in _KNOWN_IDENTIFIER_TYPES and isinstance(value, str):
                logger.warning("Unknown identifier type '%s' for item '%s'", key, citation_key)
                ident = ItemIdentifier(item=item, type=key, value=value)
                ident.full_clean()
                ident.save()

    return item


# ---------------------------------------------------------------------------
# from_csl_json_list
# ---------------------------------------------------------------------------


def from_csl_json_list(data: list[dict]) -> list[Any]:
    """Import a list of CSL JSON dicts, skipping invalid items with warnings.

    Args:
        data: A Python list of CSL JSON dicts (one per bibliographic item).

    Returns:
        A list of saved ``Item`` instances for all successfully imported items.
        Invalid items (raising ``ValidationError``) are skipped and logged
        via ``logger.warning()``.

    Behavior:
        Calls ``from_csl_json()`` for each item in the list. Items that fail
        validation are skipped and their errors are emitted as warnings.
        Successfully imported items are returned in input order.
    """
    results = []
    for item_data in data:
        try:
            item = from_csl_json(item_data)
            results.append(item)
        except ValidationError as exc:
            logger.warning("Skipping invalid CSL JSON item: %s", exc)
    return results

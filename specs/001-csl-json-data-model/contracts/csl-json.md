# Contract: CSL JSON Serialization/Deserialization

**Feature**: 001-csl-json-data-model
**Date**: 2026-04-09

## Overview

This contract defines the public interface for converting between Django `literature` models and CSL JSON dictionaries. The module `literature.converters` provides two primary functions: `to_csl_json()` (export) and `from_csl_json()` (import).

## Public API

### `to_csl_json(item: Item) -> dict`

Serialize a saved `Item` instance (with all related `ItemName`, `ItemDate`, and `ItemIdentifier` records) to a CSL JSON-compatible Python dictionary.

**Input**: A saved `Item` model instance (must have a primary key).

**Output**: A Python `dict` conforming to the CSL JSON 1.0.2 schema.

**Guarantees**:

- Output dict always contains `"id"` (populated from `item.citation_key`) and `"type"` fields
- All non-empty scalar fields on `Item` are included with their CSL JSON field names
- CSL field name mapping: snake_case Django fields → hyphenated/camelCase CSL fields (e.g., `container_title` → `container-title`, `journal_abbreviation` → `journalAbbreviation`)
- Name-variable fields: exported as arrays of name objects, ordered by `ItemName.order` within each role
- Name objects include only non-empty fields (no `"family": ""` entries)
- Date-variable fields: exported as date objects with `date-parts`, `literal`, `season`, `circa` as applicable
- Date `date-parts` arrays reflect the precision of the stored `PartialDate` (year-only → `[2019]`, year-month → `[2019, 8]`, full → `[2019, 8, 16]`)
- Identifier fields with known types (DOI, ISBN, ISSN, PMID, PMCID, URL) are exported as top-level CSL JSON properties
- Identifiers with unknown types are placed in `custom` object
- `categories` and `custom` JSONField values are included directly if non-null
- Empty/blank fields are omitted from output (no `"abstract": ""`)
- String-or-number CSL fields (volume, issue, etc.) are exported as strings

**Example output**:

```json
{
  "id": "Jennings2019b",
  "type": "article-journal",
  "title": "A new compositionally based thermal conductivity model",
  "container-title": "Geophysical Journal International",
  "volume": "219",
  "issue": "2",
  "page": "1377-1394",
  "author": [
    {"family": "Jennings", "given": "S"},
    {"family": "Hasterok", "given": "D"},
    {"family": "Payne", "given": "J"}
  ],
  "issued": {
    "date-parts": [[2019, 8, 16]]
  },
  "DOI": "10.1093/gji/ggz376",
  "ISSN": "0956-540X",
  "language": "en"
}
```

---

### `from_csl_json(data: dict) -> Item`

Deserialize a CSL JSON dictionary into a new `Item` instance with all related records.

**Input**: A Python `dict` containing CSL JSON data for a single item.

**Output**: A saved `Item` instance with all related `ItemName`, `ItemDate`, and `ItemIdentifier` records created.

**Preconditions** (validation errors raised if violated):

- `data["type"]` must be present and must be a recognized CSL JSON item type (from the 44-type enum)
- At least one of `data["citation-key"]` or `data["id"]` must be present and non-empty

**Behavior**:

1. **Citation key resolution**:
   - Use `data["citation-key"]` if present
   - Fall back to `str(data["id"])` if `citation-key` absent
   - Both absent/empty → raise `ValidationError`

2. **Citation key deduplication**:
   - If resolved key conflicts with existing `Item.citation_key`, append letter suffix: `"b"`, `"c"`, `"d"`, ..., `"z"`, `"aa"`, `"ab"`, etc.
   - Never overwrite existing records

3. **Type validation**:
   - `data["type"]` must match one of the 44 recognized CSL types
   - Unrecognized type → raise `ValidationError`

4. **Scalar fields**:
   - Map CSL JSON field names to Django field names (hyphenated → snake_case, camelCase → snake_case)
   - String-or-number values converted to strings via `str()`
   - Missing optional fields → blank/null (no error)

5. **Name-variable fields**:
   - For each CSL name-variable key (author, editor, etc.) present in `data`:
     - For each name object in the array:
       - Find or create a `Name` record matching the name parts
       - Create an `ItemName` linking to the item with role and order (array index)
   - Names provided as plain strings → stored with `literal` field

6. **Date-variable fields**:
   - For each CSL date-variable key (issued, accessed, etc.) present in `data`:
     - Parse `date-parts` arrays to `PartialDate` objects for `begin`/`end`
     - If parsing fails → store original in `raw_date_parts` JSONField
     - Parse `raw` strings with `python-dateutil` → `PartialDate` for `begin`
     - If `raw` parsing fails → store in `raw` CharField
     - Copy `literal`, `season`, `circa` directly

7. **Identifier fields**:
   - Extract known identifier properties (DOI, ISBN, ISSN, PMID, PMCID, URL) from top-level
   - Create `ItemIdentifier` records with appropriate type and value
   - Unknown identifier-like fields in `custom` → store with `logger.warning()` and custom type string

8. **Special fields**:
   - `categories` → stored as-is in JSONField
   - `custom` → stored as-is in JSONField
   - `keyword` → stored as-is in TextField
   - Deprecated `event` → mapped to `event_title`
   - Deprecated `shortTitle` → mapped to `title_short`

**Error handling**:

- Missing `type` → `ValidationError("CSL JSON item missing required 'type' field")`
- Unknown `type` → `ValidationError("Unknown CSL JSON item type: '{type}'")`
- Missing both `citation-key` and `id` → `ValidationError("CSL JSON item missing both 'citation-key' and 'id' fields")`
- All other fields optional — missing fields are silently skipped

---

### `from_csl_json_list(data: list[dict]) -> list[Item]`

Convenience function to import multiple CSL JSON items.

**Input**: A Python list of CSL JSON dictionaries.

**Output**: A list of saved `Item` instances.

**Behavior**: Calls `from_csl_json()` for each item. Collects and returns all successfully imported items. Items that fail validation are skipped with `logger.warning()` and excluded from the result list.

---

## Round-Trip Fidelity (FR-008)

The following invariant must hold for any valid CSL JSON item:

```python
original = {...}  # Valid CSL JSON dict
item = from_csl_json(original)
exported = to_csl_json(item)

# All fields present in 'original' must be present in 'exported' with equivalent values
# (string representations may differ for number values: 42 → "42")
```

**Known representation changes** (acceptable, not data loss):

- Number values in string-or-number fields become strings: `42` → `"42"`
- `citation-key` and `id` are both populated from the same `citation_key` value
- Name/date ordering is preserved via `ItemName.order` / explicit field order
- The `event` deprecated field is imported but exported as `event-title`
- The `shortTitle` deprecated field is imported but exported as `title-short`

---

## Error Types

All validation errors use Django's `django.core.exceptions.ValidationError` with descriptive messages.

| Error Condition | Message Pattern |
|---|---|
| Missing `type` | `"CSL JSON item missing required 'type' field"` |
| Unknown `type` | `"Unknown CSL JSON item type: '{value}'"` |
| Missing both `citation-key` and `id` | `"CSL JSON item missing both 'citation-key' and 'id' fields"` |

## Logging

- Unknown identifier types during import: `logger.warning("Unknown identifier type '%s' for item '%s'", type, citation_key)`
- Import failures in batch: `logger.warning("Failed to import CSL JSON item: %s", error_message)`

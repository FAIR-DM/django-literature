# Research: CSL JSON Data Model and Conversion

**Feature**: 001-csl-json-data-model
**Date**: 2026-04-09

## R1: CSL JSON Schema Structure and Field Taxonomy

### Decision

Model the CSL JSON 1.0.2 schema using four field categories mapped to Django model strategies:

1. **Scalar fields** (string, number, boolean) → columns on `Item` model
2. **Name-variable fields** (arrays of name objects) → `Name` model + `ItemName` through-model
3. **Date-variable fields** (structured date objects) → `ItemDate` model with `PartialDateField`
4. **Identifier fields** (DOI, ISBN, etc.) → `ItemIdentifier` model

### Rationale

The CSL JSON schema (`csl-data.json`) defines a flat item object with ~80 properties. These properties fall into distinct categories by type:

- **String-only fields** (42): `abstract`, `annote`, `archive`, `archive_collection`, `archive_location`, `archive-place`, `authority`, `call-number`, `citation-label`, `container-title`, `container-title-short`, `dimensions`, `division`, `DOI`, `event-title`, `event-place`, `genre`, `ISBN`, `ISSN`, `jurisdiction`, `keyword`, `language`, `medium`, `note`, `original-publisher`, `original-publisher-place`, `original-title`, `part-title`, `PMCID`, `PMID`, `publisher`, `publisher-place`, `references`, `reviewed-genre`, `reviewed-title`, `scale`, `section`, `source`, `status`, `title`, `title-short`, `URL`, `version`, `volume-title`, `volume-title-short`, `year-suffix`
- **String-or-number fields** (16): `chapter-number`, `citation-number`, `collection-number`, `edition`, `first-reference-note-number`, `issue`, `locator`, `number`, `number-of-pages`, `number-of-volumes`, `page`, `page-first`, `part`, `printing`, `supplement`, `volume`
- **Name-variable fields** (27): `author`, `chair`, `collection-editor`, `compiler`, `composer`, `container-author`, `contributor`, `curator`, `director`, `editor`, `editorial-director`, `executive-producer`, `guest`, `host`, `illustrator`, `interviewer`, `narrator`, `organizer`, `original-author`, `performer`, `producer`, `recipient`, `reviewed-author`, `script-writer`, `series-creator`, `translator`
- **Date-variable fields** (6): `accessed`, `available-date`, `event-date`, `issued`, `original-date`, `submitted`
- **Special fields**: `id` (string|number, required), `type` (string enum, required), `citation-key` (string), `categories` (string array), `journalAbbreviation` (string, camelCase), `shortTitle` (string, camelCase), `custom` (object)

### Key Schema Details

**Name-variable structure** (`name-variable` definition):

```json
{
  "family": "string",
  "given": "string",
  "dropping-particle": "string",
  "non-dropping-particle": "string",
  "suffix": "string",
  "comma-suffix": "string|number|boolean",
  "static-ordering": "string|number|boolean",
  "literal": "string",
  "parse-names": "string|number|boolean"
}
```

**Date-variable structure** (`date-variable` definition):

```json
{
  "date-parts": [[year, month?, day?], [year, month?, day?]?],
  "season": "string|number",
  "circa": "string|number|boolean",
  "literal": "string",
  "raw": "string"
}
```

- `date-parts` is an array of 1-2 arrays, each containing 1-3 elements (year, optional month, optional day)
- Two date-parts arrays represent a range (e.g., conference start/end)
- `season` and `circa` are metadata about the date
- `literal` is a free-text fallback when structured dates can't represent the value
- `raw` is an unparsed date string that processors may attempt to parse

**Item types** (45 total in CSL 1.0.2): `article`, `article-journal`, `article-magazine`, `article-newspaper`, `bill`, `book`, `broadcast`, `chapter`, `classic`, `collection`, `dataset`, `document`, `entry`, `entry-dictionary`, `entry-encyclopedia`, `event`, `figure`, `graphic`, `hearing`, `interview`, `legal_case`, `legislation`, `manuscript`, `map`, `motion_picture`, `musical_score`, `pamphlet`, `paper-conference`, `patent`, `performance`, `periodical`, `personal_communication`, `post`, `post-weblog`, `regulation`, `report`, `review`, `review-book`, `software`, `song`, `speech`, `standard`, `thesis`, `treaty`, `webpage`

### Alternatives Considered

- **Single JSON blob**: Rejected — violates Constitution III (Data Integrity), makes querying impossible
- **Fully normalized (separate table per field type)**: Rejected — over-engineering for string/number fields that don't benefit from normalization
- **Identifier fields as Item columns**: Considered but rejected — the spec requires flexible identifier types, and a dedicated model is cleaner for querying and extensibility

---

## R2: `django-partial-date` Package for Date Handling

### Decision

Use `django-partial-date` (ktowen/django_partial_date) for storing CSL JSON dates with variable precision (year-only, year-month, full date).

### Rationale

CSL JSON dates commonly have partial precision — many bibliographic entries have only a year, or a year-month. The `django-partial-date` package provides:

- `PartialDateField`: Django model field storing dates with precision metadata
- `PartialDate` class with precision levels: `YEAR=0`, `MONTH=1`, `DAY=2`
- Database representation: `DateTimeField` internally, with seconds used to encode precision level
- Accepts `None`, `PartialDate` objects, or formatted strings (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`)
- Supports comparison operators (`__eq__`, `__gt__`, `__ge__`)
- String formatting via `.format(year_fmt, month_fmt, day_fmt)`
- Access to underlying `datetime.date` via `.date` property
- Database-agnostic (uses standard `DateTimeField` internal type)

**Mapping CSL date-parts to PartialDate**:

- `[2019]` → `PartialDate("2019")` (precision=YEAR)
- `[2019, 8]` → `PartialDate("2019-08")` (precision=MONTH)
- `[2019, 8, 16]` → `PartialDate("2019-08-16")` (precision=DAY)

**Limitations**:

- Uses `six` for Python 2/3 compat (outdated but functional)
- Last updated 5 years ago — stable but unmaintained
- No support for negative years (BCE dates) — acceptable for bibliographic use
- Precision is stored in the seconds field of the datetime, which is a clever hack but somewhat fragile

### Alternatives Considered

- **Plain `DateField` with separate precision flag**: More work, less elegant, same result
- **Custom implementation**: Unnecessary given the package exists and works

---

## R3: Ordering Strategy for Name-Variables

### Decision

Use `django-ordered-model` for ordered through-model (`ItemName`) with `order_with_respect_to` scoped to both the item AND the role type.

### Rationale

CSL JSON name-variable arrays are ordered — author order matters (first author, second author, etc.), and this ordering is per-role-per-item (the ordering of authors is independent of the ordering of editors on the same item).

`django-ordered-model` provides:

- `OrderedModel` base class with automatic `order` field (PositiveIntegerField)
- `order_with_respect_to` for scoped ordering (supports tuples for multi-field scoping)
- Methods: `up()`, `down()`, `top()`, `bottom()`, `to(n)`, `swap()`, `above()`, `below()`
- `OrderedManyToManyField` for correct queryset ordering
- Admin integration via `OrderedTabularInline`/`OrderedStackedInline`
- Django 3.x-5.x and Python 3.10-3.12 compatibility
- Active maintenance (3.8.0-alpha released Nov 2024)

**Through-model pattern** (from django-ordered-model docs):

```python
class ItemName(OrderedModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    name = models.ForeignKey(Name, on_delete=models.CASCADE)
    role = models.CharField(choices=NAME_ROLE_CHOICES)
    order_with_respect_to = ('item', 'role')

    class Meta:
        ordering = ('item', 'role', 'order')
```

This ensures names are ordered independently per role per item — exactly matching CSL JSON semantics where `author: [A, B, C]` and `editor: [D, E]` have separate orderings.

### Alternatives Considered

- **`django-sortedm2m`**: Simpler API but doesn't support through-model scoped ordering — it orders the entire M2M relationship globally, not per-role. Incompatible with our requirement to order names independently by role type.
- **Manual `PositiveIntegerField`**: Works but requires manual gap management, no admin integration, more boilerplate. `django-ordered-model` handles all edge cases.
- **`Meta.ordering` only**: Doesn't provide reordering operations or admin integration.

---

## R4: Identifier Storage Strategy

### Decision

Store identifiers in a dedicated `ItemIdentifier` model with `type` (CharField with choices) and `value` (CharField). CSL JSON identifier fields (DOI, ISBN, ISSN, PMID, PMCID, URL) are top-level properties in the schema, but we normalize them into a relational model for flexibility and queryability.

### Rationale

The CSL JSON schema stores identifiers as top-level string properties on the item object:

```json
{
  "DOI": "10.1093/gji/ggz376",
  "ISBN": "978-3-16-148410-0",
  "ISSN": "0956-540X",
  "PMID": "23842776",
  "PMCID": "PMC3731681",
  "URL": "http://example.com/paper"
}
```

Additionally, `call-number` is a string field that functions as a library identifier. Other identifier-like fields (`archive_location`, `number`) have different semantics.

**Design decisions**:

- Known identifier types are enumerated as `TextChoices` for the `type` field
- The `type` field uses `max_length` sufficient for custom types, NOT restricted to choices only — per FR-017, unknown identifier types must be stored with a warning, not rejected
- `value` field uses `CharField(max_length=500)` to accommodate long URLs
- Unique constraint on `(item, type)` prevents duplicate identifier types per item
- On CSL JSON export, identifier values are mapped back to their top-level CSL field names
- On CSL JSON import, top-level identifier fields are extracted and stored as `ItemIdentifier` records, plus `call-number` is stored as identifier type `call-number`

### Alternatives Considered

- **Columns on Item model**: Simpler but inflexible — can't add new identifier types without migrations, harder to query across types
- **JSONField**: Violates Constitution III — identifiers should be queryable relational data
- **Separate model per identifier type**: Massive over-engineering for simple key-value pairs

---

## R5: `citation_key` vs `id` vs `citation-label` Semantics

### Decision

Map our `citation_key` field to CSL JSON `citation-key`. On import, prefer `citation-key`; fall back to `id` if absent. On export, populate CSL `id` from `citation_key`. Enforce uniqueness at application level, not database level.

### Rationale

The CSL 1.0.2 specification defines three distinct identifier-like fields:

1. **`id`** (required by schema): A processor-internal session-scoped lookup key used by citeproc's `retrieveItem()`. No inherent bibliographic meaning — it's whatever the calling application needs for its session. The schema requires it (`"required": ["type", "id"]`).

2. **`citation-key`**: The BibTeX entrykey-style reference handle used in `\cite{Smith2009}` and `[@Smith2009]` in-document citation syntax. Defined in CSL 1.0.2 Appendix IV as "identifier of the item in the input data file (analogous to BibTeX entrykey)". This is the meaningful, persistent identifier that humans use.

3. **`citation-label`**: A processor-generated output label (e.g., "Ferr78") — NOT a storage field. Generated by citeproc during rendering.

**Our `citation_key` field**:

- Maps to CSL `citation-key` (the human-meaningful handle)
- Required, db-indexed, CharField
- Uniqueness enforced at application level (not DB UNIQUE constraint) to support multi-library/multi-tenant deployments
- On import: `citation-key` preferred → `id` fallback → both absent = validation error
- On import: duplicates resolved by letter suffix (`Smith2009` → `Smith2009b`)
- On export: CSL `id` populated from `citation_key`

### Alternatives Considered

- **Map to CSL `id`**: Incorrect — `id` is session-scoped, not a persistent bibliographic handle
- **DB UNIQUE constraint**: Prevents multi-tenant usage where same key may exist across libraries
- **Auto-generate from title/author/year**: Fragile, non-deterministic, violates user expectations

---

## R6: CSL JSON `custom` Field Handling

### Decision

Store the CSL JSON `custom` field as a Django `JSONField` on the `Item` model. This is the only field using `JSONField` for core storage.

### Rationale

The CSL JSON schema explicitly defines `custom` as an arbitrary key-value object:

```json
{
  "custom": {
    "title": "Custom key-value pairs.",
    "type": "object",
    "description": "Used to store additional information that does not have a designated CSL JSON field."
  }
}
```

This field is inherently unstructured — it's an escape hatch for data that doesn't fit the standard schema. Attempting to normalize it would be futile and contrary to its purpose. `JSONField` is the correct representation.

Django's `JSONField` is database-agnostic since Django 3.1 (uses `json` column type on SQLite, `jsonb` on PostgreSQL). This satisfies the database-agnostic constraint.

### Alternatives Considered

- **Ignore `custom` field**: Violates round-trip fidelity (FR-008)
- **Flat text field with manual JSON serialization**: More fragile, no query support
- **Separate key-value model**: Over-engineering for arbitrary data

---

## R7: Date Handling — `python-dateutil` for Raw Date Parsing

### Decision

Use `python-dateutil` for parsing CSL JSON `raw` date strings and other loosely-formatted date inputs. Convert parsed results to `PartialDate` objects for storage.

### Rationale

CSL JSON dates can include a `raw` field containing unparsed date strings that processors may attempt to parse (e.g., "August 2019", "2019-08", "16th August 2019"). `python-dateutil`'s `parser.parse()` handles a wide variety of date formats with fuzzy parsing.

**Integration with `django-partial-date`**:

1. Parse raw string with `dateutil.parser.parse()` to get a `datetime`
2. Determine precision from the original string (e.g., "2019" → YEAR, "Aug 2019" → MONTH)
3. Create `PartialDate(parsed_date.date(), precision=determined_precision)`
4. Store in `PartialDateField`

**Fallback**: If `python-dateutil` cannot parse the string, store it as `literal` on the `ItemDate` model.

### Alternatives Considered

- **Manual regex parsing**: Handles fewer formats, more maintenance burden
- **Standard library `datetime.strptime`**: Requires known format strings, can't handle fuzzy input
- **Ignore `raw` field**: Loses data from some CSL JSON sources

---

## R8: Database-Agnostic Design Decisions

### Decision

All models use only database-agnostic Django field types. No `ArrayField`, no `HStoreField`. `JSONField` only for `custom` and date raw fallback.

### Rationale

The user explicitly requires database-agnostic design. Key implications:

- **String-or-number CSL fields** (e.g., `volume`, `issue`, `edition`): Store as `CharField`. CSL JSON allows both `"42"` and `42` for these fields. `CharField` handles both by converting numbers to strings on import. On export, we emit strings (which is valid CSL JSON — the schema accepts both types).
- **`categories`** (string array): Could use `JSONField` or a separate M2M model. Since categories are a simple list and not a frequently-queried field, we'll use `JSONField` for now. If categories become important for filtering, a dedicated model can be added later.
- **`number-of-pages`, `number-of-volumes`**: Store as `CharField` since CSL JSON allows string-or-number. The old project used `PositiveIntegerField` but this loses string values like "xii + 340" that appear in practice.
- **All date fields**: Use `PartialDateField` from `django-partial-date` which stores as `DateTimeField` internally — fully database-agnostic.

### Alternatives Considered

- **PostgreSQL `ArrayField` for categories**: Not agnostic
- **`IntegerField` for numeric CSL fields**: Loses string values that are valid CSL JSON
- **Separate categories model**: Over-engineering for this feature

---

## R9: Old Project Analysis — Lessons Learned

### Decision

Use the old `django-literature-old` project as reference for field coverage and CSL JSON mapping, but redesign the architecture based on our research findings.

### Rationale

**What the old project did well**:

- Comprehensive scalar field coverage on `LiteratureItem` (all CSL JSON string/number fields present)
- `Person` model with all CSL name-variable parts (family, given, particles, suffix, literal)
- `PersonRole` as ordered through-model using `django-ordered-model`
- `CSLDate` model with `PartialDateField` for start/end dates
- `Identifier` model with type choices
- Bidirectional CSL JSON conversion (`to_csl_json()` / `from_csl_json()`)
- Grouped CSL type choices for form UX

**What we'll change**:

- **Model naming**: `LiteratureItem` → `Item` (shorter, clearer within the `literature` app namespace), `Person` → `Name` (matches CSL spec terminology "name-variable"), `PersonRole` → `ItemName` (clearer through-model name), `CSLDate` → `ItemDate` (consistent naming pattern), `Identifier` → `ItemIdentifier`
- **Conversion code**: Move from model methods to standalone `converters.py` module — keeps models focused on data representation and makes conversion testable independently
- **Ordering scope**: The old project used `order_with_respect_to = "literature_item"` only (not scoped to role type). We'll scope to `('item', 'role')` so author ordering and editor ordering are independent.
- **Identifier type flexibility**: The old project used strict `TextChoices` with no escape hatch. We'll allow any string (per FR-017) with warnings for unknown types.
- **Date model**: The old project embedded `literature_item` FK directly on `CSLDate`, essentially combining the "through" and "value" models. We'll do the same (simpler than a separate through table for dates since each date-type-per-item is unique).
- **`citation_key` uniqueness**: The old project used `unique=True` DB constraint. We'll enforce at application level per spec.
- **Remove non-scope models**: `Collection`, `SupplementaryMaterial`, `LiteratureTag`, `TaggedLiteratureItem` are out of scope for this feature.
- **Remove `orcid` from Name**: ORCID is not part of the CSL JSON name-variable spec. It can be added in a future feature.
- **String-or-number fields**: The old project used `PositiveIntegerField` for `number_of_pages` etc. We'll use `CharField` to preserve string values.
- **`archive_collection` field**: Missing from old project but present in CSL JSON schema — we'll add it.

### Alternatives Considered

- **Copy old project directly**: Would inherit design decisions that don't match our spec or research findings
- **Start completely from scratch without reference**: Would risk missing fields or edge cases the old project already discovered

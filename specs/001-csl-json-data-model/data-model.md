# Data Model: CSL JSON Data Model and Conversion

**Feature**: 001-csl-json-data-model
**Date**: 2026-04-09

## Entity Overview

```
┌─────────────────────────────────────────────────────────┐
│                        Item                              │
│  (Core bibliographic entry — 1 CSL JSON item object)     │
│                                                          │
│  PK: id (auto)                                           │
│  citation_key: CharField (indexed, app-level unique)     │
│  type: CharField (CSL type enum)                         │
│  [~50 scalar metadata fields]                            │
│  custom: JSONField (nullable)                            │
│  categories: JSONField (nullable)                        │
├─────────────────────────────────────────────────────────┤
│  Relations:                                              │
│  ← ItemName (ordered, through-model to Name)             │
│  ← ItemDate (CSL date-variable instances)                │
│  ← ItemIdentifier (typed identifier records)             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────┐     ┌──────────────────────────────────┐
│         Name             │     │           ItemName                │
│ (CSL name-variable)      │     │ (ordered through-model)           │
│                          │     │                                   │
│ PK: id (auto)            │←────│ name: FK → Name                  │
│ family: CharField        │     │ item: FK → Item                  │
│ given: CharField         │     │ role: CharField (CSL role enum)   │
│ dropping_particle        │     │ order: PositiveIntegerField       │
│ non_dropping_particle    │     │ order_with_respect_to=(item,role) │
│ suffix: CharField        │     │                                   │
│ literal: CharField       │     │ UNIQUE(item, role, name)          │
│ comma_suffix: BoolField  │     └──────────────────────────────────┘
│ static_ordering: BoolFld │
│ parse_names: BoolField   │
└─────────────────────────┘

┌──────────────────────────────────────────────────┐
│                    ItemDate                       │
│ (CSL date-variable instance per item)             │
│                                                   │
│ PK: id (auto)                                     │
│ item: FK → Item                                   │
│ date_type: CharField (CSL date-variable enum)     │
│ begin: PartialDateField (nullable)                │
│ end: PartialDateField (nullable, for ranges)      │
│ season: CharField (nullable)                      │
│ circa: BooleanField                               │
│ literal: CharField (nullable, free-text fallback) │
│ raw: CharField (nullable, unparsed string)        │
│ raw_date_parts: JSONField (nullable, fallback)    │
│                                                   │
│ UNIQUE(item, date_type)                           │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│                 ItemIdentifier                    │
│ (typed identifier per item)                       │
│                                                   │
│ PK: id (auto)                                     │
│ item: FK → Item                                   │
│ type: CharField (known choices + custom)           │
│ value: CharField                                  │
│                                                   │
│ UNIQUE(item, type)                                │
└──────────────────────────────────────────────────┘
```

## Entity: Item

**CSL JSON mapping**: Top-level item object
**Django model**: `literature.models.Item`
**Table name**: `literature_item`

### Fields

| Django Field | CSL JSON Field | Type | Constraints | Notes |
|---|---|---|---|---|
| `id` | — | AutoField (PK) | auto | Django standard PK |
| `citation_key` | `citation-key` | CharField(255) | required, db_index | App-level unique. Import: prefer `citation-key`, fallback `id`. Export: CSL `id` = `citation_key` |
| `type` | `type` | CharField(30) | required, choices | CSL item type enum (44 values). Rejects unknown types. |
| `title` | `title` | CharField(1000) | blank, db_index | |
| `title_short` | `title-short` / `shortTitle` | CharField(500) | blank | Also maps to deprecated `shortTitle` |
| `original_title` | `original-title` | CharField(500) | blank | |
| `container_title` | `container-title` | CharField(500) | blank, db_index | Journal, book, etc. |
| `container_title_short` | `container-title-short` | CharField(255) | blank | |
| `collection_title` | `collection-title` | CharField(500) | blank | |
| `volume_title` | `volume-title` | CharField(500) | blank | |
| `volume_title_short` | `volume-title-short` | CharField(255) | blank | |
| `part_title` | `part-title` | CharField(500) | blank | |
| `reviewed_title` | `reviewed-title` | CharField(500) | blank | |
| `reviewed_genre` | `reviewed-genre` | CharField(100) | blank | |
| `abstract` | `abstract` | TextField | blank | |
| `note` | `note` | TextField | blank | |
| `annote` | `annote` | TextField | blank | |
| `publisher` | `publisher` | CharField(255) | blank, db_index | |
| `publisher_place` | `publisher-place` | CharField(255) | blank | |
| `original_publisher` | `original-publisher` | CharField(255) | blank | |
| `original_publisher_place` | `original-publisher-place` | CharField(255) | blank | |
| `event_title` | `event-title` | CharField(500) | blank | Also imports deprecated `event` |
| `event_place` | `event-place` | CharField(255) | blank | |
| `volume` | `volume` | CharField(50) | blank | String-or-number in CSL; stored as string |
| `issue` | `issue` | CharField(50) | blank | String-or-number in CSL |
| `page` | `page` | CharField(100) | blank | e.g. "171-175" |
| `page_first` | `page-first` | CharField(50) | blank | String-or-number in CSL |
| `number` | `number` | CharField(50) | blank | |
| `number_of_pages` | `number-of-pages` | CharField(50) | blank | String-or-number in CSL (e.g. "xii + 340") |
| `number_of_volumes` | `number-of-volumes` | CharField(50) | blank | String-or-number in CSL |
| `edition` | `edition` | CharField(50) | blank | String-or-number (e.g. "2nd", 3) |
| `version` | `version` | CharField(50) | blank | |
| `chapter_number` | `chapter-number` | CharField(50) | blank | String-or-number |
| `collection_number` | `collection-number` | CharField(50) | blank | String-or-number |
| `section` | `section` | CharField(100) | blank | |
| `part` | `part` | CharField(50) | blank | String-or-number |
| `supplement` | `supplement` | CharField(100) | blank | String-or-number |
| `printing` | `printing` | CharField(50) | blank | String-or-number |
| `status` | `status` | CharField(50) | blank | |
| `medium` | `medium` | CharField(100) | blank | |
| `genre` | `genre` | CharField(100) | blank | |
| `language` | `language` | CharField(10) | blank | BCP 47 tag |
| `archive` | `archive` | CharField(255) | blank | |
| `archive_collection` | `archive_collection` | CharField(255) | blank | |
| `archive_location` | `archive_location` | CharField(255) | blank | Note: underscored in CSL JSON |
| `archive_place` | `archive-place` | CharField(255) | blank | |
| `authority` | `authority` | CharField(255) | blank | |
| `jurisdiction` | `jurisdiction` | CharField(255) | blank | |
| `call_number` | `call-number` | CharField(100) | blank | |
| `dimensions` | `dimensions` | CharField(100) | blank | |
| `division` | `division` | CharField(100) | blank | |
| `scale` | `scale` | CharField(50) | blank | |
| `source` | `source` | CharField(255) | blank | |
| `references` | `references` | TextField | blank | |
| `journal_abbreviation` | `journalAbbreviation` | CharField(100) | blank | CamelCase in CSL JSON |
| `citation_label` | `citation-label` | CharField(100) | blank | Processor-generated; stored for round-trip |
| `citation_number` | `citation-number` | CharField(50) | blank | String-or-number |
| `first_reference_note_number` | `first-reference-note-number` | CharField(50) | blank | String-or-number |
| `locator` | `locator` | CharField(100) | blank | String-or-number |
| `year_suffix` | `year-suffix` | CharField(10) | blank | |
| `keyword` | `keyword` | TextField | blank | CSL `keyword` is a single string (comma-separated) |
| `categories` | `categories` | JSONField | null, blank | String array in CSL JSON |
| `custom` | `custom` | JSONField | null, blank | Arbitrary key-value pairs |
| `created` | — | DateTimeField | auto_now_add | |
| `modified` | — | DateTimeField | auto_now | |

### Indexes

| Fields | Purpose |
|--------|---------|
| `citation_key` | Fast citation key lookup |
| `type` | Filter by item type |
| `title` | Title search |
| `container_title` | Journal/container lookup |
| `publisher` | Publisher filtering |

### Meta

```python
class Meta:
    verbose_name = "item"
    verbose_name_plural = "items"
    ordering = ["-created"]
```

---

## Entity: Name

**CSL JSON mapping**: `name-variable` definition
**Django model**: `literature.models.Name`
**Table name**: `literature_name`

### Fields

| Django Field | CSL JSON Field | Type | Constraints | Notes |
|---|---|---|---|---|
| `id` | — | AutoField (PK) | auto | |
| `family` | `family` | CharField(255) | blank | |
| `given` | `given` | CharField(255) | blank | |
| `dropping_particle` | `dropping-particle` | CharField(50) | blank | e.g. "von", "van" |
| `non_dropping_particle` | `non-dropping-particle` | CharField(50) | blank | e.g. "van der", "de" |
| `suffix` | `suffix` | CharField(50) | blank | e.g. "Jr.", "III" |
| `literal` | `literal` | CharField(500) | blank | Institutional names, unparsed strings |
| `comma_suffix` | `comma-suffix` | BooleanField | default=False | |
| `static_ordering` | `static-ordering` | BooleanField | default=False | e.g. East Asian names |
| `parse_names` | `parse-names` | BooleanField | default=False | Signal to processor |
| `created` | — | DateTimeField | auto_now_add | |
| `modified` | — | DateTimeField | auto_now | |

### Indexes

| Fields | Purpose |
|--------|---------|
| `(family, given)` | Name lookup |

### Validation Rules

- At least one of `family`, `given`, or `literal` must be non-empty
- If `literal` is set, it takes precedence for display

### Meta

```python
class Meta:
    verbose_name = "name"
    verbose_name_plural = "names"
    ordering = ["family", "given"]
```

---

## Entity: ItemName

**CSL JSON mapping**: Through-model linking items to names with role and ordering
**Django model**: `literature.models.ItemName`
**Table name**: `literature_itemname`
**Extends**: `ordered_model.models.OrderedModel`

### Fields

| Django Field | CSL JSON Field | Type | Constraints | Notes |
|---|---|---|---|---|
| `id` | — | AutoField (PK) | auto | |
| `item` | — | ForeignKey → Item | CASCADE | |
| `name` | — | ForeignKey → Name | CASCADE | |
| `role` | (key name in CSL JSON) | CharField(25) | required, choices | CSL name-variable role (27 values) |
| `order` | (array index) | PositiveIntegerField | auto | Managed by django-ordered-model |

### `order_with_respect_to`

```python
order_with_respect_to = ('item', 'role')
```

This means ordering is scoped: names are ordered independently per item AND per role. Author order on Item A is separate from editor order on Item A.

### Name Role Choices (CSL name-variable fields)

```python
class NameRole(models.TextChoices):
    AUTHOR = "author", "Author"
    CHAIR = "chair", "Chair"
    COLLECTION_EDITOR = "collection-editor", "Collection Editor"
    COMPILER = "compiler", "Compiler"
    COMPOSER = "composer", "Composer"
    CONTAINER_AUTHOR = "container-author", "Container Author"
    CONTRIBUTOR = "contributor", "Contributor"
    CURATOR = "curator", "Curator"
    DIRECTOR = "director", "Director"
    EDITOR = "editor", "Editor"
    EDITORIAL_DIRECTOR = "editorial-director", "Editorial Director"
    EXECUTIVE_PRODUCER = "executive-producer", "Executive Producer"
    GUEST = "guest", "Guest"
    HOST = "host", "Host"
    ILLUSTRATOR = "illustrator", "Illustrator"
    INTERVIEWER = "interviewer", "Interviewer"
    NARRATOR = "narrator", "Narrator"
    ORGANIZER = "organizer", "Organizer"
    ORIGINAL_AUTHOR = "original-author", "Original Author"
    PERFORMER = "performer", "Performer"
    PRODUCER = "producer", "Producer"
    RECIPIENT = "recipient", "Recipient"
    REVIEWED_AUTHOR = "reviewed-author", "Reviewed Author"
    SCRIPT_WRITER = "script-writer", "Script Writer"
    SERIES_CREATOR = "series-creator", "Series Creator"
    TRANSLATOR = "translator", "Translator"
```

### Indexes

| Fields | Purpose |
|--------|---------|
| `(item, role, order)` | Ordered name lookup by role |
| `(name, role)` | Find all items for a name in a given role |

### Constraints

| Type | Fields | Name | Notes |
|------|--------|------|-------|
| UniqueConstraint | `(item, role, name)` | `unique_name_per_role_per_item` | Same person can't have same role twice on one item |

### Meta

```python
class Meta:
    verbose_name = "item name"
    verbose_name_plural = "item names"
    ordering = ["item", "role", "order"]
```

---

## Entity: ItemDate

**CSL JSON mapping**: `date-variable` definition, linked to item with date-type slot
**Django model**: `literature.models.ItemDate`
**Table name**: `literature_itemdate`

### Fields

| Django Field | CSL JSON Field | Type | Constraints | Notes |
|---|---|---|---|---|
| `id` | — | AutoField (PK) | auto | |
| `item` | — | ForeignKey → Item | CASCADE | |
| `date_type` | (key name in CSL JSON) | CharField(20) | required, choices | CSL date-variable slot name |
| `begin` | `date-parts[0]` | PartialDateField | null, blank | Start/single date. Uses `django-partial-date`. |
| `end` | `date-parts[1]` | PartialDateField | null, blank | End date for ranges. Must not be set without `begin`. |
| `season` | `season` | CharField(20) | blank | "1"=Spring, "2"=Summer, "3"=Autumn, "4"=Winter, or custom string |
| `circa` | `circa` | BooleanField | default=False | Approximate date flag |
| `literal` | `literal` | CharField(255) | blank | Free-text date when structured representation impossible |
| `raw` | `raw` | CharField(255) | blank | Unparsed date string from source |
| `raw_date_parts` | `date-parts` | JSONField | null, blank | Stores original date-parts array when normalization to PartialDate is not possible |

### Date-Type Choices (CSL date-variable fields)

```python
class DateType(models.TextChoices):
    ACCESSED = "accessed", "Accessed"
    AVAILABLE_DATE = "available-date", "Available Date"
    EVENT_DATE = "event-date", "Event Date"
    ISSUED = "issued", "Issued"
    ORIGINAL_DATE = "original-date", "Original Date"
    SUBMITTED = "submitted", "Submitted"
```

### Indexes

| Fields | Purpose |
|--------|---------|
| `(item, date_type)` | Date lookup by type per item |
| `begin` | Date range queries |
| `end` | Date range queries |

### Constraints

| Type | Fields | Name | Notes |
|------|--------|------|-------|
| UniqueConstraint | `(item, date_type)` | `unique_date_type_per_item` | One date of each type per item |

### Validation Rules

- `end` must not be set when `begin` is null
- At least one of `begin`, `literal`, or `raw` should be set (soft validation — warn, don't reject)

### Date Import Logic

```
Input CSL date-variable:
  1. If `date-parts` present:
     a. Parse first array → `begin` (PartialDate with appropriate precision)
     b. If second array present → `end` (PartialDate)
     c. If parsing fails → store original in `raw_date_parts`, leave begin/end null
  2. If `raw` present and no date-parts:
     a. Attempt parse with python-dateutil → `begin`
     b. If parsing fails → store in `raw` field, leave begin null
  3. If `literal` present → store in `literal` field
  4. Copy `season` and `circa` directly
```

### Date Export Logic

```
Output CSL date-variable:
  1. If `begin` is set:
     a. Convert to date-parts array based on precision
     b. If `end` is set, create two-element date-parts
  2. If `raw_date_parts` is set and begin is null → emit raw_date_parts as date-parts
  3. If `literal` set → emit literal
  4. If `raw` set and nothing else → emit raw
  5. Include season/circa if set
```

### Meta

```python
class Meta:
    verbose_name = "item date"
    verbose_name_plural = "item dates"
```

---

## Entity: ItemIdentifier

**CSL JSON mapping**: Identifier properties (DOI, ISBN, etc.) on item object
**Django model**: `literature.models.ItemIdentifier`
**Table name**: `literature_itemidentifier`

### Fields

| Django Field | CSL JSON Field | Type | Constraints | Notes |
|---|---|---|---|---|
| `id` | — | AutoField (PK) | auto | |
| `item` | — | ForeignKey → Item | CASCADE | |
| `type` | (varies per identifier) | CharField(50) | required | Known choices + custom strings allowed |
| `value` | (varies per identifier) | CharField(500) | required | The identifier value |

### Identifier Type Choices

```python
class IdentifierType(models.TextChoices):
    DOI = "DOI", "DOI"
    ISBN = "ISBN", "ISBN"
    ISSN = "ISSN", "ISSN"
    PMID = "PMID", "PMID"
    PMCID = "PMCID", "PMCID"
    URL = "URL", "URL"
```

Note: The `type` field is NOT restricted to these choices (per FR-017). Unknown identifier types are stored with a `logger.warning()` but not rejected. The choices list provides known CSL JSON identifier field names.

### CSL JSON Identifier Mapping

On import, these CSL JSON top-level fields are extracted to `ItemIdentifier` records:

| CSL JSON Field | `ItemIdentifier.type` |
|---|---|
| `DOI` | `"DOI"` |
| `ISBN` | `"ISBN"` |
| `ISSN` | `"ISSN"` |
| `PMID` | `"PMID"` |
| `PMCID` | `"PMCID"` |
| `URL` | `"URL"` |

On export, `ItemIdentifier` records with known types are mapped back to top-level CSL JSON fields. Unknown types are placed in the `custom` object.

### Indexes

| Fields | Purpose |
|--------|---------|
| `(item, type)` | Identifier lookup by type per item |
| `(type, value)` | Global identifier search |
| `value` | Value-based lookup |

### Constraints

| Type | Fields | Name | Notes |
|------|--------|------|-------|
| UniqueConstraint | `(item, type)` | `unique_identifier_type_per_item` | One identifier of each type per item |

### Meta

```python
class Meta:
    verbose_name = "item identifier"
    verbose_name_plural = "item identifiers"
```

---

## Relationship Summary

```
Item 1──∞ ItemName ∞──1 Name
Item 1──∞ ItemDate
Item 1──∞ ItemIdentifier
```

- **Item ↔ Name**: Many-to-many through `ItemName`, ordered per (item, role)
- **Item ↔ ItemDate**: One-to-many, unique per (item, date_type)
- **Item ↔ ItemIdentifier**: One-to-many, unique per (item, type)

---

## CSL JSON Field Coverage Checklist

All 44 CSL JSON item types: covered via `Item.type` choices.

All CSL JSON properties accounted for:

| CSL JSON Property | Storage Location | Notes |
|---|---|---|
| `id` | `Item.citation_key` (on export) | Required by schema; populated from citation_key on export |
| `type` | `Item.type` | Required. Strict enum validation. |
| `citation-key` | `Item.citation_key` | Primary import source for citation_key |
| `categories` | `Item.categories` (JSONField) | String array |
| `language` | `Item.language` | |
| `journalAbbreviation` | `Item.journal_abbreviation` | CamelCase → snake_case |
| `shortTitle` | `Item.title_short` | CamelCase → snake_case |
| 27 name-variable fields | `ItemName` records | Via role field |
| 6 date-variable fields | `ItemDate` records | Via date_type field |
| 6 identifier fields | `ItemIdentifier` records | DOI, ISBN, ISSN, PMID, PMCID, URL |
| `custom` | `Item.custom` (JSONField) | Arbitrary key-value |
| ~38 scalar string/number fields | `Item.*` columns | See Item fields table |

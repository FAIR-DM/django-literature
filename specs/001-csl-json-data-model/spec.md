# Feature Specification: CSL JSON Data Model, Conversion, and Admin

**Feature Branch**: `001-csl-json-data-model`  
**Created**: 2026-04-08  
**Status**: Draft  
**Input**: User description: "Django Literature must provide a data model that reflects CSL JSON, is well tested and well documented. We should support at a minimum conversion between our data model and CSL JSON. We should provide a basic admin interface for interacting with the models."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Store and Retrieve Bibliographic Entries (Priority: P1)

A developer integrating django-literature into their Django project defines models that accurately capture bibliographic data for articles, books, theses, web pages, and other publication types. They can create, save, and query entries using standard Django ORM patterns, with each entry storing all standard CSL JSON fields without any data loss.

**Why this priority**: This is the foundational capability on which everything else depends. Without a correct and complete data model, neither conversion nor admin is possible.

**Independent Test**: Can be fully tested by creating model instances for each CSL JSON item type, saving them to the database, retrieving them, and asserting all fields are preserved. Delivers a functional, queryable bibliographic database.

**Acceptance Scenarios**:

1. **Given** a valid CSL JSON item of type `article-journal`, **When** a developer creates a corresponding model instance with all standard fields (title, author, volume, issue, page, DOI, year), **Then** all fields are persisted and retrievable without modification.
2. **Given** a bibliographic item model, **When** the developer queries for items by type, author, or year, **Then** the correct results are returned.
3. **Given** a contributor (author or editor) associated with an item, **When** the item is retrieved, **Then** the contributor's name parts (family, given) and role are correctly associated.
4. **Given** a CSL-style partial date (year only, or year-month), **When** stored as a date field, **Then** the partial information is preserved and distinguishable from a full date.

---

### User Story 2 - Convert Between Model and CSL JSON (Priority: P2)

A developer passing bibliographic data to a citation rendering library (such as citeproc-js) or importing data from an external source can serialize model instances to standards-compliant CSL JSON and deserialize CSL JSON back into model instances.

**Why this priority**: Interoperability with the broader CSL ecosystem is the core value proposition of the library. Without this, the data model is an isolated island.

**Independent Test**: Can be fully tested by round-tripping a set of representative bibliographic entries — create a model instance, export to CSL JSON dict, import back to a new instance, and assert all fields match.

**Acceptance Scenarios**:

1. **Given** a saved bibliographic item with all fields populated, **When** the developer calls the serializer/exporter, **Then** the output is a valid CSL JSON dictionary matching the CSL JSON schema.
2. **Given** a valid CSL JSON dictionary, **When** the developer calls the importer/deserializer, **Then** a model instance is created with all fields correctly populated.
3. **Given** a CSL JSON dictionary with only required fields and some optional fields omitted, **When** imported, **Then** the missing optional fields are left blank/null without error.
4. **Given** a model instance is serialized to CSL JSON and then deserialized back, **When** all fields are compared, **Then** no data is lost or altered (round-trip fidelity).
5. **Given** a CSL JSON item with an unrecognized `type` value, **When** imported, **Then** the system stores the value without silently discarding it, and surfaces a warning or stores it with an `unknown` marker.

---

### User Story 3 - Manage Bibliographic Entries via Admin (Priority: P3)

An administrator or content manager uses the Django admin interface to browse, search, add, edit, and delete bibliographic entries without writing any code.

**Why this priority**: Provides an out-of-the-box management interface, making the library immediately useful for projects that do not yet have custom views.

**Independent Test**: Can be fully tested by navigating to the admin, creating a new item through the form, editing it, and deleting it — delivering a fully operational management UI for database records.

**Acceptance Scenarios**:

1. **Given** the app is installed and the admin is enabled, **When** an admin user visits the bibliographic entry list, **Then** all items are displayed with key fields (title, type, year) visible.
2. **Given** the admin list view, **When** the admin searches by title or author name, **Then** matching items are returned.
3. **Given** the admin list view, **When** the admin filters by item type, **Then** only items of that type are shown.
4. **Given** a new bibliographic entry form in the admin, **When** the admin submits valid data, **Then** a new item is created and appears in the list.
5. **Given** an existing bibliographic item, **When** the admin edits and saves it, **Then** the changes are persisted correctly.

---

### User Story 4 - Understand the Models via Documentation (Priority: P4)

A developer reading the source code or generated documentation can understand the purpose and CSL JSON mapping of every model, field, and utility function without needing to consult the CSL JSON specification separately.

**Why this priority**: Long-term maintainability depends on clear documentation. Without it, contributors cannot confidently extend or modify the models.

**Independent Test**: Can be fully tested by reviewing docstrings on every public model, field, manager, and conversion function, and verifying the documentation build produces complete API reference output.

**Acceptance Scenarios**:

1. **Given** any model class, **When** its docstring is read, **Then** it states what CSL JSON element it maps to and its purpose.
2. **Given** any model field, **When** its help text or docstring is read, **Then** it identifies the corresponding CSL JSON field name.
3. **Given** the conversion utilities, **When** their docstrings are read, **Then** the expected input/output formats and any edge cases are described.

---

### Edge Cases

- What happens when a CSL JSON item type is not in the known list of types? → A validation error is raised and the item is rejected; it is not stored.
- How does the system handle contributor names provided as a single string rather than separate family/given parts?
- What happens when a partial date has only a year, or year and month, but no day?
- How does the system behave when a CSL JSON field value exceeds expected length limits?
- What happens when required CSL JSON fields (e.g., `id`, `type`) are missing during import? → A validation error is raised immediately, identifying the missing field; the item is rejected and nothing is stored.
- How are duplicate entries (same DOI or citation key) handled? → On import, duplicate citation keys are resolved by appending a letter suffix (Smith2009 → Smith2009b → Smith2009c…) so every stored entry has a unique key. Existing records are never overwritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The data model MUST represent all standard CSL JSON item types (article-journal, book, chapter, thesis, webpage, report, etc.) via a strictly-enforced choices field on the item entity. The full known CSL type list MUST be enumerated as valid choices; any value outside this list MUST be rejected with a validation error.
- **FR-002**: The data model MUST support all standard CSL JSON string, number, and boolean fields on bibliographic items (title, abstract, publisher, volume, issue, page, DOI, ISBN, ISSN, URL, etc.).
- **FR-003**: The data model MUST store CSL name-variable fields (author, editor, translator, chair, collection-editor, container-author, etc.) via a dedicated `Name` model linked to `Item` through a `NameThrough` model. `NameThrough` MUST record the CSL role type (from a defined choices list) and the ordering of names within that role. `Name` MUST store separable name parts (family, given) and optionally a literal/organization name.
- **FR-004**: The data model MUST store CSL date-variable fields (issued, accessed, submitted, etc.) via a dedicated `Date` model linked to `Item` through a `DateThrough` model. `DateThrough` MUST record the CSL date slot name. `Date` MUST support year-only, year-month, and full year-month-day precision.
- **FR-017**: The data model MUST store typed identifiers (DOI, ISBN, ISSN, URL, PMID, call-number, etc.) in a dedicated `Identifier` model associated with `Item`, recording identifier type and value. Multiple identifiers of different types MUST be storable per item. The identifier type field MUST define choices for all well-known CSL identifier types but MUST allow any string value; unknown types produce a warning and are stored without rejection.
- **FR-005**: The data model MUST support a unique citation key per item to identify entries.
- **FR-006**: The system MUST provide a function or method to serialize a model instance to a CSL JSON-compatible dictionary.
- **FR-007**: The system MUST provide a function or method to deserialize a CSL JSON dictionary into a new model instance. If the citation key from the incoming data already exists, the importer MUST automatically append a letter suffix (e.g. `Smith2009` → `Smith2009b`) to produce a unique key; existing records MUST NOT be overwritten. If required fields (`id`, `type`) are absent, the importer MUST raise a validation error identifying the missing field and reject the item without storing anything.
- **FR-008**: Round-trip conversion (model → CSL JSON → model) MUST preserve all stored field values without data loss.
- **FR-009**: Every model class MUST have a docstring describing its purpose and its mapping to the CSL JSON specification.
- **FR-010**: Every model field and conversion function MUST have documentation (docstring or help_text) identifying the corresponding CSL JSON field.
- **FR-011**: The test suite MUST cover all model fields, relationships, and conversion functions.
- **FR-012**: The Django admin MUST register all core models and provide list display with at minimum title, type, and year.
- **FR-013**: The Django admin MUST support search by title and contributor name.
- **FR-014**: The Django admin MUST support filtering by item type.
- **FR-015**: Importing a CSL JSON item with an unrecognised `type` value MUST raise a validation error; the item MUST NOT be stored.
- **FR-016**: Name entries provided as a literal string (rather than family/given parts) MUST be storable and round-trippable via the `Name` model's literal field.

### Key Entities

- **Item**: The core bibliographic entry. Represents a single CSL JSON item object with a unique citation key, item type, and all scalar metadata fields (title, abstract, publisher, volume, issue, page, etc.). Related names, dates, and identifiers are held in dedicated related models.
- **Name**: A person or organization referenced in a CSL name-variable field (family, given, literal/organization name parts). Names are linked to Items via a through model (`NameThrough`) that records the CSL field role (author, editor, translator, chair, collection-editor, container-author, etc.) and ordering.
- **Date**: A bibliographic date linked to an Item via a through model (`DateThrough`) that records the CSL date-variable slot name (issued, accessed, submitted, etc.). Stores year-only, year-month, or full date precision reflecting the CSL JSON date-parts structure.
- **Identifier**: A typed identifier (e.g., DOI, ISBN, ISSN, PMID, URL) associated with an Item. Stores the identifier type and its value, allowing multiple identifiers per item.

## Clarifications

### Session 2026-04-08

- Q: How should CSL JSON fields be stored — flat table, JSON overflow, or normalized relational models? → A: Separate `Name` model for name-variables (linked via `NameThrough` with a role type field); separate `Date` model for date-variables (linked via `DateThrough` with a slot name field); separate `Identifier` model for identifiers (DOI, ISBN, ISSN, etc.); scalar/string/number CSL fields remain as columns on `Item`.
- Q: When importing a CSL JSON item whose citation key already exists, what should happen? → A: Always create a new record; if the citation key conflicts, automatically append a letter suffix to make it unique (e.g. Smith2009 → Smith2009b → Smith2009c). Overwriting existing data is explicitly not supported.
- Q: Should the `type` field enforce the known CSL type list or allow any string? → A: Strictly enforce the known CSL type list; importing an item with an unrecognised type MUST raise a validation error and the item MUST NOT be stored.
- Q: What should the importer do when required CSL JSON fields (`id`, `type`) are missing? → A: Raise a validation error immediately, report which field is missing, and reject the item. No auto-generation or partial storage.
- Q: Should the `Identifier` model's type field enforce a fixed choices list or allow any string? → A: Fixed choices for well-known identifier types (DOI, ISBN, ISSN, PMID, URL, etc.); allow any string for custom/unknown types with a warning but no rejection.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All CSL JSON item types defined in the CSL specification can be stored and retrieved; 0 known item types are unsupported.
- **SC-002**: Round-trip conversion (model → CSL JSON → model) produces identical field values for 100% of fields on a reference set of test fixtures covering all item types.
- **SC-003**: The automated test suite achieves 90% or greater line coverage across all model and conversion code.
- **SC-004**: Every public model class, field, and conversion function has a docstring; 0 undocumented public interfaces in the core module.
- **SC-005**: An administrator can create, view, edit, and delete any bibliographic entry through the admin in fewer than 5 interactions per operation.
- **SC-006**: Admin search returns correct results for title and contributor name queries with no false negatives on exact matches.

## Assumptions

- The CSL JSON specification version 1.0.2 is the target standard; future CSL versions may require spec updates.
- The library is intended as a reusable Django app, so models must be database-agnostic (no vendor-specific field types).
- REST API views, custom front-end views, and template tag utilities are out of scope for this feature.
- The admin interface uses Django's built-in admin framework; a custom admin theme is not required.
- Bulk import/export operations (e.g., importing an entire `.json` file of CSL items) are desirable but can be deferred; this feature targets single-item conversion at minimum.
- The app targets Python 3.11+ and Django 4.2+ as minimum supported versions.
- Only the CSL JSON serialization format is targeted; CSL XML and BibTeX are out of scope for this feature.

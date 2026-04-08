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

- What happens when a CSL JSON item type is not in the known list of types (e.g., a future or custom type)?
- How does the system handle contributor names provided as a single string rather than separate family/given parts?
- What happens when a partial date has only a year, or year and month, but no day?
- How does the system behave when a CSL JSON field value exceeds expected length limits?
- What happens when required CSL JSON fields (e.g., `id`, `type`) are missing during import?
- How are duplicate entries (same DOI or citation key) handled?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The data model MUST represent all standard CSL JSON item types (article-journal, book, chapter, thesis, webpage, report, etc.) via a type field on the item entity.
- **FR-002**: The data model MUST support all standard CSL JSON string, number, and boolean fields on bibliographic items (title, abstract, publisher, volume, issue, page, DOI, ISBN, ISSN, URL, etc.).
- **FR-003**: The data model MUST support contributor roles (author, editor, translator, collection-editor, container-author, etc.) with each contributor having separable family name, given name, and optionally a literal/organization name.
- **FR-004**: The data model MUST support CSL JSON date fields (issued, accessed, submitted, etc.) as partial dates that can represent year-only, year-month, or year-month-day precision.
- **FR-005**: The data model MUST support a unique citation key per item to identify entries.
- **FR-006**: The system MUST provide a function or method to serialize a model instance to a CSL JSON-compatible dictionary.
- **FR-007**: The system MUST provide a function or method to deserialize a CSL JSON dictionary into model instances (creating or updating as appropriate).
- **FR-008**: Round-trip conversion (model → CSL JSON → model) MUST preserve all stored field values without data loss.
- **FR-009**: Every model class MUST have a docstring describing its purpose and its mapping to the CSL JSON specification.
- **FR-010**: Every model field and conversion function MUST have documentation (docstring or help_text) identifying the corresponding CSL JSON field.
- **FR-011**: The test suite MUST cover all model fields, relationships, and conversion functions.
- **FR-012**: The Django admin MUST register all core models and provide list display with at minimum title, type, and year.
- **FR-013**: The Django admin MUST support search by title and contributor name.
- **FR-014**: The Django admin MUST support filtering by item type.
- **FR-015**: Importing a CSL JSON item with an unrecognized type MUST NOT silently discard the type value.
- **FR-016**: Contributor names provided as a literal string (rather than family/given parts) MUST be storable and round-trippable.

### Key Entities

- **Item**: The core bibliographic entry. Represents a single CSL JSON item object with a unique citation key, item type, and all associated metadata fields. Items are the primary object managed throughout the system.
- **Contributor**: A person or organization associated with an item in a specific role (author, editor, etc.). Has separable name parts (family, given) and/or a literal form. One item may have many contributors in different roles.
- **PartialDate**: A date associated with an item in a named slot (issued, accessed, submitted, etc.). Supports year-only, year-month, and full date precision, reflecting the CSL JSON date-parts structure.

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

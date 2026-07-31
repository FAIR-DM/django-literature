# Feature Specification: CSL JSON Data Model and Conversion

**Feature Branch**: `001-csl-json-data-model`
**Created**: 2026-04-08
**Status**: Draft
**Input**: User description: "Django Literature must provide a data model that reflects CSL JSON, is well tested and well documented. We should support at a minimum conversion between our data model and CSL JSON. We should provide a basic admin interface for interacting with the models."

> **Scope note**: The admin interface originally described in the input has been removed from this feature. A dedicated CRUD/admin interface will be addressed in a subsequent spec once the normalized data model is fully established.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Store and Retrieve Bibliographic Entries (Priority: P1)

A developer integrating django-literature into their Django project defines models that accurately capture bibliographic data for articles, books, theses, web pages, and other publication types. They can create, save, and query entries using standard Django ORM patterns, with each entry storing all standard CSL JSON fields without any data loss.

**Why this priority**: This is the foundational capability on which everything else depends. Without a correct and complete data model, conversion is not possible.

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
5. **Given** a CSL JSON item with an unrecognized `type` value, **When** imported, **Then** the importer raises a `ValidationError` identifying the unknown type and rejects the item without storing it (see FR-015).

---

### User Story 3 - Understand the Models via Documentation (Priority: P3)

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
- What happens when required CSL JSON fields are missing during import? → If `type` is absent, a validation error is raised immediately and the item is rejected. If both `citation-key` and `id` are absent or empty, a validation error is raised (no usable citation key can be derived). If `citation-key` is absent but `id` is present, `id` is used as the `citation_key` fallback.
- How are duplicate entries (same DOI or citation key) handled? → On import, duplicate citation keys are resolved by appending a letter suffix (Smith2009 → Smith2009b → Smith2009c…) so every stored entry has a unique key. Existing records are never overwritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The data model MUST represent all standard CSL JSON item types (article-journal, book, chapter, thesis, webpage, report, etc.) via a strictly-enforced choices field on the item entity. The full known CSL type list MUST be enumerated as valid choices; any value outside this list MUST be rejected with a validation error.
- **FR-002**: The data model MUST support all standard CSL JSON string, number, and boolean fields on bibliographic items (title, abstract, publisher, volume, issue, page, DOI, ISBN, ISSN, URL, etc.).
- **FR-003**: The data model MUST store CSL name-variable fields (author, editor, translator, chair, collection-editor, container-author, etc.) via a dedicated `Name` model linked to `Item` through an `ItemName` through-model. `ItemName` MUST record the CSL role type (from a defined choices list) and the ordering of names within that role, scoped per `(item, role)`. `Name` MUST store separable name parts (family, given) and optionally a literal/organization name.
- **FR-004**: The data model MUST store CSL date-variable fields (issued, accessed, submitted, etc.) via a dedicated `ItemDate` model directly associated with `Item`. `ItemDate` MUST record the CSL date-variable slot name (`date_type`). `ItemDate` MUST support all CSL JSON date forms including year-only, year-month, full year-month-day, and date ranges (two date-parts arrays stored as `begin`/`end` PartialDate fields). When date-parts can be parsed to a PartialDate, the model MUST normalize into structured `begin`/`end` fields; when normalization is not possible (e.g. partial ranges, unusual precision), the raw `date-parts` array MUST be preserved in a `raw_date_parts` JSONField alongside the structured fields.
- **FR-017**: The data model MUST store typed identifiers (DOI, ISBN, ISSN, URL, PMID, call-number, etc.) in a dedicated `ItemIdentifier` model associated with `Item`, recording identifier type and value. Multiple identifiers of different types MUST be storable per item. The identifier type field MUST define choices for all well-known CSL identifier types but MUST allow any string value; when an unknown identifier type is encountered, the importer MUST emit a `logger.warning(...)` via `logging.getLogger(__name__)` and store the item without rejection.
- **FR-005**: The data model MUST support a required `citation_key` field on `Item`. This field maps to the CSL JSON `citation-key` variable — the BibTeX entrykey-style handle used in `\cite{...}` and `[@key]` in-document citation syntax (distinct from the CSL `id` field, which is a processor-internal session-scoped lookup key, and `citation-label`, which is processor-generated output). The `citation_key` field MUST be db-indexed for fast lookup. Uniqueness MUST be enforced at the application level, NOT as a database `UNIQUE` constraint, to support multi-library and multi-tenant deployments where the same key may exist across different library scopes. The database identifier is Django's standard auto-increment primary key. When a `citation_key` value conflicts with an existing record within the same scope, the importer MUST automatically append a letter suffix (e.g. `Smith2009` → `Smith2009b`) to produce a unique key.
- **FR-006**: The system MUST provide a function or method to serialize a model instance to a CSL JSON-compatible dictionary.
- **FR-007**: The system MUST provide a function or method to deserialize a CSL JSON dictionary into a new model instance. Required import fields are `type` plus at least one of `citation-key` or `id`; if `type` is absent, OR if both `citation-key` and `id` are absent or empty, the importer MUST raise a validation error identifying the missing field(s) and reject the item without storing anything. On import, the CSL `citation-key` field is the preferred source for `citation_key`; if `citation-key` is absent, the CSL `id` field is used as a fallback. The resolved value is deduplicated by appending a letter suffix if needed (e.g. `Smith2009` → `Smith2009b`). On export (serialization), the CSL `id` field MUST be populated with the `citation_key` value. Existing records MUST NOT be overwritten.
- **FR-008**: Round-trip conversion (model → CSL JSON → model) MUST preserve all stored field values without data loss.
- **FR-009**: Every model class MUST have a docstring describing its purpose and its mapping to the CSL JSON specification.
- **FR-010**: Every model field and conversion function MUST have documentation (docstring or help_text) identifying the corresponding CSL JSON field.
- **FR-011**: The test suite MUST cover all model fields, relationships, and conversion functions. Date handling MUST include dedicated round-trip tests for every supported CSL JSON date form: year-only, year-month, full year-month-day, full date range (both parts precise), and partial date range (one or both parts lacking full precision).
- **FR-015**: The importer (`from_csl_json()`) MUST enforce the type constraint defined by FR-001 at the function boundary: importing a CSL JSON item with an unrecognized `type` value MUST raise a `ValidationError` and the item MUST NOT be stored. This is the importer-layer mirror of the model-layer `choices` constraint; FR-001 is the authoritative definition.
- **FR-016**: Name entries provided as a literal string (rather than family/given parts) MUST be storable and round-trippable via the `Name` model's literal field.
- **FR-018**: All user-facing strings MUST use Django translation wrappers, with wrapper choice determined by call site:
  - **Module/class import time** (model `Meta.verbose_name`, `Meta.verbose_name_plural`, field `help_text`, descriptive `choices` labels, `validators` messages): MUST use `gettext_lazy` (imported as `_` from `django.utils.translation`).
  - **Function/method body** (importer validation error messages, serializer warnings, any string raised or returned inside a callable): MUST use eager `gettext` (imported as `_` from `django.utils.translation`).
  - **Exemption**: Pure acronym `choices` labels that are language-invariant (e.g., `"DOI"`, `"ISBN"`, `"ISSN"`, `"URL"`) do NOT require wrapping. Mixed or descriptive labels (e.g., `"Call Number"`, `"PubMed ID"`) MUST be wrapped with `gettext_lazy`.
  Hard-coded bare string literals that are displayed to users in any other context MUST NOT appear in the package source.
- **FR-019**: The package MUST include a `literature/locale/en/LC_MESSAGES/` directory containing a generated `django.po` stub. This initial catalog MUST be produced by running `django-admin makemessages -l en` against the package source and committed alongside this feature's i18n changes. `makemessages` MUST complete without errors.
- **FR-020**: Identifier values stored in `ItemIdentifier` MUST be validated at the model layer for well-known types. DOI values MUST match the pattern `10.\d{4,}/\S+`. ISBN values MUST be a valid ISBN-10 or ISBN-13 (digit count and check-digit verification). ISSN values MUST match the pattern `\d{4}-\d{3}[\dX]`. URL values MUST be a syntactically valid absolute URL (scheme + authority). PMID and PMCID values MUST be numeric strings. Validation MUST use Django validators attached to the `ItemIdentifier.value` field and MUST raise `ValidationError` with a descriptive, translated (`gettext_lazy`) message. Unknown identifier types have no format constraint and MUST be stored without format validation.

### Key Entities

- **Item**: The core bibliographic entry. Represents a single CSL JSON item object with a Django `BigAutoField` primary key, a required `citation_key` field (maps to the CSL JSON `citation-key` variable — the BibTeX entrykey-style handle; db-indexed, uniqueness enforced at application level), item type, and all scalar metadata fields (title, abstract, publisher, volume, issue, page, etc.). Related names, dates, and identifiers are held in dedicated related models.
- **Name**: A person or organization referenced in a CSL name-variable field (family, given, literal/organization name parts). Names are linked to Items via the `ItemName` through-model that records the CSL field role (author, editor, translator, chair, collection-editor, container-author, etc.) and ordering scoped per `(item, role)`.
- **ItemName**: Through-model linking `Item` to `Name`. Records the CSL name-variable role (`NameRole` choices) and position order within that role on that item. ~~Extends `django-ordered-model`'s `OrderedModel` with `order_with_respect_to = ("item", "role")`.~~ **[Superseded by ADR-0005, 2026-07-24]** The `(item, role)` ordering intent stands, but the mechanism changed: `django-ordered-model` cannot scope by the non-FK `role` field, so ordering is now assigned in `ItemName.save()` on a plain `PositiveIntegerField`.
- **ItemDate**: A bibliographic date associated directly with an `Item`. Records the CSL date-variable slot name (`date_type`, `DateType` choices) and stores the date using `begin`/`end` PartialDate fields for structured dates or a `raw_date_parts` JSONField for dates that cannot be fully normalized. Supports single dates and date ranges.
- **ItemIdentifier**: A typed identifier (e.g., DOI, ISBN, ISSN, PMID, URL) associated with an `Item`. Stores the identifier type and its value, allowing multiple identifiers per item. Well-known identifier values are validated at the model layer (FR-020).

## Clarifications

### Session 2026-04-09 (i18n)

- Q: Should `locale/` directory bootstrapping (creating the `en` `.po` catalog and ensuring `makemessages` runs cleanly) be included in this feature's scope? → A: Yes — include `locale/` setup in this feature. Create `literature/locale/en/LC_MESSAGES/`, run `makemessages` to generate the initial `django.po` stub, and commit it alongside this feature's Python i18n changes. This satisfies Principle VII's requirement that the package ships a `locale/` directory from the first i18n-compliant feature onward.
- Q: Should the test suite include an i18n integration test that activates a non-English locale and asserts translated strings are returned? → A: No — testing Django's translation machinery is not required; Django and upstream packages cover that behaviour. The i18n requirement is strictly a code-authoring discipline: all user-facing strings MUST use `gettext` or `gettext_lazy` wrappers. Correct wrapper usage is enforced via code review and `makemessages` clean runs, not runtime locale-activation tests.
- Q: Should importer/serializer validation error strings (defined inside function bodies) use eager `gettext` or lazy `gettext_lazy`? → A: Eager `gettext` (`from django.utils.translation import gettext as _`) for strings defined and raised inside function bodies, since the locale is already active at call time. `gettext_lazy` is reserved for strings evaluated at module/class import time (model `verbose_name`, field `help_text`, `choices` labels, etc.).
- Q: Should `choices` labels for identifier types (DOI, ISBN, ISSN, etc.) be wrapped with `gettext_lazy` even though they are language-invariant acronyms? → A: No — pure acronym labels (all-caps strings like `"DOI"`, `"ISBN"`, `"ISSN"`, `"URL"`) are exempt from `gettext_lazy` wrapping, as they do not vary across languages. Mixed or descriptive labels (e.g., `"Call Number"`, `"PubMed ID"`) MUST still be wrapped.
- Q: Should the constitution's Principle VII Testing sub-section (which mandates a locale-activation integration test) be amended to match the project-level decision that runtime i18n testing is not required? → A: Yes — amend constitution to v2.1.1 (PATCH). Replace the locale-activation integration test requirement with a `makemessages` clean-run CI gate and code-review enforcement. The spec clarification is the correct stance; the constitution must stay consistent.

### Session 2026-04-09

- Q: Does the `Date` model need to handle CSL JSON date ranges (two date-parts arrays), or only single-date precision? → A: Range support required — `Date` stores both start and end date-parts (either may be partial/absent); normalizes to a structured datetime/date field when full precision allows; otherwise stores the raw date-parts array as a `JSONField` fallback.
- Q: What mechanism should surface the warning when an unknown identifier type is encountered? → A: Django logging — emit `logger.warning(...)` via `logging.getLogger(__name__)`; no changes to importer return signature.
- Q: Should the Django admin interface be included in this feature's scope? → A: No — admin is removed from this spec entirely. The normalized data model makes a basic admin non-trivial; a dedicated CRUD/admin interface will be specified separately in a later feature.
- Q: Should round-trip tests cover all CSL JSON date forms, or a representative subset? → A: All forms must be supported and tested — year-only, year-month, full year-month-day, single-date range, and partial-range each require dedicated round-trip tests.
- Q: What is the correct role of the CSL JSON `id`, `citation-key`, and `citation-label` fields, and how should `citation_key` be modelled? → A: Research against the CSL 1.0.2 specification and schema confirmed three distinct fields: (1) **`id`** — a processor-internal session-scoped lookup key, required by the CSL JSON schema for citeproc to call `retrieveItem()`; carries no inherent bibliographic meaning. (2) **`citation-key`** — the BibTeX entrykey-style reference handle used in `\cite{...}` / `[@key]` in-document syntax; defined in CSL 1.0.2 Appendix IV as "identifier of the item in the input data file (analogous to BibTeX entrykey)". (3) **`citation-label`** — a processor-generated output label (e.g. "Ferr78"), not a storage field. Our `citation_key` field maps to CSL `citation-key`. `citation_key` is REQUIRED, db-indexed, and unique enforced at application level (not a DB UNIQUE constraint) to support multi-library/multi-tenant deployments. On import, `citation-key` is preferred; `id` is used as a fallback if `citation-key` is absent; both absent → validation error. On export, the CSL `id` field is populated from `citation_key`.

### Session 2026-04-08

- Q: How should CSL JSON fields be stored — flat table, JSON overflow, or normalized relational models? → A: Separate `Name` model for name-variables (linked via `NameThrough` with a role type field); separate `Date` model for date-variables (linked via `DateThrough` with a slot name field); separate `Identifier` model for identifiers (DOI, ISBN, ISSN, etc.); scalar/string/number CSL fields remain as columns on `Item`.
- Q: When importing a CSL JSON item whose citation key already exists, what should happen? → A: Always create a new record; if the citation key conflicts, automatically append a letter suffix to make it unique (e.g. Smith2009 → Smith2009b → Smith2009c). Overwriting existing data is explicitly not supported.
- Q: Should the `type` field enforce the known CSL type list or allow any string? → A: Strictly enforce the known CSL type list; importing an item with an unrecognised type MUST raise a validation error and the item MUST NOT be stored.
- Q: What should the importer do when required CSL JSON fields are missing? → A: Raise a validation error immediately, report which field is missing, and reject the item. No auto-generation or partial storage. See Session 2026-04-09 for the full `citation-key` / `id` field semantics.
- Q: Should the `Identifier` model's type field enforce a fixed choices list or allow any string? → A: Fixed choices for well-known identifier types (DOI, ISBN, ISSN, PMID, URL, etc.); allow any string for custom/unknown types with a warning but no rejection.

### Session 2026-04-09 (analysis remediation)

- Q: Should US2 Acceptance Scenario 5 describe storage or rejection of unknown item types? → A: Rejection only — FR-015 is authoritative. US2 Scenario 5 was rewritten to match: an unknown `type` raises a `ValidationError` and the item is NOT stored.
- Q: Should identifier value format validation be in scope for this feature? → A: Yes — Constitution Principle I mandates that invalid identifiers MUST NOT be silently stored. FR-020 was added explicitly covering DOI, ISBN, ISSN, URL, PMID, PMCID format validators at the model layer (Django validators on `ItemIdentifier.value`). SC-006 tracks the measurable outcome.
- Q: Should round-trip tests cover all 45 CSL item types, not just 3? → A: Yes — SC-002 requires "all item types." T006 (choices completeness) and T013 (round-trip) were extended to cover all 45 types.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All CSL JSON item types defined in the CSL specification can be stored and retrieved; 0 known item types are unsupported.
- **SC-002**: Round-trip conversion (model → CSL JSON → model) produces identical field values for 100% of fields on a reference set of test fixtures covering all item types and all CSL JSON date forms (year-only, year-month, full date, full date range, partial date range).
- **SC-003**: The automated test suite achieves 90% or greater line coverage across all model and conversion code.
- **SC-004**: Every public model class, field, and conversion function has a docstring; 0 undocumented public interfaces in the core module.
- **SC-005**: `django-admin makemessages -l en` runs without errors against the package source and the `literature/locale/en/LC_MESSAGES/django.po` file is present in the repository. Runtime translation behaviour is NOT tested — correct `gettext`/`gettext_lazy` wrapper usage is enforced via code review and the clean `makemessages` run.
- **SC-006**: Model-layer format validators on `ItemIdentifier.value` reject malformed DOI, ISBN, ISSN, URL, PMID, and PMCID values with a `ValidationError`. Unknown identifier types are stored without format validation. This satisfies the Constitution Principle I requirement that "invalid identifiers MUST NOT be silently stored."

## Assumptions

- The CSL JSON specification version 1.0.2 is the target standard; future CSL versions may require spec updates.
- The library is intended as a reusable Django app, so models must be database-agnostic (no vendor-specific field types).
- REST API views, custom front-end views, template tag utilities, and admin/CRUD interfaces are out of scope for this feature.
- Bulk import/export operations (e.g., importing an entire `.json` file of CSL items) are desirable but can be deferred; this feature targets single-item conversion at minimum.
- The app targets Python 3.11+ and Django 4.2+ as minimum supported versions.
- Only the CSL JSON serialization format is targeted; CSL XML and BibTeX are out of scope for this feature.

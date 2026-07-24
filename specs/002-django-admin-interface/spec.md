# Feature Specification: Django Admin Interface for Bibliographic Data

**Feature Branch**: `002-django-admin-interface`
**Created**: 2026-04-10
**Status**: Superseded (2026-07-24)

> **Superseded (2026-07-24).** The bundled, in-core Django admin described here was removed from the installable core because it conflicts with the headless-core scope: the core ships no management surface (see the README *Scope & philosophy* section and `GOALS.md` G3). Reference management returns as part of the opt-in front end. This spec is kept as history of what was built.
**Input**: User description: "A fully functional Django admin interface for managing bibliographic data in django-literature. Administrators can create, view, edit, and delete literature items through the standard Django admin site, with contributors (authors, editors, translators, etc.) organised by role rather than mixed together in a single list. The interface groups the large number of CSL JSON fields into logical sections to keep the form manageable. List views support searching and filtering by common criteria. All models are accessible and the interface requires no additional dependencies beyond Django itself."

## Clarifications

### Session 2026-04-10

- Q: Should the admin interface be accessible to non-superuser staff users with standard Django model-level permissions, or restricted to superusers only? → A: Standard Django model permissions — any `is_staff` user with the relevant `add`/`change`/`delete` permissions can access.
- Q: What should the display string (`__str__`) for each model show in list links and inline dropdowns? → A: `Item` shows title (truncated if long); `Name` shows "Family, Given" (falling back to literal name if family name absent).
- Q: How should contributors (ItemName) be presented on the Item form — flat inline or separate per-role sections — and must ordering be supported? → A: Single flat inline with a role column; the inline MUST support up/down reorder buttons (`move_up_down_links` via django-ordered-model's `OrderedTabularInline`) to change contributor position; drag-and-drop JavaScript is out of scope.
- Q: Should static admin UI strings (verbose names, fieldset headings, inline labels) be wrapped with `gettext_lazy`? → A: Yes — all static admin UI strings MUST use `gettext_lazy`, consistent with the existing model field convention.
- Q: Should the names of the Item fieldset sections be specified in this spec? → A: Deferred — specific section names and field assignments are to be determined during the research and planning phase.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Create and Edit a Literature Item (Priority: P1)

An administrator opens the Django admin site and creates a new bibliographic entry for a journal article. They fill in the title, publication type, and key metadata organised into field groups (Identity, Titles, Publication Details, etc.), then save. Later they open the saved record and correct the volume number.

**Why this priority**: CRUD for the `Item` model is the foundational capability; every other story depends on it. An item list with a working change form delivers immediately usable value.

**Independent Test**: Can be fully tested by logging into admin, navigating to Literature > Items, creating a record, saving, reopening, editing, and saving again — all without any other model being registered.

**Acceptance Scenarios**:

1. **Given** an authenticated admin user, **When** they navigate to the Items list, **Then** they see a table with columns for title, type, and issue date.
2. **Given** the Item add form is open, **When** the user fills required fields and clicks Save, **Then** the record appears in the list view.
3. **Given** an existing Item, **When** the user changes a field and clicks Save, **Then** the updated value is persisted.
4. **Given** the Item change form, **When** it loads, **Then** the many CSL JSON fields are visually grouped into multiple labelled fieldset sections.

---

### User Story 2 - Manage Contributors by Role (Priority: P2)

An administrator editing a literature item needs to assign multiple contributors — an author, two editors, and a translator — each with the correct role. Rather than wading through a flat list of all 26 role types, the contributor section presents names organised by their role.

**Why this priority**: Contributors are the most common related data on a bibliographic item; making their management clear is a primary usability requirement.

**Independent Test**: Can be tested independently by confirming that the Item change form includes inline contributor rows, each with a role selector, and that saved contributors can be re-opened showing the correct role assignment.

**Acceptance Scenarios**:

1. **Given** an Item change form, **When** the user scrolls to the Contributors section, **Then** they see a single flat inline table where each row has a name field and a role dropdown.
2. **Given** a contributor row, **When** the user selects role "Author" and saves, **Then** the contributor is saved with the Author role.
3. **Given** multiple contributors with different roles saved on one item, **When** the item is reopened, **Then** all contributors are shown with their correct roles.
4. **Given** the contributor inline, **When** the user adds a new row and leaves it empty, **Then** the empty row is ignored on save.
5. **Given** multiple contributors on an item, **When** the user uses the reorder buttons (up/down) to change a contributor's position and saves, **Then** the new order is persisted and reflected when the item is reopened.

---

### User Story 3 - Manage Dates and Identifiers Inline (Priority: P3)

An administrator adds an issued date (year/month) and a DOI identifier to a literature item without leaving the item form.

**Why this priority**: Dates and identifiers complete the core bibliographic record. They are separate models but always edited in the context of a single item.

**Independent Test**: Can be tested by confirming that the Item change form contains inline sections for dates and identifiers, and that saving entries in those sections correctly stores related `ItemDate` and `ItemIdentifier` records.

**Acceptance Scenarios**:

1. **Given** an Item change form, **When** the user adds an issued date using the date inline, **Then** the date is saved as a related `ItemDate` record with the correct date type.
2. **Given** an Item change form, **When** the user adds a DOI using the identifier inline, **Then** the identifier is saved as a related `ItemIdentifier` record with type "doi".
3. **Given** existing dates and identifiers on an item, **When** the item is reopened, **Then** all related dates and identifiers are displayed in their respective inline sections.

---

### User Story 4 - Search and Filter the Items List (Priority: P4)

An administrator browsing a growing literature collection needs to find all journal articles published by a specific publisher, or search by title keyword, without exporting data.

**Why this priority**: Discovery support is essential for usability once the collection grows beyond a handful of records.

**Independent Test**: Can be tested independently by verifying that the list view includes a search box that filters by title/author and that sidebar filters for item type and publisher are present and functional.

**Acceptance Scenarios**:

1. **Given** items in the database, **When** the admin types a title keyword in the search box, **Then** only matching items are displayed.
2. **Given** items of multiple types, **When** the admin selects a type filter (e.g., "Journal Article"), **Then** only items of that type are shown.
3. **Given** items with various publishers, **When** the admin applies a publisher filter, **Then** only items from that publisher are shown.
4. **Given** items with various issued years, **When** the admin selects a year from the year filter sidebar, **Then** only items with that issued year are shown.

---

### User Story 5 - Access and Manage Names (Priority: P5)

An administrator needs to review and deduplicate shared `Name` records (persons/entities used across multiple items as contributors).

**Why this priority**: Name records are a shared resource — direct admin access is needed for deduplication and correction, but it is less urgent than item-level operations.

**Independent Test**: Can be tested independently by confirming the Names model is registered in admin with a list view showing family and given name, and a search capability.

**Acceptance Scenarios**:

1. **Given** name records in the database, **When** the admin navigates to Literature > Names, **Then** a list shows each name's family name and given name.
2. **Given** the Names list, **When** the admin searches by family name, **Then** matching records are returned.
3. **Given** an existing Name, **When** the admin edits the given name and saves, **Then** the change is persisted.

---

### Edge Cases

- What happens when an item has no contributors? The item saves successfully; the contributor inline shows as empty.
- What happens when a contributor name record is shared across multiple items and the name is edited? The change propagates to all linked items since the name is a foreign-key relationship.
- What happens when an admin tries to delete a Name record that is referenced by ItemName rows? The admin should show an appropriate warning about cascading deletes before confirming.
- What happens when there are no items in the database? The list view shows an empty state with a prompt to add the first record.
- What happens when the user enters an invalid partial date? Validation feedback is shown inline before the record is saved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The admin interface MUST register all five models — `Item`, `Name`, `ItemName`, `ItemDate`, and `ItemIdentifier` — so they are accessible from the Django admin site. `Item` and `Name` are registered as standalone `ModelAdmin` entries; `ItemName`, `ItemDate`, and `ItemIdentifier` are registered as tabular inlines on the `Item` change form.
- **FR-002**: The `Item` change form MUST organise its fields into multiple named fieldset sections that group related CSL JSON fields together; the specific section names and field assignments are to be determined during the planning phase based on model analysis.
- **FR-003**: `ItemName` (contributor) records MUST be editable as a single flat inline on the `Item` change form, with each row showing the name, the role dropdown, and up/down reorder buttons (`move_up_down_links` from django-ordered-model's `OrderedTabularInline`); row order MUST be persisted on save.
- **FR-004**: `ItemDate` records MUST be editable inline on the `Item` change form, with each row showing the date type and date value.
- **FR-005**: `ItemIdentifier` records MUST be editable inline on the `Item` change form, with each row showing the identifier type and value.
- **FR-006**: The `Item` list view MUST display columns for title, type, and issued year at minimum.
- **FR-007**: The `Item` list view MUST support full-text search across title and citation key.
- **FR-008**: The `Item` list view MUST support sidebar filtering by item type, publisher, and issued year.
- **FR-009**: The `Name` list view MUST display family name and given name, and support search by those fields.
- **FR-010**: The admin interface MUST introduce no **new** third-party Python packages beyond Django itself; use of `django-ordered-model` is permitted as it is already a declared project dependency.
- **FR-011**: All registered models MUST support the standard Django admin CRUD operations (create, read, update, delete).
- **FR-012**: The `Item` list view MUST support sorting by title and issued year.
- **FR-013**: Each model MUST have a human-readable string representation: `Item` displays its title (truncated to a reasonable length); `Name` displays "Family, Given" falling back to the literal name field when family name is absent.
- **FR-014**: All static admin UI strings — including `ModelAdmin` verbose names, fieldset headings, and inline section labels — MUST be wrapped with `gettext_lazy` to support translation, consistent with the existing codebase convention.

### Key Entities

- **Item**: A single bibliographic entry. Contains all scalar CSL JSON fields (title, type, publisher, volume, issue, page, etc.) plus related contributors, dates, and identifiers.
- **Name**: A reusable person or entity record (family name, given name, literal name, suffix, etc.). May appear on multiple items in different roles.
- **ItemName**: Through-model linking a `Name` to an `Item` with an ordered role assignment (one of 26 CSL name-variable roles: author, editor, translator, etc.).
- **ItemDate**: A typed date record linked to an `Item` (e.g., issued, accessed, submitted) stored as a partial date supporting year-only, year-month, and full date precision.
- **ItemIdentifier**: A typed identifier record linked to an `Item` (e.g., DOI, ISBN, ISSN, PMID, URL, arXiv ID).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can create a fully populated literature item — including title, type, contributors, a date, and an identifier — in a single admin session without navigating away from the item form.
- **SC-002**: The item list view returns filtered results within the same page-load time as an unfiltered list, ensuring search and filter do not introduce noticeable delay.
- **SC-003**: All five models appear in the Django admin index without any additional configuration step beyond installing the app.
- **SC-004**: An administrator can locate a specific item by title keyword using the search box without needing to scroll through an unfiltered list.
- **SC-005**: The Item change form is navigable without horizontal scrolling at standard desktop viewport widths, confirming that field grouping keeps the layout manageable.

## Assumptions

- The admin interface grants access to any Django `is_staff` user who holds the standard model-level `add`, `change`, and `delete` permissions for each literature model; no custom permission logic is required. Superusers retain full access by default.
- The application's `INSTALLED_APPS` already includes `django.contrib.admin`, `django.contrib.auth`, and `django.contrib.contenttypes` as required by the standard Django admin.
- The `PartialDateField` from `django-partial-date` renders an acceptable default widget in the admin without custom widget overrides.
- Bulk-action operations beyond the Django default (delete selected) are out of scope for this feature.
- Import/export functionality (CSL JSON round-trip) is out of scope; this feature covers only manual data entry and editing through the admin form.
- Contributor ordering on `ItemName` is managed via django-ordered-model's `OrderedTabularInline`, which provides up/down move buttons (`move_up_down_links`) directly in the inline row; custom drag-and-drop JavaScript is out of scope. The `ItemName` model must inherit from `OrderedModelBase` for this integration to work.
- The `Name` model is managed in its own admin section; inline creation of new `Name` records within the `Item` contributor inline is a convenience enhancement that may be deferred.

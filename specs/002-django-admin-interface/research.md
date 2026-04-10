# Research: Django Admin Interface for Bibliographic Data

**Feature Branch**: `002-django-admin-interface`
**Date**: 2026-04-10

## Research Task 1: CSL JSON Field Grouping for Admin Fieldsets

### Problem

The `Item` model has ~50 scalar fields mirroring the CSL JSON 1.0.2 schema. These need to be organized into logical admin fieldsets so the change form is navigable. Infrequently used sections should start collapsed.

### Research

The CSL JSON 1.0.2 schema organizes fields into several semantic categories:

1. **Identity fields**: `citation_key`, `type` — always required/important
2. **Title fields**: 11 title-related fields; most items use `title` and `container_title`
3. **Long-text fields**: `abstract`, `note`, `annote` — textarea content
4. **Publisher fields**: 4 publisher-related fields
5. **Event fields**: `event_title`, `event_place` — conference/event items only
6. **Numbering fields**: 16 fields for volume, issue, page, edition, etc.
7. **Status/metadata fields**: `status`, `medium`, `genre`, `language`
8. **Archive fields**: 12 fields for archival location and access
9. **Citation metadata fields**: 6 processor-generated or round-trip fields
10. **Keywords/free-form fields**: `keyword`, `categories`, `custom`
11. **Auto timestamps**: `created`, `modified` (not CSL JSON)

### Decision: Fieldset Groupings

Based on frequency of use in typical bibliographic workflows:

**Always open (3 fieldsets):**

- **Identity & Type** — `citation_key`, `type` — core identity, always needed
- **Titles** — `title`, `title_short`, `container_title`, `container_title_short` — primary titles
- **Publication** — `publisher`, `publisher_place` — frequently entered

**Collapsed by default (8 fieldsets):**

- **Numbering** — volume, issue, page, edition, etc. — common for journals/books but many items don't use all fields
- **Additional Titles** — original_title, collection_title, volume_title, etc. — specialized
- **Content** — abstract, note, annote — long text, often imported not manually entered
- **Event** — event_title, event_place — only for conference papers/events
- **Original Publication** — original_publisher, original_publisher_place — rare
- **Archive & Location** — archive through scale/source — specialized academic/archival items
- **Citation Metadata** — journal_abbreviation through year_suffix — mostly processor-generated
- **Classification & Keywords** — language, genre, medium, status, keyword, categories, custom
- **Record Info** — created, modified (read-only)

### Rationale

- Grouping follows CSL JSON semantic categories for intuitive discovery
- Titles are split into "core" (open) and "additional" (collapsed) to avoid overwhelming the form
- Publisher is split into primary (open) and original (collapsed) for the same reason
- Numbering fields are collapsed because their relevance varies by item type
- Citation metadata is collapsed because these are typically processor-generated
- Archive fields are collapsed since they're only relevant for specialized item types
- `number` field stays in the numbering section since it's used across many item types (report number, patent number, etc.)

### Alternatives Considered

1. **Single fieldset per CSL JSON category** — Rejected: too many small open fieldsets
2. **All fields in one long form** — Rejected: unusable with 50+ fields
3. **Dynamic fieldsets based on item type** — Rejected: adds complexity beyond spec requirements; admin UX is not a high priority

---

## Research Task 6: Year Column and Year Filter for Item List View

### Problem

Showing "year" in the Item list view and allowing users to filter by year is an extremely common bibliographic requirement. However, dates are stored in the related `ItemDate` model — not directly on `Item` — and different item types may use different date types (issued, event-date, accessed, etc.).

### Research

**Storage format**: `PartialDateField` stores dates internally as a `DateTimeField` (the seconds component encodes precision: 0=year, 1=month, 2=day). This means standard Django ORM `__year` lookups work at the database level.

**Date type inconsistency**: CSL JSON defines 6 date types (issued, accessed, available-date, event-date, original-date, submitted). Different item types commonly use different "primary" dates:

- Journal articles, books, chapters → `issued`
- Conference papers → `issued` (publication) or `event-date` (presentation)
- Webpages → `issued` or `accessed`

However, `issued` is by far the most universally applicable — it maps to the concept of "publication year" which is what users expect when they see a "Year" column in any bibliography tool.

**Django admin approach**: Since the year lives in a related model, we need:

1. A `Subquery` annotation on the `Item` queryset to pull the issued year
2. A custom display method on `ItemAdmin` to render the annotated year
3. A custom `SimpleListFilter` to build year filter lookups from distinct issued years

### Decision

Use the `issued` date type universally as the source for the "Year" column and year filter. Items without an issued date show blank and are excluded from year filter results.

**Implementation**:

- `get_queryset()` annotates `issued_year` via `Subquery(ItemDate.objects.filter(item=OuterRef('pk'), date_type='issued').values('begin__year')[:1])`
- Custom method `issued_year()` on `ItemAdmin` reads the annotation, with `admin_order_field = 'issued_year'` for sortability
- `IssuedYearFilter(SimpleListFilter)` queries distinct years from `ItemDate(date_type='issued')` for sidebar filter

### Rationale

- "Issued" is the canonical publication date in CSL JSON and the most expected "Year" field
- Using a single date type is simpler and more predictable than trying to pick the "best" date per item type
- Items without an issued date (rare in practice) gracefully show empty rather than showing a confusing fallback
- The annotation approach avoids N+1 queries — year is fetched in the same query as the item list

### Alternatives Considered

1. **Fallback chain** (issued → event-date → original-date → accessed) — Rejected: complex, unpredictable, and hard to explain to users which year they're seeing
2. **Denormalized year field on Item** — Rejected: would require a migration and keeping it in sync; violates the design of having dates in a separate model
3. **Show all date types in list view** — Rejected: clutters the list view with multiple date columns

---

## Research Task 2: Contributor Ordering in Admin

### Problem

`ItemName` currently inherits from `models.Model` with a manual `order PositiveIntegerField`. The spec (FR-003) requires contributor rows to support ordering with up/down reorder buttons; drag-and-drop is explicitly out of scope.

### Research

- `ItemName` inherits from `models.Model`, NOT from `OrderedModel`
- The `order` field is a plain `PositiveIntegerField(default=0)`
- `django-ordered-model` is already installed (required by `pyproject.toml` as a project dependency)
- [`OrderedTabularInline`](https://github.com/django-ordered-model/django-ordered-model#admin-integration) provides `move_up_down_links` — up/down arrow buttons that make AJAX calls to reorder rows; this is the correct ordering UI and satisfies FR-003
- `OrderedTabularInline` requires the through-model to inherit from `OrderedModel` or `OrderedModelBase`
- `OrderedModelBase` is the correct choice since `ItemName` **already has** an `order` field — use `order_field_name = "order"` to map to it, avoiding any schema change
- `order_with_respect_to = 'item'` scopes ordering within each item (all contributors, regardless of role, share a single position sequence within one item)
- Switching from `models.Model` to `OrderedModelBase` adds a custom manager, which Django migrations will detect — a new (non-destructive) migration is required
- The parent `ItemAdmin` must mix in `OrderedInlineModelAdminMixin` for the URL routes serving move AJAX calls to be registered
- FR-010 ("no Python dependencies beyond Django itself") is satisfied because `django-ordered-model` is already a project dependency — this uses existing infrastructure, not a new package

### Decision

Update `ItemName` to inherit from `OrderedModelBase` with `order_field_name = "order"` and `order_with_respect_to = 'item'`. Use `OrderedTabularInline` + `OrderedInlineModelAdminMixin` in the admin.

**Admin inline pattern** (from django-ordered-model README):

```python
from ordered_model.admin import OrderedTabularInline, OrderedInlineModelAdminMixin

class ItemNameInline(OrderedTabularInline):
    model = ItemName
    fields = ("name", "role", "order", "move_up_down_links")
    readonly_fields = ("order", "move_up_down_links")
    ordering = ("order",)
    extra = 1

class ItemAdmin(OrderedInlineModelAdminMixin, admin.ModelAdmin):
    inlines = [ItemNameInline, ...]
```

### Rationale

- Provides a proper ordering UX (up/down buttons) without drag-and-drop or manual number editing
- `OrderedModelBase` removes the need for users to type raw order integers
- No schema change required — just a manager addition
- `django-ordered-model` is already a declared dependency, so FR-010 is not violated
- `order_with_respect_to = 'item'` gives a flat global position sequence matching the flat inline presentation

### Alternatives Considered

1. **Standard `TabularInline` with editable `order` field** — Rejected: unacceptable UX; users must manually enter integers with no feedback about the current sequence
2. **Custom JavaScript drag-and-drop** — Rejected: out of scope; FR-010 prohibits new admin-level packages
3. **`order_with_respect_to = ('item', 'role')`** — Considered: would scope ordering per (item, role) group, but the flat inline shows all contributors together, making per-group position integers confusing to users; flat per-item ordering is more intuitive

---

## Research Task 3: Django Admin Collapse Behavior

### Problem

Confirm how `classes: ['collapse']` works for Django admin fieldsets.

### Decision

Standard Django admin collapse is used. Fieldsets with `classes: ['collapse']` are rendered hidden by default with a toggle header. Clicking the header expands/collapses the content. This is built into Django's admin CSS and JavaScript — no additional dependencies needed.

Requirements:

- Fieldsets must have a non-None name for collapse to work properly
- Use `_("Fieldset Name")` for i18n compliance (Principle VII)
- Can combine with `wide` class: `classes: ['collapse', 'wide']`

---

## Research Task 4: Admin Registration and Test Settings

### Problem

The current test settings (`tests/settings.py`) do not include `django.contrib.admin`, `django.contrib.auth`, or `django.contrib.contenttypes` in `INSTALLED_APPS`. Admin tests will need these.

### Decision

Tests for the admin interface require a separate or augmented settings configuration that includes the Django admin dependencies. Options:

1. Add admin apps to the main test settings (may affect existing tests)
2. Use a `conftest.py` settings override for admin-specific tests

The simplest approach is to add the required apps to the existing test settings since they don't interfere with model tests and are needed by the spec assumption ("INSTALLED_APPS already includes admin/auth/contenttypes").

### Rationale

Adding `django.contrib.admin`, `django.contrib.auth`, `django.contrib.contenttypes`, and `django.contrib.sessions` to test settings is non-destructive — existing model tests are unaffected. This also validates that the admin module loads correctly in an environment matching real-world usage.

---

## Research Task 5: Item `__str__` Method

### Problem

The spec requires `Item.__str__` to display the title (truncated if long). Currently it returns `self.citation_key`.

### Decision

Update `Item.__str__` to return the title truncated to a reasonable length (e.g., 80 characters), falling back to citation_key if no title is set. This satisfies FR-013.

### Rationale

- Title is more human-readable than citation key in admin list views
- Truncation prevents excessively long strings in dropdowns and breadcrumbs
- Fallback to citation_key handles edge cases where title is empty

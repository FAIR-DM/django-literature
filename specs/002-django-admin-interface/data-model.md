# Data Model: Django Admin Interface for Bibliographic Data

**Feature Branch**: `002-django-admin-interface`
**Date**: 2026-04-10

## Overview

This feature adds no new database models. It registers the existing five models
(`Item`, `Name`, `ItemName`, `ItemDate`, `ItemIdentifier`) in the Django admin
and configures their presentation. The "data model" for this feature is the
admin configuration layer — `ModelAdmin` classes, inlines, fieldsets, and
list/filter/search definitions.

## Entities (Admin Configuration)

### ItemAdmin

**Registered model**: `Item`

**List view** (`list_display`):

- `title` — primary display column
- `type` — item type (choices display)
- `issued_year` — year extracted from the related "issued" `ItemDate` (custom column)
- `citation_key` — unique identifier

**Search** (`search_fields`):

- `title`
- `citation_key`

**Filters** (`list_filter`):

- `type` — sidebar filter by item type
- `IssuedYearFilter` — custom `SimpleListFilter` for year (see below)
- `publisher` — sidebar filter by publisher

**Sorting** (`ordering`):

- `-created` (default, matches model Meta)
- `issued_year` column is sortable via `admin_order_field` pointing to the annotated year

**Fieldsets** (12 sections):

| # | Fieldset Name | Fields | Collapsed |
|---|---------------|--------|-----------|
| 1 | Identity & Type | `citation_key`, `type` | No |
| 2 | Titles | `title`, `title_short`, `container_title`, `container_title_short` | No |
| 3 | Publication | `publisher`, `publisher_place` | No |
| 4 | Numbering | `volume`, `issue`, `page`, `page_first`, `number`, `number_of_pages`, `number_of_volumes`, `edition`, `version`, `chapter_number`, `collection_number`, `section`, `part`, `supplement`, `printing` | Yes |
| 5 | Additional Titles | `original_title`, `collection_title`, `volume_title`, `volume_title_short`, `part_title`, `reviewed_title`, `reviewed_genre` | Yes |
| 6 | Content | `abstract`, `note`, `annote` | Yes |
| 7 | Event | `event_title`, `event_place` | Yes |
| 8 | Original Publication | `original_publisher`, `original_publisher_place` | Yes |
| 9 | Archive & Location | `archive`, `archive_collection`, `archive_location`, `archive_place`, `authority`, `jurisdiction`, `call_number`, `dimensions`, `division`, `scale`, `source`, `references` | Yes |
| 10 | Citation Metadata | `journal_abbreviation`, `citation_label`, `citation_number`, `first_reference_note_number`, `locator`, `year_suffix` | Yes |
| 11 | Classification & Keywords | `language`, `genre`, `medium`, `status`, `keyword`, `categories`, `custom` | Yes |
| 12 | Record Info | `created`, `modified` | Yes (read-only) |

**Inlines** (3):

- `ItemNameInline` — contributors (via `OrderedTabularInline`; parent `ItemAdmin` must mixin `OrderedInlineModelAdminMixin`)
- `ItemDateInline` — dates
- `ItemIdentifierInline` — identifiers

---

### NameAdmin

**Registered model**: `Name`

**List view** (`list_display`):

- `family` — family name
- `given` — given name
- `literal` — literal/institutional name

**Search** (`search_fields`):

- `family`
- `given`
- `literal`

**Fieldsets**: None (default single form with all fields)

---

### ItemNameInline

**Model**: `ItemName` (through-model)
**Type**: `OrderedTabularInline` (from `ordered_model.admin`)
**Fields**: `name`, `role`, `order`, `move_up_down_links`
**Readonly fields**: `order`, `move_up_down_links`
**Extra rows**: 1
**Ordering**: `order` (ascending)

Note: The parent `ItemAdmin` MUST inherit `OrderedInlineModelAdminMixin` (before `admin.ModelAdmin`) so that the AJAX URL routes for move up/down are registered.

---

### ItemDateInline

**Model**: `ItemDate`
**Type**: `TabularInline`
**Fields**: `date_type`, `begin`, `end`, `season`, `circa`, `literal`, `raw`
**Extra rows**: 1

Note: `raw_date_parts` is excluded from the inline — it's a JSON fallback field not meant for manual editing.

---

### ItemIdentifierInline

**Model**: `ItemIdentifier`
**Type**: `TabularInline`
**Fields**: `type`, `value`
**Extra rows**: 1

---

## Model Changes Required

### ItemName (base class change)

**Current**: `class ItemName(models.Model)`
**New**: `class ItemName(OrderedModelBase)` (from `ordered_model.models`)

Required additions to the class body:

```python
from ordered_model.models import OrderedModelBase

class ItemName(OrderedModelBase):
    # ... existing fields unchanged ...
    order_field_name = "order"          # maps to existing PositiveIntegerField
    order_with_respect_to = "item"      # ordering scoped per item (flat global position)
```

No schema change is required — the `order` field already exists. The change adds a custom `OrderedModelManager`, which Django migrations will detect; a new (non-destructive) migration must be generated with `makemigrations`.

The `class Meta.ordering = ["item", "role", "order"]` and existing index on `(item, role, order)` are preserved unchanged.

### Item.**str**

**Current**: Returns `self.citation_key`
**New**: Returns `self.title` truncated to 80 characters, falling back to `self.citation_key` if title is empty.

This satisfies FR-013: "Item displays its title (truncated to a reasonable length)".

### Migrations

One non-destructive migration is required: the `ItemName` base-class change from `models.Model` to `OrderedModelBase` causes Django to detect a new `OrderedModelManager` and generate a manager-only migration (no schema alteration — no columns are added, changed, or deleted). All other changes are admin configuration only.

---

### Year Column & Filter Implementation

The "issued year" is stored in `ItemDate.begin` (a `PartialDateField` which uses `DateTimeField` internally) where `date_type='issued'`. Extracting it for list display and filtering requires:

**List column (`issued_year`)**:

- Override `get_queryset()` on `ItemAdmin` to annotate each `Item` with the year from its related "issued" `ItemDate`
- Use `Subquery` + `ExtractYear` to annotate: `issued_year = Subquery(ItemDate.objects.filter(item=OuterRef('pk'), date_type='issued').values('begin__year')[:1])`
- Note: `PartialDateField` stores as `DateTimeField`, so `__year` lookups work at the DB level
- Custom method on `ItemAdmin` reads the annotation; `admin_order_field = 'issued_year'` enables column sorting
- Items without an issued date display "—" (empty value display)

**Year filter (`IssuedYearFilter`)**:

- Custom `SimpleListFilter` subclass
- `lookups()`: queries distinct years from `ItemDate` where `date_type='issued'`, ordered descending
- `queryset()`: filters `Item.objects.filter(item_dates__date_type='issued', item_dates__begin__year=value)`
- Shows all years that have at least one item, most recent first

**UX consistency note**: The "issued" date type is used universally as the year source. While different item types may have different relevant dates (e.g., `event-date` for conferences), "issued" is the most common and the one users expect when they see "Year" in a bibliography. Items without an issued date simply show blank in the year column and are excluded from year filter results.

## Validation Rules

- All existing model-level validation (identifier validators on `ItemIdentifier.clean()`) is respected by the admin
- The `unique_name_per_role_per_item` constraint on `ItemName` prevents duplicate contributor assignments
- The `unique_date_type_per_item` constraint on `ItemDate` prevents duplicate date types
- The `unique_identifier_type_per_item` constraint on `ItemIdentifier` prevents duplicate identifier types

## State Transitions

N/A — No state machine or workflow. All models support standard CRUD.

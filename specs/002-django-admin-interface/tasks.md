# Tasks: Django Admin Interface for Bibliographic Data

**Input**: Design documents from `/specs/002-django-admin-interface/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ quickstart.md ✅

**User stories (priority order)**:

- US1 (P1) — Create and Edit a Literature Item
- US2 (P2) — Manage Contributors by Role
- US3 (P3) — Manage Dates and Identifiers Inline
- US4 (P4) — Search and Filter the Items List
- US5 (P5) — Access and Manage Names

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Wire up the Django admin dependencies and create the skeleton files that all
user stories build on.

- [X] T001 Update `tests/settings.py`: add `django.contrib.admin`, `django.contrib.auth`, `django.contrib.contenttypes`, `django.contrib.sessions` to `INSTALLED_APPS`
- [X] T002 Create `literature/admin.py` with module docstring and a single `pass` placeholder (no registrations yet)
- [X] T003 [P] Add `admin_user` pytest fixture to `tests/conftest.py` — creates a `User` with `is_staff=True` and `is_superuser=True` for HTTP admin tests

### System Validation — Phase 1

- [X] T004 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [X] T005 ⚠️ CRITICAL: Run existing tests: `poetry run pytest -v` — ALL tests MUST pass (confirms settings change is non-destructive)

**Checkpoint — Setup Complete**: System checks pass and existing tests stay green. Proceed to Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Update `Item.__str__` to show the title — required by FR-013 and used in admin list links, inlines, and breadcrumbs throughout all five user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Write failing test in `tests/test_models.py`: `Item.__str__` returns truncated title (≤80 chars); falls back to `citation_key` when title is empty; truncates with `…` suffix at 80 characters
- [X] T006b Write failing test in `tests/test_models.py`: `Name.__str__` returns `"Family, Given"` when family name present; returns literal name when family absent; returns `"Name #<pk>"` as last fallback
- [X] T007 Implement `Item.__str__` in `literature/models.py`: return `self.title[:80] + "…"` when title > 80 chars, `self.title` when title ≤ 80 chars, otherwise `self.citation_key`

### System Validation — Phase 2

- [X] T008 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [X] T009 ⚠️ CRITICAL: Run foundation tests: `poetry run pytest tests/test_models.py -v` — ALL tests MUST pass before proceeding to any user story

**Checkpoint — Foundation Ready**: `Item.__str__` is green. User story phases can now begin.

---

## Phase 3: User Story 1 — Create and Edit a Literature Item (Priority: P1) 🎯 MVP

**Goal**: Register `Item` in the Django admin with a fully-grouped change form and a usable
list view including the issued year column.

**Independent Test**: Navigate to `/admin/literature/item/`, create a new item, save it,
reopen it, edit a field, save again — all without any other models being registered.

### Tests for User Story 1 ⚠️ Write FIRST — ensure they FAIL before implementing T011

- [X] T010 [US1] Write failing tests in `tests/test_admin.py`:
  - Item changelist URL (`/admin/literature/item/`) returns HTTP 200
  - Item add URL (`/admin/literature/item/add/`) returns HTTP 200
  - Item change URL returns HTTP 200 for a saved item
  - Item changelist response contains columns: title, type, citation key, and year
  - Item change form response contains fieldset headings: "Identity & Type", "Titles", "Publication"

### Implementation for User Story 1

- [X] T011 [US1] Implement `ItemAdmin` in `literature/admin.py`:
  - Register `Item` with `@admin.register(Item)`
  - `list_display = ("title_display", "type", "issued_year", "citation_key")`
  - `title_display()` method — calls `str(obj)` (uses `__str__`)
  - `get_queryset()` — annotates queryset with `issued_year` using `Subquery(ItemDate.objects.filter(item=OuterRef("pk"), date_type="issued").values("begin__year")[:1])`
  - `issued_year()` display method — reads annotation, returns `"—"` when `None`; `short_description = _("year")`; `admin_order_field = "issued_year"`
  - `search_fields = ("title", "citation_key")`
  - `list_filter = ("type", "publisher")`
  - `ordering = ("-created",)`
  - `readonly_fields = ("created", "modified")`
  - 12 fieldsets per `data-model.md` with `gettext_lazy` headings and `classes: ["collapse"]` for fieldsets 4–12

### System Validation — Phase 3

- [X] T012 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [X] T013 ⚠️ CRITICAL: Run US1 tests: `poetry run pytest tests/test_models.py tests/test_admin.py -v` — ALL tests MUST pass

**Checkpoint — US1 Complete**: Item list view and change form load; fieldsets visible; year column shows.

---

## Phase 4: User Story 2 — Manage Contributors by Role (Priority: P2)

**Goal**: Add a flat contributor inline (`ItemNameInline`) to the `Item` change form so
administrators can assign names with roles in a single table.

**Independent Test**: Open a saved `Item`, add two contributor rows with different roles,
save, reopen — all contributors appear with correct roles.

### Tests for User Story 2 ⚠️ Write FIRST — ensure they FAIL before implementing T014b–T015

- [X] T014 [US2] Write failing tests in `tests/test_admin.py`:
  - Item change form response contains a `<div>` or heading for the contributor inline section
  - POST to Item change URL with an `item_names-TOTAL_FORMS` management form saves a new `ItemName` with correct role
  - Reopening the item shows the saved contributor
  - Item change form response contains `move_up_down_links` controls (up/down ordering buttons)

### Implementation for User Story 2

- [X] T014b [US2] Update `ItemName` model in `literature/models.py` to inherit from `OrderedModelBase`:
  - Change `class ItemName(models.Model)` → `class ItemName(OrderedModelBase)`
  - Add `from ordered_model.models import OrderedModelBase` import
  - Add class attribute `order_field_name = "order"`
  - Add class attribute `order_with_respect_to = "item"`
  - Preserve all existing fields, constraints, indexes, and `class Meta.ordering` unchanged
- [X] T014c [US2] Generate migration for `ItemName` manager change: `poetry run python manage.py makemigrations literature --name itemname_ordered_model_base` — verify it is non-destructive (manager-only change, no schema alteration)
- [X] T015 [US2] Implement `ItemNameInline` in `literature/admin.py` and wire to `ItemAdmin`:
  - `from ordered_model.admin import OrderedTabularInline, OrderedInlineModelAdminMixin`
  - `class ItemNameInline(OrderedTabularInline)` with `model = ItemName`
  - `fields = ("name", "role", "order", "move_up_down_links")`
  - `readonly_fields = ("order", "move_up_down_links")`
  - `extra = 1`
  - `ordering = ("order",)`
  - `verbose_name = _("contributor")`; `verbose_name_plural = _("contributors")`
  - Update `ItemAdmin` class signature: `class ItemAdmin(OrderedInlineModelAdminMixin, admin.ModelAdmin)`
  - Add `inlines = [ItemNameInline]` to `ItemAdmin`

### System Validation — Phase 4

- [X] T016 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [X] T017 ⚠️ CRITICAL: Run US1+US2 tests: `poetry run pytest tests/test_models.py tests/test_admin.py -v` — ALL tests MUST pass

**Checkpoint — US2 Complete**: Contributor inline visible and saves correctly.

---

## Phase 5: User Story 3 — Manage Dates and Identifiers Inline (Priority: P3)

**Goal**: Add `ItemDateInline` and `ItemIdentifierInline` to the `Item` change form so
dates and identifiers can be managed without leaving the item form.

**Independent Test**: Open a saved `Item`, add an "issued" date and a DOI identifier, save,
reopen — both the date and identifier appear in their respective inline sections.

### Tests for User Story 3 ⚠️ Write FIRST — ensure they FAIL before implementing T019–T021

- [X] T018 [US3] Write failing tests in `tests/test_admin.py`:
  - Item change form response contains the date inline management form (`item_dates-TOTAL_FORMS`)
  - Item change form response contains the identifier inline management form (`item_identifiers-TOTAL_FORMS`)
  - POST that includes an `ItemDate` (type=issued, begin=2024) saves a related `ItemDate` record
  - POST that includes an `ItemIdentifier` (type=DOI, value=10.1234/test) saves a related `ItemIdentifier` record

### Implementation for User Story 3

- [X] T019 [US3] Implement `ItemDateInline` in `literature/admin.py`:
  - `class ItemDateInline(admin.TabularInline)` with `model = ItemDate`
  - `fields = ("date_type", "begin", "end", "season", "circa", "literal", "raw")`
  - `extra = 1`
  - `verbose_name = _("date")`; `verbose_name_plural = _("dates")`
- [X] T020 [US3] Implement `ItemIdentifierInline` in `literature/admin.py`:
  - `class ItemIdentifierInline(admin.TabularInline)` with `model = ItemIdentifier`
  - `fields = ("type", "value")`
  - `extra = 1`
  - `verbose_name = _("identifier")`; `verbose_name_plural = _("identifiers")`
- [X] T021 [US3] Add `ItemDateInline` and `ItemIdentifierInline` to `ItemAdmin.inlines` in `literature/admin.py`

### System Validation — Phase 5

- [X] T022 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [X] T023 ⚠️ CRITICAL: Run US1–US3 tests: `poetry run pytest tests/test_models.py tests/test_admin.py -v` — ALL tests MUST pass

**Checkpoint — US3 Complete**: Date and identifier inlines visible and save correctly.

---

## Phase 6: User Story 4 — Search and Filter the Items List (Priority: P4)

**Goal**: Wire up the custom `IssuedYearFilter` sidebar filter so administrators can narrow
the list by type, publisher, and year.

**Independent Test**: With items of different types and years in the DB, clicking "Journal
Article" in the type filter returns only journal articles; selecting a year returns only items
with that issued year; entering a title keyword in the search box returns matching items.

### Tests for User Story 4 ⚠️ Write FIRST — ensure they FAIL before implementing T025–T026

- [X] T024 [US4] Write failing tests in `tests/test_admin.py`:
  - Item changelist with `?q=<title_fragment>` returns only matching items
  - Item changelist with `?type=article-journal` returns only journal articles
  - Item changelist with `?publisher=<value>` returns only matching publisher items
  - Item changelist with `?issued_year=2024` returns only items with issued year 2024
  - Year filter sidebar contains an entry for each year that has at least one issued date

### Implementation for User Story 4

- [X] T025 [US4] Implement `IssuedYearFilter(admin.SimpleListFilter)` in `literature/admin.py`:
  - `title = _("year")`; `parameter_name = "issued_year"`
  - `lookups()`: queries `ItemDate.objects.filter(date_type="issued").values_list("begin__year", flat=True).distinct().order_by("-begin__year")`; yields `(str(year), str(year))` tuples
  - `queryset()`: when value set, filters `queryset.filter(item_dates__date_type="issued", item_dates__begin__year=self.value())`
- [X] T026 [US4] Add `IssuedYearFilter` to `ItemAdmin.list_filter` in `literature/admin.py` (between `type` and `publisher`)

### System Validation — Phase 6

- [X] T027 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [X] T028 ⚠️ CRITICAL: Run US1–US4 tests: `poetry run pytest tests/test_models.py tests/test_admin.py -v` — ALL tests MUST pass

**Checkpoint — US4 Complete**: Search, type filter, publisher filter, and year filter all functional.

---

## Phase 7: User Story 5 — Access and Manage Names (Priority: P5)

**Goal**: Register `Name` in the Django admin so administrators can browse, search, and
deduplicate shared name records independently of the `Item` form.

**Independent Test**: Navigate to `/admin/literature/name/`, search by family name, open a
record, edit the given name, save — all without touching any `Item`.

### Tests for User Story 5 ⚠️ Write FIRST — ensure they FAIL before implementing T030

- [X] T029 [US5] Write failing tests in `tests/test_admin.py`:
  - Name changelist URL (`/admin/literature/name/`) returns HTTP 200
  - Name changelist with `?q=<family_fragment>` returns only matching names
  - Name change URL returns HTTP 200 for a saved name
  - POST to Name change URL with updated `given` field persists the change

### Implementation for User Story 5

- [X] T030 [US5] Implement `NameAdmin` in `literature/admin.py` and register:
  - `@admin.register(Name)` with `class NameAdmin(admin.ModelAdmin)`
  - `list_display = ("family", "given", "literal")`
  - `search_fields = ("family", "given", "literal")`

### System Validation — Phase 7

- [X] T031 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass before proceeding
- [X] T032 ⚠️ CRITICAL: Run full feature tests: `poetry run pytest tests/test_models.py tests/test_admin.py -v` — ALL tests MUST pass

**Checkpoint — US5 Complete**: All five models accessible. Admin feature fully functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify i18n compliance, update documentation, and confirm the quickstart guide
still matches the implementation.

- [X] T033 [P] Verify i18n: run `poetry run python -m django makemessages --all` from the repo root and confirm it exits cleanly with no syntax errors; fix any untranslatable strings found
- [X] T034 [P] Update `docs/usage.md` (or create `docs/admin.md`) with a short section documenting admin availability, required `INSTALLED_APPS` entries, and a link to `quickstart.md`

### System Validation — Final

- [X] T035 ⚠️ CRITICAL: Run Django system checks: `poetry run python manage.py check` — MUST pass
- [X] T036 ⚠️ CRITICAL: Run full test suite: `poetry run pytest -v` — ALL tests MUST pass

**Checkpoint — Feature Complete**: System checks pass. Full test suite green. i18n clean. Docs updated.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)          — No dependencies; start immediately
Phase 2 (Foundational)   — Requires Phase 1 completion; BLOCKS all user stories
Phase 3 (US1)            — Requires Phase 2 completion 🎯 MVP
Phase 4 (US2)            — Requires Phase 3 completion (needs ItemAdmin registered)
Phase 5 (US3)            — Requires Phase 3 completion (needs ItemAdmin registered)
Phase 6 (US4)            — Requires Phase 3 completion (needs ItemAdmin registered)
Phase 7 (US5)            — Independent of US2–US4; requires Phase 2 completion
Phase 8 (Polish)         — Requires all user story phases complete
```

**Note**: US2 (Phase 4), US3 (Phase 5), US4 (Phase 6), and US5 (Phase 7) are all
independent of each other — they can be developed in any order after Phase 3 is done.

### Parallel Execution Examples

**After Phase 3 is complete**, the following can proceed in parallel:

| Stream A | Stream B | Stream C |
|----------|----------|----------|
| Phase 4 (US2) — Contributors | Phase 5 (US3) — Dates/Identifiers | Phase 7 (US5) — Names |

Phase 6 (US4) depends only on Phase 3 and can run in parallel with streams A, B, C if separate
contributors are adding the `IssuedYearFilter`.

### Phase Gate Tasks Summary

| Phase | System Check Task | Pytest Command |
|-------|-------------------|----------------|
| Phase 1 (Setup) | T004 | `poetry run pytest -v` |
| Phase 2 (Foundational) | T008 | `poetry run pytest tests/test_models.py -v` |
| Phase 3 (US1) | T012 | `poetry run pytest tests/test_models.py tests/test_admin.py -v` |
| Phase 4 (US2) | T016 | `poetry run pytest tests/test_models.py tests/test_admin.py -v` |
| Phase 5 (US3) | T022 | `poetry run pytest tests/test_models.py tests/test_admin.py -v` |
| Phase 6 (US4) | T027 | `poetry run pytest tests/test_models.py tests/test_admin.py -v` |
| Phase 7 (US5) | T031 | `poetry run pytest tests/test_models.py tests/test_admin.py -v` |
| Phase 8 (Polish) | T035 | `poetry run pytest -v` |

---

## Implementation Strategy

**MVP scope**: Complete Phase 1 → 2 → 3 (T001–T013). This delivers a fully functional Item
CRUD admin with grouped fieldsets and the year column — the core value of the feature.

**Incremental delivery**:

1. **T001–T013** — MVP: Item CRUD with fieldsets and year column (US1 alone)
2. - **T014–T017** — Add contributor management (US2)
3. - **T018–T023** — Add date and identifier inlines (US3)
4. - **T024–T028** — Add year filter and refine search/filters (US4)
5. - **T029–T032** — Add Names admin (US5)
6. - **T033–T036** — Polish, docs, i18n verification

**Total tasks**: 39
**Tasks per user story**: US1=4, US2=6 (includes model change T014b + migration T014c), US3=5, US4=5, US5=4, Setup/Foundation/Polish=15 (includes T006b)
**Files affected**: `literature/admin.py` (new), `literature/models.py` (1 method + base class change), `tests/settings.py`, `tests/conftest.py`, `tests/test_admin.py` (new), `literature/migrations/` (new migration for ItemName), `docs/`

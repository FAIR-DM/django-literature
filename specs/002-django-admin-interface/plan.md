# Implementation Plan: Django Admin Interface for Bibliographic Data

**Branch**: `002-django-admin-interface` | **Date**: 2026-04-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-django-admin-interface/spec.md`

## Summary

Register all five literature models (`Item`, `Name`, `ItemName`, `ItemDate`, `ItemIdentifier`) in the Django admin with grouped fieldsets, tabular inlines, search, and basic filtering. Uses only standard Django admin tooling — no third-party admin packages. Item fields are organized into 12 logical fieldsets based on CSL JSON semantic categories, with infrequently used sections collapsed by default.

## Technical Context

**Language/Version**: Python 3.11+ + Django 4.2+
**Primary Dependencies**: Django (admin framework), `django-partial-date` (PartialDateField widget), `django-ordered-model` (used for `OrderedTabularInline` and `OrderedInlineModelAdminMixin` on the contributor inline)
**Storage**: SQLite (development/test), PostgreSQL (reference)
**Testing**: pytest + pytest-django
**Target Platform**: Django web application (server-side)
**Project Type**: Reusable Django library
**Performance Goals**: N/A — standard Django admin performance
**Constraints**: FR-010 — no Python dependencies beyond Django itself for the admin module
**Scale/Scope**: 5 models registered, ~50 fields on Item, 3 inlines, 12 fieldsets, 1 custom list filter

## Constitution Check (Pre-Research)

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (CSL-JSON)**: ✅ PASS — No CSL-JSON fields are added, changed, or removed. The admin exposes existing fields only. No import/export behavior is changed.
- **Principle II (Embeddable Package)**: ✅ PASS — The admin module is auto-discovered via Django's `admin.autodiscover()`. No mandatory structural changes required in host projects. The admin is available when `django.contrib.admin` is in `INSTALLED_APPS`.
- **Principle III (Data Integrity)**: ✅ PASS — No new migrations needed. No schema changes. Existing model constraints (unique constraints on ItemName, ItemDate, ItemIdentifier) are enforced by the admin. The only code change is to `Item.__str__` which has no schema impact.
- **Principle IV (Test-First)**: ✅ PASS — Tests will be written before implementation. Admin views will be tested via HTTP requests to verify they load without errors.
- **Principle V (Documentation)**: ✅ PASS — The admin interface will be documented in the quickstart guide and package documentation. No new public Python APIs, settings, or template tags are introduced.
- **Principle VI (Demo App)**: ⚠️ NOTED — The admin module changes the `admin.py` registration. The demo/test app settings need `django.contrib.admin` and related apps. Tests will verify admin view loading.
- **Principle VII (i18n)**: ✅ PASS — All fieldset headings, inline verbose names, and any new static strings will use `gettext_lazy`. `makemessages` will be verified to run cleanly.

## Project Structure

### Documentation (this feature)

```text
specs/002-django-admin-interface/
├── plan.md              # This file
├── research.md          # Phase 0 output — fieldset groupings, ordering research
├── data-model.md        # Phase 1 output — admin configuration specification
├── quickstart.md        # Phase 1 output — setup and usage guide
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
literature/
├── admin.py             # NEW — ModelAdmin classes, inlines, fieldsets
├── models.py            # MODIFIED — Item.__str__ update (title truncation)
└── ...                  # No other files changed

tests/
├── settings.py          # MODIFIED — add admin/auth/contenttypes/sessions to INSTALLED_APPS
├── test_admin.py        # NEW — admin view load tests, fieldset verification
└── ...                  # Existing test files unchanged
```

**Structure Decision**: Single Django app structure. The admin module is a single `admin.py` file following Django convention. Admin tests go in a dedicated `tests/test_admin.py`. No contracts directory needed — this feature exposes no external interfaces beyond the standard Django admin.

## Constitution Check (Post-Design)

- **Principle I (CSL-JSON)**: ✅ PASS — Confirmed: no changes to CSL-JSON mapping or data model.
- **Principle II (Embeddable Package)**: ✅ PASS — Confirmed: `admin.py` is auto-discovered. Host projects only need `django.contrib.admin` which is a standard Django dependency.
- **Principle III (Data Integrity)**: ✅ PASS — Confirmed: one non-destructive manager-only migration for `ItemName` (base-class change to `OrderedModelBase`; no schema alteration). `Item.__str__` change is display-only. Existing model constraints are unchanged.
- **Principle IV (Test-First)**: ✅ PASS — Test plan: admin changelist and change form HTTP tests for all registered models.
- **Principle V (Documentation)**: ✅ PASS — quickstart.md covers setup and usage. Package docs should be updated to document admin availability.
- **Principle VI (Demo App)**: ✅ PASS — test settings updated to include admin apps; admin views tested via HTTP requests.
- **Principle VII (i18n)**: ✅ PASS — All fieldset names use `_()`. All inline verbose names already use `gettext_lazy` via model Meta. No templates introduced. `makemessages` verification planned as a test task.

## Complexity Tracking

No constitution violations. No complexity tracking entries needed.

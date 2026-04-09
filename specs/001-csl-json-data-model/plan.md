# Implementation Plan: CSL JSON Data Model and Conversion

**Branch**: `001-csl-json-data-model` | **Date**: 2026-04-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-csl-json-data-model/spec.md`

## Summary

Implement a normalized Django data model that faithfully represents the CSL JSON 1.0.2 specification as relational database tables. The core `Item` model stores all scalar/string/number CSL fields as columns. Name-variables (author, editor, etc.) are stored via a `Name` model linked through an `ItemName` ordered through-model that records role type and position. Date-variables (issued, accessed, etc.) are stored via an `ItemDate` model using `django-partial-date`'s `PartialDateField` for partial-date precision. Identifiers (DOI, ISBN, etc.) are stored in a dedicated `ItemIdentifier` model. Bidirectional CSL JSON serialization/deserialization is provided with full round-trip fidelity. The `django-ordered-model` package provides ordering for contributor names within each role-per-item scope.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Django 4.2+, `django-partial-date` (ktowen/django_partial_date), `django-ordered-model` 3.7+, `python-dateutil`, `citeproc-py`
**Storage**: Database-agnostic (SQLite for dev/test; no PostgreSQL-specific fields)
**Testing**: pytest + pytest-django
**Target Platform**: Reusable Django app (any Django host project)
**Project Type**: Library (installable Django app)
**Performance Goals**: N/A for this feature (data model + conversion)
**Constraints**: Database-agnostic — no PostgreSQL-specific features. `JSONField` only for `custom` CSL field and unparseable date fallback. All core relational data uses standard Django field types.
**Scale/Scope**: Single Django app, ~5 models, ~2 conversion modules, 90%+ test coverage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. CSL-JSON as Lingua Franca | PASS | All models map directly to CSL JSON 1.0.2 schema. Every field documented with CSL JSON equivalent. |
| II. Embeddable Django Package | PASS | Standard Django app structure. All models in `literature` namespace. No host-project structural requirements. |
| III. Data Integrity & Long-Term Persistence | PASS | Migrations included. Partial dates via `django-partial-date`. Relational structure for names, dates, identifiers. `JSONField` only for `custom` overflow and date fallback. |
| IV. Test-First Quality | PASS | pytest + pytest-django. Test structure mirrors source. Round-trip tests for all date forms. 90%+ target coverage. |
| V. Documentation Critical | PASS | All models, fields, and conversion functions will have docstrings mapping to CSL JSON. |
| VI. Living Demo & Reference App | PASS | Test app in `tests/` exercises all models. Existing `manage.py` provides the scaffold. |

**Gate Result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-csl-json-data-model/
├── plan.md              # This file
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: entity/field/relationship design
├── quickstart.md        # Phase 1: developer getting-started guide
├── contracts/           # Phase 1: CSL JSON serialization contracts
│   └── csl-json.md      # Import/export contract specification
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
literature/
├── __init__.py
├── apps.py
├── choices.py           # CSL type choices, name role choices, identifier type choices
├── models.py            # Item, Name, ItemName, ItemDate, ItemIdentifier
├── converters.py        # CSL JSON serialization/deserialization
├── utils/
│   ├── __init__.py
│   └── date.py          # Date parsing utilities (python-dateutil)
└── migrations/
    ├── __init__.py
    └── 0001_initial.py

tests/
├── __init__.py
├── conftest.py          # Shared fixtures, factory helpers
├── settings.py          # Minimal Django settings for test runner
├── test_models.py       # Model field/relationship tests
├── test_converters.py   # CSL JSON round-trip + edge case tests
├── test_choices.py      # Choices completeness tests
└── data/
    ├── csl-data.json    # CSL JSON schema (reference)
    └── publication-csl.json  # Real-world test fixture
```

**Structure Decision**: Standard Django reusable app layout. Single `models.py` file (5 models is manageable). Conversion logic in dedicated `converters.py` to keep models focused on data representation. Date utilities in `utils/date.py` for parsing raw/EDTF date strings.

## Complexity Tracking

No constitution violations — no entries needed.

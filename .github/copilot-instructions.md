# django-literature Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-10

## Active Technologies
- Python 3.11+ + Django 4.2+, `django-partial-date` (ktowen/django_partial_date), `django-ordered-model` 3.7+, `python-dateutil`, `citeproc-py` (001-csl-json-data-model)
- [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION] (002-django-admin-interface)
- [if applicable, e.g., PostgreSQL, CoreData, files or N/A] (002-django-admin-interface)
- Python 3.11+ + Django 4.2+ + Django (admin framework), `django-partial-date` (PartialDateField widget), `django-ordered-model` (installed but not used for admin ordering) (002-django-admin-interface)
- SQLite (development/test), PostgreSQL (reference) (002-django-admin-interface)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 002-django-admin-interface: Added Python 3.11+ + Django 4.2+ + Django (admin framework), `django-partial-date` (PartialDateField widget), `django-ordered-model` (installed but not used for admin ordering)
- 002-django-admin-interface: Added [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]
- 001-csl-json-data-model: Added Python 3.11+ + Django 4.2+, `django-partial-date` (ktowen/django_partial_date), `django-ordered-model` 3.7+, `python-dateutil`, `citeproc-py`

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

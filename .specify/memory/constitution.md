<!--
Sync Impact Report
- Version change: 2.1.0 → 2.1.1
- Modified principles:
  - Updated: VII (Internationalization) — replaced locale-activation integration test
    requirement with makemessages clean-run CI gate and code-review enforcement; runtime
    i18n testing is not required since Django and upstream packages cover that behaviour
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  - ✅ constitution.md — updated (version 2.1.0 → 2.1.1, Principle VII Testing amended)
  - ✅ plan-template.md — no changes needed (Principle VII gate already references makemessages)
  - ✅ spec-template.md — no changes needed
  - ✅ tasks-template.md — no changes needed
  - ✅ checklist-template.md — no changes needed
- Follow-up TODOs:
  - TODO(DEMO_APP_PATH): Confirm demo/test app directory name once project scaffold is created
  - TODO(GITHUB_INSTRUCTIONS): Create or update .github/instructions/ files to reference these principles
  - TODO(PRINCIPLE_III_REVISIT): Re-introduce an ecosystem integration principle when third-party form/filter/table/UI packages are formally adopted
  - TODO(I18N_AUDIT): Audit existing model fields, templates, admin, and views for missing
    gettext / gettext_lazy wrapping now that i18n is a constitutional MUST
-->

# Django Literature Constitution

## Core Principles

### I. CSL-JSON as the Lingua Franca

Django Literature is built around the Citation Style Language JSON (CSL-JSON) specification as its canonical data exchange format.

- All data models MUST reflect the CSL-JSON structure as closely as reasonably practical within a Django relational database context.
- Import and export functionality MUST support CSL-JSON as the primary interchange format.
- When a field or concept exists in the CSL-JSON specification, it MUST be expressible — and preferably stored — in Django Literature's data model.
- Deviations from CSL-JSON field names or structures MUST be explicitly documented, motivated, and mapped back to their CSL-JSON equivalents.
- The CSL-JSON specification is the authoritative reference for supported item types, name variables, date variables, and all other metadata fields.
- Identifier fields (DOI, ISBN, ISSN, ORCID, URL) MUST be validated at the model and form layer; invalid identifiers MUST NOT be silently stored.

**Rationale**: CSL-JSON is a widely adopted, tool-agnostic open standard. Centering this package on it ensures interoperability with Zotero, Mendeley, Pandoc, and the tooling that data-centric researchers already rely on. It is especially well-suited for web applications and data transfer workflows.

### II. Embeddable Django Package

Django Literature is a reusable Django application, not a standalone research portal. Its primary users are Django developers who need literature management capabilities in their own projects.

- The package MUST be installable via pip/Poetry and enabled solely by adding it to `INSTALLED_APPS`.
- All models, views, URLs, template tags, and utilities MUST be importable from the `literature` namespace and MUST NOT conflict with common Django project structures or other third-party apps.
- The package MUST NOT impose mandatory structural changes on the host application.
- URL patterns MUST be optional and namespaced; host applications MUST be able to selectively include only the patterns they need.
- Integration with host models MUST rely on standard Django `ForeignKey` / `ManyToManyField` patterns so any host model can link to bibliographic entries.
- Default settings MUST work out of the box; all package-level configuration MUST be overridable via the host project's `settings.py` under a namespaced key (e.g., `LITERATURE`).

**Rationale**: Research applications built on Django come in many shapes. A literature management package that makes assumptions about the host project's structure will see limited adoption. Minimal footprint and clean integration are non-negotiable.

### III. Data Integrity & Long-Term Persistence

Bibliographic data is valuable and often hard to recreate. Long-term reliability and correctness of stored data MUST be design priorities.

- All migrations MUST be included in the package and kept up-to-date; host applications MUST NOT need to write custom migrations for core models.
- Migrations MUST be backwards-compatible wherever possible; destructive schema changes MUST be accompanied by data migration strategies and documented upgrade paths.
- Dates MUST accommodate the partial-date nature of CSL-JSON date structures (year-only, year-month, full date, and date ranges); partial-date-backed model fields are the canonical representation.
- Structured, queryable data (person names, dates, identifiers) MUST be stored in proper relational structures; raw JSON blobs MUST NOT be used for data that has known, stable field definitions.
- Tagging, contributor roles, and file attachments MUST use proper relational structures to remain queryable, filterable, and maintainable.

### IV. Test-First Quality & Sustainability (NON-NEGOTIABLE)

Django Literature is intended for integration into long-lived research infrastructure. All behavior changes MUST be driven by tests written first, and code, documentation, and community processes must reflect that responsibility.

**Test-First Discipline**:

- Tests MUST be written and observed failing before implementation work begins (Red → Green → Refactor).
- All new or changed Python behavior MUST have pytest coverage.
- Django integration behavior MUST have pytest-django coverage with appropriate test database strategies.
- Pull requests MUST NOT be merged with failing tests or without new/updated tests for behavior changes.
- The only acceptable exception is a docs-only change with no runtime behavior impact.

**Code Quality & Tooling**:

- Type hints, static analysis, and style rules (Ruff, mypy) are REQUIRED for core package code except where explicitly exempted in `pyproject.toml`.
- Test organization MUST mirror the `literature/` source tree with `test_` prefixes (e.g., `literature/models.py` → `tests/test_models.py`).
- Fixture factories MUST use pytest fixtures and/or factory-boy for reusable test data.
- Tests MUST use transaction rollback for isolation; the test database MUST be created once per session.
- Coverage tools SHOULD be used to identify untested code paths; high coverage percentages alone do NOT guarantee quality. Tests MUST be meaningful, maintainable, and reliable.

**Documentation & Community**:

- Documentation MUST be updated alongside new features or breaking changes so that adopters can remain productive.
- Accessibility readiness SHOULD be treated as non-optional; regressions MUST be treated as bugs.
- Internationalization (i18n) MUST be maintained as defined in Principle VII; any regression in translatability MUST be treated as a bug.
- Community contributions MUST respect this constitution; maintainers MUST provide clear rationale for accepting or rejecting proposals with explicit reference to these principles.

### V. Documentation Critical

Documentation is part of the package surface area and MUST be treated with the same rigour as code.

- Every public model field, setting key, template tag, and public API MUST be documented with at least one minimal usage example.
- Any change to public behavior MUST include a documentation update in the same pull request.
- Examples in documentation MUST be kept working and reflect the current recommended usage.
- Documentation MUST describe expected behavior in testable terms (inputs, outputs, and constraints).
- Breaking changes MUST include migration guides providing concrete, step-by-step upgrade instructions.
- Documentation MUST be versioned alongside code releases so users can reference docs appropriate to their deployed version.

### VI. Living Demo & Reference App

Django Literature maintains a reference/example Django project (the "demo app" or test application) that serves as executable documentation, a regression guard, and a model for adopters.

- The demo app MUST remain functional and up-to-date with the current package version at all times.
- When core models, APIs, or recommended integration patterns change, the demo app MUST be updated in the same pull request.
- Demo app code SHOULD include docstrings that explain purpose, usage, and rationale for each component, and SHOULD link to relevant documentation sections where applicable.
- The demo app SHOULD demonstrate:
  - Installation and configuration of `django-literature` in a new project
  - All supported CSL-JSON item types and their metadata fields
  - Import and export of CSL-JSON data
  - Citation rendering via template tags
  - Basic CRUD and admin integration for core entities
- CI/CD pipelines MUST verify that the demo app migrates cleanly, basic pages render, and there are no import errors as part of the standard test suite.

**Rationale**: The demo app simultaneously serves as a smoke test that package changes work in a realistic context, a learning resource for new adopters, and a forcing function to ensure that patterns recommended in documentation are actually usable.

### VII. Internationalization (i18n) Compatibility (NON-NEGOTIABLE)

Django Literature MUST be fully translatable and localizable so that host applications serving any language or locale can adopt it without patching the package.

**Translation Coverage**:

- All user-facing strings in Python code (models, forms, views, admin, template tags, validators)
  MUST be wrapped with `gettext_lazy()` (imported as `_`) for lazy evaluation at import time.
- All user-facing strings rendered in template tag output or passed to template context MUST
  use `gettext` or `gettext_lazy` as appropriate to the call site.
- All Django templates MUST load `{% load i18n %}` and wrap every user-facing string with
  `{% trans "..." %}` or `{% blocktrans %}...{% endblocktrans %}`.
- Any JavaScript code that produces user-facing strings MUST use Django's `JsI18n` view or
  an equivalent mechanism (e.g., a compiled JSON catalog served via `django.views.i18n.JavaScriptCatalog`)
  so that strings can be translated at runtime without rebuilding assets.
- The package MUST ship a base English (`en`) `.po`/`.mo` catalog and MUST include a
  `locale/` directory in the package source so host projects can compile or extend translations.
- `makemessages` MUST collect strings without errors from all Python, template, and JavaScript
  source files in the package.

**Non-Negotiable Rules**:

- Hard-coded user-visible strings (error messages, labels, help texts, verbose names, action
  names) MUST NOT be introduced after ratification of this principle.
- Model `verbose_name` and `verbose_name_plural` MUST use `gettext_lazy`.
- Form field `label`, `help_text`, and `error_messages` entries MUST use `gettext_lazy`.
- Any string introduced in a PR that is displayed to end users without a translation wrapper
  MUST be flagged as a blocking review comment and MUST NOT be merged.

**Testing**:

- CI MUST run `django-admin makemessages --all` against the package source and verify it exits cleanly with no untranslatable syntax errors. This is the primary i18n quality gate.
- Correct `gettext`/`gettext_lazy` wrapper usage is enforced via code review. Runtime locale-activation tests are NOT required — Django and upstream packages cover translation machinery behaviour.

**Rationale**: Django Literature is intended for use in academic, research, and institutional
content management systems worldwide. Many of those systems operate in languages other than
English. If the package ships with hard-coded English strings, every adopter in a non-English
context must maintain a fork or monkey-patch the package. Full i18n compliance from the start
eliminates that burden and makes the package a first-class citizen of the Django ecosystem,
which has strong i18n support built in.

## Architecture & Stack Constraints

This section defines the non-negotiable architectural boundaries and technology choices that keep Django Literature coherent and maintainable.

- **Language & Runtime**: The package MUST be implemented in Python and target currently supported CPython versions as declared in `pyproject.toml`.
- **Web Framework**: Django is the required web framework. The package MUST support all currently supported Django LTS versions as declared in `pyproject.toml`.
- **Data Storage**:
  - Core models MUST use Django's ORM against a SQL database; PostgreSQL is the reference implementation, but SQLite MUST be supported for development and testing.
  - All core migrations MUST be included in the package codebase.
- **Bibliographic Standard**: CSL-JSON is the canonical data exchange format; all import/export MUST support it natively.
- **Citation Rendering**: `citeproc-py` or a governance-approved equivalent SHOULD be used for server-side citation formatting; bundled CSL style files MUST be attributable to the CSL project and licensed accordingly.
- **Frontend UI**:
  - Django's built-in template engine with server-rendered HTML is the default UI layer.
  - No specific third-party form, table, filter, or client-side enhancement packages are prescribed at this stage; they MAY be introduced and codified in a future constitutional amendment as the project matures.
- **Configuration**:
  - All package-level settings MUST be accessible and overridable under a namespaced `LITERATURE` key in the host project's `settings.py`.
  - Sensitive configuration (e.g., API keys for remote import services) MUST be read from environment variables, not hard-coded.
- **Testing & Tooling**:
  - pytest and pytest-django are the canonical testing stack.
  - Tests MUST use transaction rollback for isolation; the test database MUST be created once per session.
  - Static analysis: Ruff (linting + formatting), mypy, djlint (HTML templates) as configured in `pyproject.toml`.
  - Coverage measurement via coverage.py is a guide to find gaps, not a gate to merge.
- **Core MUST include**:
  - The canonical data model: `LiteratureItem`, `Person` (contributor), `CSLDate`, and related entities mapping to CSL-JSON.
  - Import and export in CSL-JSON format.
  - Citation rendering via template tags (using bundled or user-supplied CSL styles).
  - Basic CRUD views, forms, and admin integration for all core entities.
  - Basic list, filter, and search views for literature items.
- **Extensions MAY provide** (examples, non-exhaustive):
  - Support for additional import formats (BibTeX, RIS, PubMed XML, etc.).
  - Deep integration with external citation databases (CrossRef, PubMed, Semantic Scholar).
  - Advanced citation analytics or network graphs.
  - Specialized item-type workflows beyond the generic CSL-JSON item editor.

## Development Workflow & Quality Gates

This section governs how new capabilities are proposed, designed, and implemented within Django Literature, including how Speckit-based specification files are used.

- **Specification First**:
  - Non-trivial changes MUST start with a feature specification (`spec.md`) that articulates user stories, priorities, and measurable success criteria in developer and end-user terms.
  - User stories MUST be independently testable slices of value and ordered by priority (P1, P2, P3, …).
- **Planning & Constitution Check**:
  - Each feature MUST include an implementation plan (`plan.md`) recording technical context, chosen architecture, and project structure.
  - The "Constitution Check" section in `plan.md` MUST explicitly note how the design aligns with the Core Principles; intentional violations MUST be recorded in the "Complexity Tracking" table with justification.
- **Task Breakdown**:
  - Tasks (`tasks.md`) MUST be grouped by user story and structured so that each story can be implemented and tested independently where feasible.
  - Shared foundational work (infrastructure, core models) MUST be captured as explicit blocking tasks before story-specific implementation.
- **Test-First Discipline**:
  - Tests MUST be written and observed failing before implementation work begins (Red → Green → Refactor) as defined in Principle IV.
  - No change MAY be merged that causes the agreed test suite for the touched areas to fail.
  - Pull requests without appropriate test coverage for behavior changes MUST NOT be merged (except docs-only changes).
- **Implementation Validation & Quality Checkpoints**:
  - **Django System Checks**: `poetry run python manage.py check` MUST be run and pass between completing user stories or major implementation phases to catch configuration errors before they surface as runtime failures.
  - **Demo App Testing**: When changes affect core models, admin classes, template tags, or recommended integration patterns, the demo app MUST be tested after the changes:
    - Create or update tests in the demo app's `tests/` directory to verify new/changed features work correctly.
    - Run demo app tests and ensure all tests pass before considering the feature complete.
    - Admin views SHOULD be tested by making HTTP requests to list, add, and change views to ensure they load without errors.
  - **Documentation Currency**: Documentation MUST be updated as features are implemented, not deferred to the end:
    - When implementing a user story that changes behavior visible to package consumers, update the relevant documentation section in the same pull request.
    - New public APIs, settings, template tags, and template blocks MUST be documented with usage examples before the feature is considered complete.
    - Breaking changes MUST include migration guidance documenting the upgrade path from the previous version.
  - **Validation Frequency**: For multi-phase implementations, run system checks and demo app tests after completing each phase or user story, not just at the end.
- **Documentation Critical**:
  - Developer and contributor documentation MUST be updated when behavior, configuration, or integration patterns change in user-visible ways, as defined in Principle V.
  - Speckit templates (`plan-template`, `spec-template`, `tasks-template`, `checklist-template`, and command templates) MUST remain consistent with this constitution; any divergence MUST be corrected as part of the change.

## Governance

The constitution defines how Django Literature is evolved and how compliance is enforced.

- **Governance & Scope**:
  - This constitution supersedes ad-hoc practices when they conflict.
  - It applies to the core `django-literature` package and any official demo or reference projects maintained in this repository.
  - Final authority for constitutional changes and major core decisions currently rests with the original author as BDFL (Benevolent Dictator For Life), while explicitly leaving room for a future, broader governance model.
- **Amendments & Versioning**:
  - Amendments MUST be made via pull request that clearly states the intended change, rationale, and expected impact on existing adopters and contributors.
  - Constitution versions MUST follow semantic versioning:
    - **MAJOR**: Backward-incompatible governance or principle changes, or removal/redefinition of existing principles.
    - **MINOR**: Addition of new principles or sections, or substantial expansion of existing guidance.
    - **PATCH**: Clarifications, non-semantic wording changes, and typo fixes.
  - Any change to this document MUST update the version, Last Amended date, and Sync Impact Report at the top of the file.
  - The `django-literature` package itself SHOULD follow semantic versioning; breaking changes MUST be clearly versioned, documented, and accompanied by migration guidance.
- **Compliance & Review**:
  - Code review for core changes MUST consider alignment with the Core Principles, Architecture & Stack Constraints, and Workflow rules defined here.
  - When violations are accepted (e.g., for pragmatic reasons), they MUST be documented in the relevant `plan.md` "Complexity Tracking" section and, where long-lived, reflected in a future constitutional amendment.
  - Runtime guidance for contributors and AI agents (e.g., `.github/instructions/`) MUST be kept consistent with this constitution.
- **Transparency & Community Input**:
  - Proposed constitutional changes SHOULD be discussed openly (e.g., via issues or discussions) before being merged.
  - Maintainers SHOULD provide clear, written rationale when accepting or rejecting significant changes with explicit reference to this document.
  - As additional maintainers join the project, a more formal governance structure (e.g., a small core team with an RFC process) SHOULD be established and documented as an amendment to this section.

**Version**: 2.1.1 | **Ratified**: 2026-04-08 | **Last Amended**: 2026-04-09

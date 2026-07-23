<!--
Sync Impact Report
- Version change: 2.1.1 → 3.0.0 (MAJOR: restructured onto the shared engineering-standards
  article framework; core principles now the shared defaults, repo-specific principles kept as
  project articles VIII–XII).
- Core articles I–VIII are the shared defaults (Test-First incl. Red→Green→Refactor, Simplicity,
  Anti-Abstraction, Integration-First, Security & data-safety, Documentation, Dependency
  discipline, Internationalization). The former Principle IV (Test-First) and V (Documentation)
  fold into Articles I and VI; the former Principle VII (i18n) is now the shared default Article
  VIII.
- Project articles (retained, renumbered): IX CSL JSON Lingua Franca (was I), X Embeddable
  Django Package (was II), XI Data Integrity & Persistence (was III), XII Living Demo & Reference
  App (was VI).
- Model-name reconciliation: the pre-implementation names LiteratureItem / Person / CSLDate are
  replaced throughout by the implemented, CSL-faithful names Item / Name / ItemDate.
- Removed: the standalone Speckit-template-consistency clause (tooling-specific, no longer the
  workflow engine).
-->

# django-literature Constitution

<!-- Authored at onboarding. Rarely changed; amendments are human-gated and never made
     mid-feature. Read at the Constitution Check during planning and by reviewers. -->

## Core articles

<!-- Shared engineering-standards defaults. Kept in full unless explicitly struck. -->

### Article I — Test-First
Every behavior change follows the traffic-light cycle: **Red** — write a test and watch it fail;
**Green** — write the least code that makes it pass; **Refactor** — clean up with the tests staying
green. No implementation before a failing test exists for the behavior. All new or changed Python
behavior has pytest coverage; Django integration behavior has pytest-django coverage. Pre-existing
tests are never modified or deleted without a recorded, approved decision. Docs-only changes with
no runtime impact are the only exception.

### Article II — Simplicity
Start with the simplest design that satisfies the spec. Each new dependency, abstraction, or piece
of infrastructure needs a stated justification. YAGNI over speculation.

### Article III — Anti-Abstraction
No wrapper layers, base classes, or future-proofing indirection without a present, concrete second
use. Prefer duplication over the wrong abstraction. Structured, queryable data (names, dates,
identifiers) lives in relational structures, never raw JSON blobs, when the fields are known and
stable.

### Article IV — Integration-First
Contracts and integration points are designed and tested before internals are polished. For this
package the load-bearing contract is CSL JSON import/export: round-trip fidelity is exercised the
way adopters touch it, not just at the unit level.

### Article V — Security & data-safety
Values rendered into output are escaped through Django's template layer, never hand-built string
interpolation of model or user data. Secrets (e.g. API keys for remote import services) live in
runtime config read from the environment, never in code, fixtures, or version control. External
input is untrusted. Bibliographic data is valuable and hard to recreate: migrations are included
in the package and kept current, and destructive schema changes carry a data-migration path.

### Article VI — Documentation
Public API changes ship their docs in the same PR: README + CHANGELOG updated, docstrings on public
surfaces, and the built docs stay clean. Every public model field, setting key, template tag, and
public API is documented with at least one working usage example. Breaking changes ship a migration
guide. As a package, the README follows the shared documentation standard, including a mandatory
`## Scope & philosophy` section.

### Article VII — Dependency discipline
A new runtime dependency requires a stated justification. `deptry` must pass: no unused, missing, or
transitively-relied-upon dependencies. Prefer the shared toolchain bundle over ad-hoc dev deps.

### Article VIII — Internationalization (NON-NEGOTIABLE)
The package must be fully translatable so host applications in any locale can adopt it without
patching.

- All user-facing strings in Python (models, forms, views, admin, template tags, validators) are
  wrapped with `gettext_lazy` (imported as `_`); templates load `{% load i18n %}` and wrap strings
  with `{% trans %}` / `{% blocktrans %}`.
- Model `verbose_name` / `verbose_name_plural`, and form `label` / `help_text` / `error_messages`,
  use `gettext_lazy`. Pure acronym labels (DOI, ISBN, …) are exempt.
- The package ships a base English (`en`) catalog and a `locale/` directory so host projects can
  compile or extend translations.
- A hard-coded user-visible string introduced in a PR is a blocking review comment.
- CI runs `makemessages` against the package source and verifies it exits cleanly — the primary
  i18n gate. Correct wrapper usage is otherwise enforced by review; runtime locale-activation tests
  are not required (Django and upstream packages cover that machinery).

## Project articles (django-literature-specific)

### Article IX — CSL JSON as the Lingua Franca
CSL JSON 1.0.2 is the canonical data-exchange format and the authoritative reference for supported
item types, name variables, date variables, and metadata fields.

- Data models reflect the CSL JSON structure as closely as is practical within a Django relational
  database. Where CSL JSON names a concept, this package mirrors that name (`Item`, `Name`,
  `ItemDate`, `ItemIdentifier`) rather than inventing its own.
- Import and export support CSL JSON as the primary interchange format, with round-trip fidelity.
- Any deviation from CSL JSON field names or structure is explicitly documented, motivated, and
  mapped back to its CSL JSON equivalent.
- Identifier fields (DOI, ISBN, ISSN, URL, PMID, PMCID) are validated at the model/form layer for
  known types; invalid known-type identifiers are never silently stored. Unknown identifier types
  are stored without rejection by design.

### Article X — Embeddable Django Package
django-literature is a reusable Django app, not a standalone portal; its users are Django
developers embedding literature management in their own projects.

- Installable via pip/Poetry and enabled by adding `literature` (and `ordered_model`) to
  `INSTALLED_APPS`; no mandatory structural changes to the host project.
- Everything public is importable from the `literature` namespace and does not collide with common
  Django project structures.
- URL patterns are optional and namespaced. Host models link to bibliographic entries through
  standard `ForeignKey` / `ManyToManyField` patterns.
- Defaults work out of the box; package configuration is overridable under a namespaced
  `LITERATURE` settings key.

### Article XI — Data Integrity & Long-Term Persistence
Bibliographic data must survive schema evolution.

- All core migrations ship in the package; host projects never write migrations for core models.
- Migrations are backwards-compatible wherever possible; destructive changes carry a documented
  upgrade path.
- Dates accommodate the partial-date nature of CSL JSON (year-only, year-month, full date, and
  ranges); partial-date-backed fields are the canonical representation.
- Contributor roles, dates, and identifiers stay in relational structures so they remain
  queryable and filterable.

### Article XII — Living Demo & Reference App
The bundled demo/reference project is executable documentation and a regression guard.

- The demo app stays functional and current with the package at all times, and is updated in the
  same PR when core models, admin, template tags, or integration patterns change.
- It demonstrates installation/configuration, the CSL JSON item types, import/export, citation
  rendering, and basic CRUD/admin for core entities.
- CI verifies the demo app migrates cleanly and its pages render without import errors.

## Architecture & stack constraints

- **Language/framework:** Python (currently-supported CPython) and Django (currently-supported
  versions), as declared in `pyproject.toml`.
- **Storage:** Django ORM against SQL; PostgreSQL is the reference, SQLite is supported for
  development and testing. Core migrations ship in the package.
- **Citation rendering:** `citeproc-py` or a governance-approved equivalent; bundled CSL style
  files are attributable to the CSL project and licensed accordingly.
- **UI:** server-rendered Django templates by default. No third-party form/table/filter/JS
  packages are prescribed yet; adopting one is a constitutional amendment.
- **Testing & tooling:** pytest and pytest-django are canonical; test modules mirror the
  `literature/` tree with `test_` prefixes. Static analysis via Ruff and mypy as configured in
  `pyproject.toml`. Coverage is a guide to find gaps, not a merge gate.

## Quality bar

Read at planning and review; applies to every change.

- Coverage may not decrease.
- Every public API change updates README + CHANGELOG in the same PR.
- Lint (Ruff), type-check (mypy), and `deptry` pass.
- **Package:** builds with valid metadata; the README renders on the package index (absolute
  URLs); the public API honors the deprecation policy.
- **CSL JSON:** round-trip fidelity holds — importing then exporting yields equivalent CSL JSON.
- **i18n:** `makemessages` runs clean over the package source (Article XI).
- **Demo app:** migrates cleanly and its core pages render without import errors (Article XII).

## Non-negotiables

- One PR per feature; Sam merges; automation never merges.
- Automation commits under a bot identity, not a human PAT. This repo's account has a bot App
  (`fairdm-bot[bot]`): the org's PRs are authored by it and the default branch requires one
  approval — Sam is the distinct approver, then merges. Identity is scoped per GitHub account and
  never shared across accounts.
- Machine verification (tests/build/lint) gates every stage exit; no judgment call overrides a red
  gate.

## Governance

This constitution supersedes ad-hoc practice when they conflict. It covers the core
`django-literature` package and any official demo or reference project in this repository.

- **Amendments** are made via a pull request stating the change, rationale, and impact on adopters,
  and are never made mid-feature.
- **Versioning** is semantic: **MAJOR** for backward-incompatible governance/principle changes or
  removals; **MINOR** for new principles/sections or substantial expansions; **PATCH** for
  clarifications and wording. Any change updates the version, the Last Amended date, and the Sync
  Impact Report above.
- **Compliance:** code review for core changes weighs alignment with these articles; accepted
  deviations are recorded in the relevant plan's complexity tracking and, if long-lived, reflected
  in a later amendment.
- Final authority currently rests with the original author, leaving room for a broader governance
  model as more maintainers join.

**Version**: 3.0.0 | **Ratified**: 2026-04-08 | **Last Amended**: 2026-07-23

<!--
Sync Impact Report
- Version change: 4.0.0 → 5.0.0 (MAJOR: an article removed). Article I now points at
  docs/contributing/standards/testing.md, which carries the test-first cycle, what gets a test,
  test structure and fixtures, and the coverage floors. Article XIV (Test structure & fixtures)
  moved into that document and is removed here; Cohesion is renumbered from XV to XIV. Article VI
  points at docs/contributing/standards/code-documentation.md. The coverage wording in the stack
  constraints and quality bar follows the standard's floors. Non-negotiables hold merge rules only;
  the rules for automated contributors are in AGENTS.md.
- References to Articles XIV and XV in specs/, tests/ and the package are updated.

- Version change: 3.2.0 → 4.0.0 (MAJOR: a governance restriction removed). The stack constraints
  had named django-mvp as the one adopted UI layer and required a constitutional amendment before
  any further front-end package could be adopted. That bar was heavier than the decision it
  governed: adding a rendering library the adopted UI layer already integrates with is ordinary
  dependency work, and routing it through an amendment made the constitution the bottleneck for
  every interface feature. Front-end additions now sit under Article VII's dependency discipline,
  keeping the two conditions that were doing the real work — the core never gains a front-end
  dependency, and django-mvp's own integration is the route in where one exists.
- Governance: the flat prohibition on amending mid-feature is replaced by a disclosure rule. The
  clause existed so a branch could not quietly widen a rule it was judged against; requiring the
  amendment to be declared in the pull request's description addresses that directly, where the
  prohibition instead forced a second pull request for a paragraph.
- No article added or removed; no renumbering. Templates and specs referencing article numbers
  are unaffected.
- Earlier report retained below.

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

### Article I — Testing
Every change follows [`docs/contributing/standards/testing.md`](docs/contributing/standards/testing.md): what gets a test
and what does not, the test-first cycle, test structure and fixtures, and the coverage floors.

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
surfaces, and the built docs stay clean. Docstrings, component annotations and code comments
follow [`docs/contributing/standards/code-documentation.md`](docs/contributing/standards/code-documentation.md). Every public model field, setting key, template tag, and
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

### Article XIII — Data-model conventions (Django)
Every model field is a deliberate indexing decision. Because consumers of a published package cannot
add their own indexes, any field with a plausible lookup / filter / ordering path is indexed at its
definition (`db_index`, `unique`, an FK's automatic index, or a composite `Meta.constraints` /
`Meta.indexes`); a field with no query path stays unindexed to avoid write cost. The choice —
indexed or not, and why — is recorded (plan `data-model.md` or `decisions.md`). `verbose_name` and
`help_text` are mandatory on every model field (Article VIII). **Migrations are consolidated per
PR:** the migrations a feature branch introduces are squashed into as few files as possible before
the PR is submitted (branch-local and unapplied, so safe at any release stage); data migrations
(`RunPython`/`RunSQL`) are exempt from auto-regeneration — keep them via `squashmigrations` or
standalone.

### Article XIV — Cohesion (Python)
Related behaviour is grouped in a class, not scattered across module-level functions.

**The test:** two or more module-level functions that share a *subject* belong on a class. They
share a subject when they operate on the same data, take the same first argument, are only
meaningful in sequence, or are named around the same noun (`build_x`, `validate_x`, `render_x`).

**Why this is a standard and not a taste.** In a published package, a class is the extension
point. A consumer who needs different behaviour subclasses it and overrides one method. A module
of functions can only be monkey-patched, which is not a supported interface and breaks on any
internal change. Grouping also gives the behaviour a name, a place for shared configuration, and
one import instead of six.

**Shape:** shared state or configuration → a regular class holding it. Grouping for namespacing
with no shared state → still a class, with `@classmethod`/`@staticmethod`, or a small frozen
dataclass carrying the config. Expose a module-level convenience function only as a thin wrapper
over the class, never as the implementation.

**Django first.** Where the framework already owns the grouping, use it rather than inventing a
class: a `QuerySet`/`Manager` method instead of a function taking a queryset, a model method or
property instead of a function taking an instance, a `Form`/`Serializer` method instead of a free
validation function, a `TemplateView` method instead of a helper called by a view.

**Exceptions — narrow, and stated rather than assumed.** A genuinely standalone pure function with
no siblings. Framework-dictated module shapes: `conftest.py` fixtures, migrations, `urls.py`,
`apps.py`, decorator-registered template tags and filters, signal receivers, management-command
entry points. Factory functions that return the class. A module of independent utilities that
genuinely share no subject.

**This does not license abstraction.** Article III still holds: one class grouping today's
behaviour is the goal, not a base class, a registry, or a hierarchy built for a second
implementation that does not exist. Grouping related functions is organisation; adding a layer
between the caller and the work is not.

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

- Installable via pip or uv and enabled by adding `literature` to
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
- **UI:** server-rendered Django templates. The opt-in `literature.ui` app is built on
  [django-mvp](https://github.com/django-mvp), the adopted UI layer — arriving through the
  optional `ui` extra rather than a core dependency, so the core stays free of it and a core-only
  install resolves no front-end package. A further front-end package may be added to the `ui`
  extra when the interface genuinely needs it, under Article VII's ordinary dependency discipline:
  a stated justification, `deptry` clean, and the core still resolving none of it. Two conditions
  hold whatever is added — the core never gains a front-end dependency, and the package is
  reached through django-mvp's own integration for it where one exists, rather than as a second
  way of doing something django-mvp already does.
- **Testing & tooling:** pytest and pytest-django are canonical; test modules mirror the
  `literature/` tree with `test_` prefixes. Static analysis via Ruff and mypy as configured in
  `pyproject.toml`. Coverage floors are set in the testing standard (Article I).

## Quality bar

Read at planning and review; applies to every change.

- Test coverage meets the floors in `docs/contributing/standards/testing.md` (`codecov.yml`).
- Every public API change updates README + CHANGELOG in the same PR.
- Lint (Ruff), type-check (mypy), and `deptry` pass.
- **Package:** builds with valid metadata; the README renders on the package index (absolute
  URLs); the public API honors the deprecation policy.
- **CSL JSON:** round-trip fidelity holds — importing then exporting yields equivalent CSL JSON.
- **i18n:** `makemessages` runs clean over the package source (Article VIII).
- **Demo app:** migrates cleanly and its core pages render without import errors (Article XII).

## Non-negotiables

- Tests, build and lint pass before a change merges. Nobody overrides a red check.
- The default branch requires one approval, and the author of a change never approves it.

## Governance

This constitution supersedes ad-hoc practice when they conflict. It covers the core
`django-literature` package and any official demo or reference project in this repository.

- **Amendments** are made via a pull request stating the change, rationale, and impact on adopters.
  An amendment carried alongside feature work is declared in that pull request's description, so a
  branch can never quietly widen a rule it is being judged against.
- **Versioning** is semantic: **MAJOR** for backward-incompatible governance/principle changes or
  removals; **MINOR** for new principles/sections or substantial expansions; **PATCH** for
  clarifications and wording. Any change updates the version, the Last Amended date, and the Sync
  Impact Report above.
- **Compliance:** code review for core changes weighs alignment with these articles; accepted
  deviations are recorded in the relevant plan's complexity tracking and, if long-lived, reflected
  in a later amendment.
- Final authority currently rests with the original author, leaving room for a broader governance
  model as more maintainers join.

**Version**: 5.0.0 | **Ratified**: 2026-04-08 | **Last Amended**: 2026-09-28

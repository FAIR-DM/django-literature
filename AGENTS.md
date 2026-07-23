# AGENTS.md — Agent Configuration for django-literature

<!-- Thin index only — bloat here = ignored instructions. Details live in the pointed-to
     files. Keep sections, replace placeholders. -->

`django-literature` is a reusable Django app that stores bibliographic references as a faithful
relational representation of the **CSL JSON 1.0.2** standard: an **Item** (top-level entry) with
related **Name**, **ItemName** (role + order), **ItemDate**, and **ItemIdentifier** records, plus
CSL JSON import/export with round-trip fidelity. See `CONTEXT.md` for the ubiquitous language.

## Stack & commands

- **Stack:** Python ≥3.11 / Django 5.2 + 6.0 (family standard — supported releases only, CI matrix
  Python 3.12–3.13), Poetry-managed. Dev toolchain via the `mvp-shared` bundle. Ships to PyPI.
- **Install:** `poetry install`
- **Test:** `poetry run pytest` (pytest-django; settings module `tests.settings`)
- **Lint/format:** `poetry run pre-commit run --all-files` (ruff lint + ruff-format; local mypy + deptry hooks)
- **Type-check:** `poetry run mypy`
- **Build:** `poetry build`

## Agent skills

### Issue tracker

Issues tracked in GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix).
See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — `CONTEXT.md` glossary at root, `docs/adr/` for standing decisions.
See `docs/agents/domain.md`.

### CI checks

CI delegates to the `django-mvp/shared` reusable workflows (`tests.yml`, `build.yml`). Required
status checks (exact names): `call-build / Code Quality`, `call-build / Security Scan`,
`call-build / Build Package`, and the test matrix `call-tests / Test Python <py>, Django <dj>`
(Python 3.12–3.13 × Django 5.2/6.0).

## Development workflow

Feature work follows a spec-driven process: spec → plan → tasks → implement → review → PR, with
`specs/NNN-slug/` directories per feature (there is no spec-kit install in the repo). Project
standards and the quality bar live in `memory/constitution.md`. One PR per feature; the default
branch is protected and requires one approval before merge.

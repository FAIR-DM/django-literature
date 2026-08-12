# ADR-0016 — The front end arrives through an optional extra

- **Status:** Accepted
- **Context date:** spec 006 (D5), `pyproject.toml`, `literature/ui/`, issue #45

## Context

The catalogue interface is opt-in. "Opt-in" has two possible readings: the host chooses whether to
add the app to `INSTALLED_APPS`, with the front-end stack installed either way; or the host chooses
whether to install the front-end stack at all.

The first reading is a convention. It holds only as long as everyone remembers it, and it is
invisible from outside the source: a project embedding the core still pays the install, still
carries the dependency in its lock file, and still inherits its vulnerability surface.

## Decision

**django-mvp is an optional dependency, declared under the `ui` extra. A core-only install resolves
no front-end package at all.** The interface lives in `literature.ui`, and nothing in the core
imports from it.

## Consequences

- The separation is a property of the dependency graph, so it can be proved mechanically rather than
  reviewed by eye — a test boots the core against settings that install neither `literature.ui` nor
  any of its dependencies, and it fails the moment something in the core reaches across.
- A host wanting the interface installs `django-literature[ui]` and follows the documented setup
  steps. Those steps are real: django-mvp needs several apps, a context processor and a `SITE_ID`,
  and the app configures none of them on the host's behalf (see the README).
- Anything the interface needs from the core is added to the core deliberately, as core API. The
  reverse direction has no route.
- Tooling that loads Django settings has to pick a side. The type checker reads the core-only
  settings module, so it does not depend on an optional extra being installed in a job that cannot
  install one.

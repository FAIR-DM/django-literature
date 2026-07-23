# Goals

These are the standing directions `django-literature` works toward. Each one is a capability or
quality to steer by, not a task that gets ticked off. Whether any goal has been served well enough
is decided in the roadmap, the feature specs, and review, never by the goal itself.

This file carries no version numbers or release plan; that lives in the roadmap. For what the
package is, what it stays out of, and the principles that settle a close call, read the
*Scope & philosophy* section of the [README](README.md).

Importance is a tag on each goal, not a ranking:

- **Essential** — not worth adopting without it.
- **Expected** — a complete, dependable version is expected to have it.
- **Aspirational** — a genuine want whose absence never makes the package incomplete.

| ID | Goal | Importance | Status | Notes |
|----|------|------------|--------|-------|
| G1 | Store bibliographic references as a normalized relational model of CSL JSON 1.0.2 | Essential | | |
| G2 | Convert between CSL JSON and the model in both directions with round-trip fidelity | Essential | | |
| G3 | Run as a headless core with no UI required | Essential | | |
| G4 | Offer a full front end as an opt-in app built on django-mvp | Expected | | |
| G5 | Import references from common bibliography formats such as BibTeX and RIS | Expected | | |
| G6 | Ship a runnable demo project that exercises the app and guards against regressions | Expected | | |
| G7 | Validate known identifier types at the model layer | Expected | | |
| G8 | Render citations and bibliographies through a downstream CSL processor | Aspirational | | |

_Written 2026-07-23. Revise as the goals change._

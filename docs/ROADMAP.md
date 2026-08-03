# Roadmap

**Date:** 2026-07-23

This document was designed against [GOALS.md](../GOALS.md). See also [CONTEXT.md](../CONTEXT.md) for domain terminology and [memory/constitution.md](../memory/constitution.md) for project standards.

## Versioning

Releases are gated on goal importance, not on a count of features.

| Version | Meaning |
|---------|---------|
| `0.0.x` | Building toward the Essential goals. Pre-viable, git-pin only, nothing published. |
| `0.1.0` | All Essential goals delivered. The minimum usable release and first publish. |
| `0.1.x` → `0.x` | Advancing the Expected goals, at whatever granularity the work takes. Patches are fixes. |
| `1.0.0` | All Expected goals delivered. The complete, dependable release. |
| `1.x` | Stable line. Non-breaking fixes and additive features only. |
| `2.0` | The next major. Breaking changes wait for it. |

Two rules hold across the line: a goal is not one minor (some take several, and one minor can move two), and once `1.0` ships a breaking change never goes out as `1.x`; it waits for the next major. Aspirational goals may be developed against v2, or earlier if capacity allows.

This roadmap reads as the full build sequence from an empty repository. The early items are already delivered and carried here so the story stays whole and their ids are citable; the package sits on the `0.1.x` line today, with the Essential bar met and the work ahead advancing the Expected goals toward `1.0.0`.

## Essential goals: v0.1.0

Everything needed to reach a minimum usable release.

### R1 — Normalized CSL JSON store

*Delivered · advances G1*

Bibliographic references persist as a normalized relational model of CSL JSON 1.0.2: a top-level item with its contributors, dates, and identifiers held in their own related structures rather than a JSON blob. This is the foundation the rest of the package builds on.

Serves G1.

### R2 — Two-way conversion with round-trip fidelity

*Delivered · advances G2*

References convert between CSL JSON and the model in both directions, and importing then exporting yields equivalent CSL JSON. This is what keeps references portable: they can leave the package as the same CSL JSON they arrived as.

Serves G2.

### R3 — Headless core

*Delivered · advances G3*

The core runs with no front end required: add it to a project, point a relation at an item, and the host owns its reference catalogue with no UI stack pulled in. The core installs no management surface of its own, so nothing is registered and no UI stack is imported.

Serves G3.

## Expected goals: v1.0.0

What a complete, dependable version is expected to carry.

### R4 — Identifier validation at the model layer

*Delivered · advances G7*

Known identifier types are format-checked where the data lives, so a malformed DOI, ISBN, ISSN, or similar is rejected rather than silently stored, while unknown types are still accepted so nothing is lost. Validation sits at the model layer so every write path inherits it.

Serves G7.

### R5 — Import from BibTeX and RIS

*multi-feature · advances G5*

The store converts CSL JSON only, yet researchers keep their references in BibTeX and RIS exports from reference managers and databases. This item adds importers for both formats, mapping their fields onto the model through the existing conversion boundary and routing anything that will not normalize to the store's documented fallbacks rather than dropping it. It comes before the front end so the interface has working import paths and real data to surface from the start.

Underneath their differing syntax both formats do the same job, and the front end will eventually need to accept an uploaded file without knowing which format it holds. So the item also settles one calling contract shared by every importer: an agreed way to run an import, and one shape for its result, with format-specific parsing underneath and out of the caller's way. Article III bars a base class without a concrete use behind it, so that contract ships together with the first importer rather than ahead of it, and the second format is what proves the seam was drawn in the right place.

**Deliverables:**

- One import contract shared by every format, covering how an import is invoked and how the outcome of each record is reported, delivered together with the first importer.
- BibTeX import that maps entries and contributor lists onto the model.
- RIS import that maps tagged records onto the model.
- Unresolved source fields preserved through the model's fallback slots rather than discarded.
- A caller can tell which records failed to import and why, instead of comparing counts.
- Tests over representative real-world files, including messy and partial records.

Serves G5. Out of scope: exporting to BibTeX or RIS, and any live sync with external registries, though the contract should not make an export counterpart harder to add later.

### R6 — Opt-in front-end app on django-mvp, with a runnable demo

*multi-feature · advances G4, G6*

The intended way to use the package in full is an opt-in front end, kept entirely separate from the headless core, and the demo project that shows it off is the same piece of work: a runnable project is how the front end is exercised and guarded against regressions. This item builds the app on django-mvp, a complete and consistent interface for browsing and managing references that a host installs when it wants one, together with a demo that serves it over real data and runs in CI. The core stays free of any front-end dependency throughout, and this item assumes a headless core that bundles no management of its own. It is the largest item and comes last because it sits on the import paths that give it real data to show (R5). It will span several releases.

**Deliverables:**

- An installable front-end app that a host opts into, with the core still installable on its own and carrying no front-end dependency.
- Browse, create, edit, and delete flows for references and their contributors, dates, and identifiers.
- A self-contained design system that does not depend on the host project's styling.
- A demo project that starts with a documented command and serves the front end over seed references spanning a range of item types, names, dates, and identifiers.
- A smoke path over the demo, run in CI on every change, so regressions are caught before release.

Serves G4 and G6. Out of scope: blending into a host project's theme, and citation rendering (R7).

## Aspirational goals: v2.0

Genuine wants whose absence never makes the package incomplete; developed against v2, or earlier if capacity allows.

### R7 — Citation and bibliography rendering

*feature · advances G8*

Render items and reference lists as formatted citations and bibliographies through a downstream CSL processor, kept out of the core store so formatting never becomes a storage concern. Fuller deliverables are written when this item reaches the front of the queue on a re-run.

Serves G8. Out of scope: baking formatting into the store.

# ADR-0030 — The import page accepts an unbounded upload from anyone who can reach it

- **Status:** Accepted
- **Context date:** spec 011 (FR-007, and the assumptions behind FR-041), issue #50

## Context

This feature opens the package's first file-upload boundary. Two properties of it were approved
separately and are worth naming together, because their combination is what a reader needs to see:

- Nothing in the front end checks permissions (ADR-0022), so the import page is reachable by whoever
  can reach the catalogue.
- The package imposes no size limit of its own on the submitted file, and the format is chosen rather
  than detected (ADR-0029), which rules out an extension or content-type allowlist by requirement
  rather than by choice.

## Decision

Both stand. The documentation states them plainly rather than leaving a reader to infer them from
the absence of a check.

## Consequences

- The endpoint grants no privilege the already-open create page does not. What it adds is throughput:
  one anonymous request parses a caller-sized file in the worker and can create thousands of
  references and their related rows, where the create page creates one. That is a difference in kind
  of exposure, not only of degree.
- What bounds it is the host project's own upload size, request timeout and access rules. A reusable
  application cannot bound them on its host's behalf without imposing the structural assumptions this
  package refuses to make, so the bound belongs where the deployment is.
- A project that needs the page restricted restricts it at its own routing, the same way it would
  guard any other view, and a project that needs a size limit sets one in its own configuration.
- Previewing by default (ADR-0028) does not change this. A preview reads the whole file and stages
  it, so it costs the same work as the import it describes.

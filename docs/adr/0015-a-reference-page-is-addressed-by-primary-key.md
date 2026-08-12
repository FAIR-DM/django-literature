# ADR-0015 — A reference page is addressed by its primary key

- **Status:** Accepted
- **Context date:** spec 006 (D2), `literature/ui/urls.py`, issue #45

## Context

The citation key is the handle a reader already uses for a reference, and the obvious candidate for a
readable URL: `/catalogue/rowe2021joint/` reads better than `/catalogue/417/`, and any later surface
that addresses a reference faces the same choice.

A citation key is indexed, but it is not globally unique. Uniqueness is resolved per import batch
(ADR-0001), so two items imported in different batches can hold the same key.

## Decision

**A page for one reference is addressed by the item's primary key. A citation key never addresses a
page.** The key is displayed on the catalogue entry and on the reference page, where it is the handle
that distinguishes two similar entries from each other.

The same rule holds for a contributor: the page is addressed by the contributor record's primary
key, because a stored name is not unique either and carries no other stable handle.

## Consequences

- A URL carries no meaning a reader can read, and none that survives being quoted in a paper.
- Addressing by key would have to resolve a collision somehow, either by picking an arbitrary one of
  several matching items or by 404-ing on a key that exists twice. Both are worse than an opaque
  number.
- Readable URLs remain available as a feature of their own. They require the key to become globally
  unique, which is a change to the store's key semantics and a decision about what happens to the
  keys already assigned — not something a browse interface can settle on its own.

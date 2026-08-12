# ADR-0019 — The repository holds data as source, never as a built database

- **Status:** Accepted
- **Context date:** spec 007 (D4), `demo/seed/catalogue.json`, issue #46

## Context

The demo has to start over a populated catalogue. A repository can arrange that two ways: commit a
pre-built database so starting is instant, or commit the data as source and build the database on
start.

The first is tempting for a demo in particular, because the whole promise is one command and no
setup, and shipping a ready database removes a few seconds from it.

## Decision

**Data lives in the repository as source. A database is built, never committed.** The seed
catalogue is CSL JSON that the package's own converter reads, and the start command creates the
database, applies migrations and loads the catalogue every time.

## Consequences

A change to the seeded data is reviewable. Someone can see that a reference was added, read the
fields it carries and disagree with them, which is not possible with a binary.

The catalogue cannot disagree with itself. There is one artifact, so no question arises about
which of two the guard should trust.

Migrations cannot drift out from under the data. A committed database goes stale the moment a
migration lands and nobody rebuilds it, and the failure surfaces as a demo that works for everyone
holding the old file and breaks on a fresh clone — the worst shape a failure can take, because the
people who can reproduce it are the ones least able to explain it.

Running the command twice, from any starting state, reaches the same catalogue, and nobody has to
do anything to keep that true. With a committed database it would be a property someone had to
maintain.

The cost is a few seconds at start, and a demo that depends on the import path working. That
dependency is deliberate — an importer regression now breaks the demo, and for a check that exists
to catch regressions, being downstream of more of the package is the useful direction.

## Alternatives considered

**Commit `demo/db.sqlite3`.** Instant start, and everything above goes wrong quietly.

**Commit a Django fixture instead of CSL JSON.** Reviewable, and it loads without the converter.
It also encodes the storage layout rather than the source format, so it drifts with every model
change, and it exercises none of the package on the way in.

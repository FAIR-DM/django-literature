# ADR 0023 — A citation key's uniqueness is the reader's concern, not the package's

**Status:** accepted

Supersedes [ADR 0001](0001-citation-key-unique-per-import-batch.md).

## Decision

A citation key is stored exactly as it is given. Nothing warns about a collision, nothing refuses
one, and nothing rewrites a key to make it distinct. Two references may carry the same key.

This holds everywhere a key is written: the interface's create and edit forms, and the import path,
which was brought into line afterwards.

## Why

A citation key is a handle for writing bibliographies: it exists so a person can refer to the right
reference in their own manuscript. Keeping keys distinct is therefore the person's business, the
same way it is in every other reference manager. Two references sharing a key is a situation people
create deliberately and resolve themselves.

Enforcement is also wrong at the boundary it would have to sit on. A store-wide check assumes one
bibliography per installation, and the shapes this package is heading toward break that assumption
in two directions: separate bibliographies per user, and collections of references grouped by the
article being written. A key that must be unique across all of them is a key nobody can choose
freely.

The failure mode of the superseded rule is concrete. Importing a file whose key already exists
stored `smith2020` as `smith2020-2`, so the key the person writes in their manuscript quietly
stopped being the key on the record. That is the exact outcome the rule was meant to prevent.

## Revisit if

The package gains a feature that genuinely requires addressing a reference by its citation key
rather than by its identity. Nothing does today: a reference's own page is addressed by primary key
for this reason, which [ADR 0015](0015-a-reference-page-is-addressed-by-primary-key.md) records.

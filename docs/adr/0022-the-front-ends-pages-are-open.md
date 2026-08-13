# ADR 0022 — The front end's pages are open, including the ones that write

**Status:** accepted

## Decision

Every page the front-end app serves is reachable without signing in, and the app imposes no
permission check of its own. That now includes the pages that create, change and delete references.
A host that wants the catalogue restricted wires the URL include behind its own protection, exactly
as it would for any embedded app.

The bundled demo ships this way, and its regression check asserts that no page redirects to a login.

## Why

The package is built for a researcher managing their own library. In that setting a permission model
is a cost with no reader: an account to create, a login to pass, a role to configure, before anyone
can look at their own bibliography.

The earlier read-only pages settled this for browsing. Extending it to writing is a larger claim and
is recorded here rather than inherited quietly, because the consequence is different in kind: open
read pages let a visitor see the catalogue, open write pages let one empty it.

Restriction belongs to the host either way. A reusable app that imposes its own permission model
forces that model on every project embedding it, and a project's own rules are the ones that should
decide who may write.

## Revisit if

The package is used by more than one person against the same store, or a deployment exposes it
beyond a trusted network. Either makes the reasoning above false rather than merely inconvenient,
and access control becomes a piece of work in its own right, one that currently has no issue and
no roadmap item behind it.

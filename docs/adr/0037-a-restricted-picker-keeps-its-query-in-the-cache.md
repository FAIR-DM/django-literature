# ADR 0037 — A restricted picker keeps its query in the cache

**Status:** accepted

## Decision

A reference picker whose queryset is filtered tells the shared search route which references to
search by a key, and the query behind the key lives in Django's default cache.

- `SearchRestriction.key_for(queryset)` stores the queryset's query under a digest of the
  restriction itself and puts that digest, signed, on the select.
- `SearchRestriction.queryset_for(key)` checks the signature, reads the query back from the cache
  and returns the queryset the search runs against.
- The request carries only the signed digest. Nothing from a request is ever unpickled.
- A key that fails its signature, or whose entry is no longer in the cache, makes the search
  answer 404 with no results. It never falls back to the whole catalogue.
- An unrestricted picker carries no key and needs no cache.

This is the first place the package depends on a project's cache. A project that uses restricted
pickers in production needs a cache shared between its processes.

## Why

Every picker in a project shares one search route, so the route has to learn each picker's
restriction from the request. A queryset cannot travel in a query string, and asking the developer
to mount one route per restriction would turn a one-line field declaration into wiring of their
own. django-select2 meets the same need the same way, by keeping the widget's queryset in the cache
under a signed key, and that is the established mechanism.

The digest is derived from the restriction rather than generated at random, so one restriction has
one cache entry however many pages draw it, and each render keeps that entry alive. A key the route
cannot resolve answers with nothing because offering too much would break the restriction, while
offering nothing only stops the search. Submitting a form is validated against the field's own
queryset whatever the search returned, so the restriction holds on save in every case.

## Revisit if

The project's cache proves unreliable in a common deployment, for example per-process memory caches
behind several workers, often enough that restricted pickers routinely offer nothing. Then the
restriction would be named on the route instead, at the cost of declaring it in the project.

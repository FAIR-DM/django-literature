# ADR 0024 — The catalogue search adds no index

**Status:** accepted

## Decision

The catalogue's search and filters ship with no database index of their own, and no migration. A
future change must not add `db_index=True` to the searched text fields on the assumption that it was
an oversight.

## Why

The search matches a fragment appearing anywhere inside a value, because a reader types part of a
surname or part of a title rather than its opening characters. An ordinary index orders a column's
values, so it can serve a query anchored at the start of a value and cannot serve one looking
inside it. Indexing the title fields would therefore add a migration and add write cost to every
import, and change no query plan. The failure would be invisible: nothing breaks, the search stays
exactly as slow, and the package carries something that looks like diligence.

What would genuinely serve a fragment search is specific to the database and expensive in a way that
has nothing to do with query time. On PostgreSQL it is a trigram index, which means requiring an
extension to be installed. On SQLite, which the test suite and the demo run on, there is no
equivalent at all. A package that needs a database extension to stay usable at scale is a different
package from one that does not, and becoming that one is a decision in its own right rather than a
detail of a search feature.

The filters reach the same answer by another route. They narrow through the foreign keys linking
contributors and dates to a reference, which Django already indexes, and through item type and
language, whose handful of distinct values give a query planner little reason to use an index even
where one exists.

## The cost this accepts

A search term is split on whitespace, and every word is matched against each of the eight field
paths, three of which reach contributors through a join. A ten-word query therefore issues eighty
fragment comparisons across joined tables and then removes duplicates. The result page stays bounded
because it is paginated, but the scan does not, and nothing caps what a reader can type. This is the
accepted consequence, recorded so that the first report of a slow catalogue is not diagnosed from
scratch.

## Revisit if

A catalogue outgrows this. The answer then is a dedicated text-search facility, arriving as its own
piece of work with its own decision about what the package requires of its host — not an index added
to these fields.

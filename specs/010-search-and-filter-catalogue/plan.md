# Implementation Plan: Find a Reference in a Large Catalogue

**Branch**: `010-search-and-filter-catalogue` · **Spec**: [`spec.md`](spec.md) · **Research**: [`research.md`](research.md) · **Decisions**: [`decisions.md`](decisions.md)

**Issue**: #49 (epic) · Stories #91–#95 · Pull request #96

## Summary

Both catalogue presentations gain a search box and four filters by adopting django-mvp's existing
search mixin and its django-filter integration, rather than by writing search or filtering of our
own. The card list becomes a `MVPFilteredListView`; the table composes `MVPTableViewMixin` with
`FilterView`, which is the upstream-documented way to reach a filtered view that is not the
ready-made class. One `FilterSet` and one list of searchable field paths serve both, so the two
presentations cannot drift.

`django-filter` joins the `ui` extra, the django-mvp floor rises to the release whose pagination
links preserve the address, and the two tests pinning the old address move with it. No model
changes, no migration, no index.

## Technical Context

**Language/Version**: Python ≥3.11 for the core, ≥3.12 wherever the front end is installed.

**Primary Dependencies**: django-mvp `>=0.19.1,<1.0` (raised from `>=0.19`, research R6),
django-tables2 `>=3.0,<4`, and django-filter — new, `ui` extra only (research R2). The core's three
runtime dependencies are untouched.

**Storage**: unchanged. No model change, no field, no migration, and deliberately no index
(`decisions.md` D1).

**Testing**: pytest + pytest-django, `tests.settings`. New module `tests/test_ui/test_filters.py`
mirrors `literature/ui/filters.py` per Article XIV; view behaviour extends
`tests/test_ui/test_views.py`; packaging assertions move in `tests/test_ui/test_packaging.py`.

**Target Platform**: server-rendered Django, SQLite and PostgreSQL both supported.

**Performance Goals**: a page of results costs a constant number of queries regardless of how many
results are on it (FR-026) — the existing guarantee, preserved through the filtered queryset.

**Constraints**: the core stays free of any front-end import; the contributor page, which subclasses
the card list, must not inherit the new controls (research R11); nothing forks upstream markup.

**Scale/Scope**: one new module (`filters.py`), two view classes changed, one dependency added, one
floor raised, two pinned assertions moved, seed data extended, one README section rewritten and one
paragraph deleted. Roughly twenty new tests.

## Constitution Check

Checked against `memory/constitution.md` v4.0.0.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every task writes its test before its code | Applies, no tension |
| II Simplicity / III Anti-Abstraction | Search and filtering are adopted from upstream, not implemented. One `FilterSet`, one field list, no base class invented to share them | Pass |
| V Security | The search term reaches the ORM through `icontains` on declared field paths only, never string-formatted SQL. Filter values are validated by the filterset's own form, which is what makes FR-017's invalid-value behaviour a form-level outcome rather than a crash | Applies, tasked |
| VI Documentation | README's front-end section gains what search and filters do, and loses the paragraph describing the pagination limitation this feature removes; CHANGELOG in the same change | Applies, tasked |
| VII Dependency discipline | One new runtime dependency in an optional extra, justified in research R2, reached through django-mvp's own integration for it; `deptry` stays clean | Applies, tasked |
| VIII i18n (non-negotiable) | Every filter label, the search placeholder we override, and the no-results message are translatable | Applies, tasked |
| IX CSL JSON | No conversion path touched | N/A |
| X Embeddable package | `django_filters` must reach the host's `INSTALLED_APPS`; documented in the installation block, as django-tables2 was | Applies, tasked |
| XI Data integrity | No model change, no migration | Pass by construction |
| XII Living demo | Seed data gains language values, and the guard walks a search, a filter and a page move (research R8) | Applies, US-5 |
| XIII Data-model conventions | No field added. Indexing was considered and deliberately rejected — `decisions.md` D1 records why, so the absence is a decision on the record rather than an omission | Pass |
| XIV Test structure | `literature/ui/filters.py` → `tests/test_ui/test_filters.py` | Applies, tasked |
| Stack constraints | django-filter is admitted under Article VII and reached through django-mvp's own integration, which is the condition the constraint states | Pass |

No entry in Complexity Tracking.

## Design decisions

### D-1 — One `FilterSet` and one field list, in a new `literature/ui/filters.py`

FR-023 requires what is searchable and filterable to be defined once. The module holds
`SEARCH_FIELDS` (the ORM paths of FR-002) and `ItemFilterSet` (the four filters), and both views
import them. Not a mixin and not a base view: the two presentations already differ in their base
class, and a shared *value* is a weaker coupling than a shared ancestor while giving the same
guarantee. The test that both views return the same references for the same query (US-4) is what
proves it, and it would still pass if someone replaced the import with a copy — which is why the
architecture test asserting one definition is worth writing alongside it.

### D-2 — The card list becomes `MVPFilteredListView`, the table composes the mixin with `FilterView`

Research R3: `MVPFilteredListView` is a convenience composition of `MVPListViewMixin` and
`FilterView`, and no filtered-table equivalent exists. `MVPTableViewMixin` already extends
`MVPListViewMixin`, so the table's form is `class ItemTableView(MVPTableViewMixin, FilterView)`,
which is the pattern `MVPListViewMixin`'s own docstring names. Nothing is forked and nothing is
reimplemented.

`ItemListView` today is an `MVPListView`; it becomes an `MVPFilteredListView`. That changes its base
class, so the contributor page, which subclasses it, has to be checked rather than assumed (D-6).

### D-3 — `search_fields` replaces the two `search_fields = None` declarations

Both views name `search_fields = None` today with a comment pointing at this issue. Each becomes
`search_fields = SEARCH_FIELDS`, and the table's `actions` list regains `"search"` and `"filter"`
alongside `"create"`. FS-009 switched those controls off deliberately so a later upstream default
could not introduce them; switching them on here is that decision being reversed by the feature that
owns it.

The paths, from FR-002: `citation_key`, `title`, `title_short`, `original_title`,
`container_title`, `item_names__name__family`, `item_names__name__given`,
`item_names__name__literal`.

### D-4 — The filtered queryset is made distinct in the filterset, not in each view

Research R10: three of the four filters and three of the eight search paths traverse `item_names`,
so a reference can match more than once. `.distinct()` belongs in the shared definition — putting it
in each view is two places to forget it, and putting it in neither is a defect that only shows up on
data where a contributor holds two roles, which the demo seed may not even contain. Tests assert the
single occurrence directly (FR-005, FR-011) rather than asserting `.distinct()` was called.

Interaction to watch: the table orders on an annotated `issued` column, and `DISTINCT` combined with
an ordering on an annotation is where this goes wrong quietly. The task that adds it runs the
table's existing sort tests as its own check.

### D-5 — The year filter reuses FS-009's subquery annotation, on both views

Research R9: the table annotates `issued` from a `Subquery` over `ItemDate`, chosen over a join
because a join multiplies rows and corrupts the paginator's count. The card list has no such
annotation. Rather than filtering one view through an annotation and the other through a join —
which is two behaviours wearing one name — the annotation moves into the shared definition and both
views carry it.

Year matching is on the annotated value's year, accepting a year-only stored date and a range
beginning in that year, and excluding a reference with no `issued` row at all, which falls out of
the subquery being null (FR-012).

### D-6 — The contributor page must not inherit the controls

`ContributorDetailView` subclasses `ItemListView`, so changing the card list's base class and giving
it `search_fields` hands the contributor page a search box and four filters it must not have
(FR-025, research R11). It overrides them back off — `search_fields = None`, no filterset — and a
test asserts the contributor page renders neither control. Written as a task of its own so it cannot
be lost inside the card-list task.

### D-7 — Applying a filter drops the current sort; raise it upstream, carry it in our own form

Research R5, and the one finding that is not simply mechanical. The filter form is a GET form
carrying its own fields, so submitting it replaces the query string and discards `?sort=`. Losing
`?page=` is correct — a new filter belongs on page one — but losing the sort is the same defect as
#88 arriving from the other direction.

Two things happen, in this order:

1. **Raise it upstream** as a django-mvp issue, with the reproduction and the suggested fix (the
   filter form should carry the current sort, exactly as the pagination link now carries the rest of
   the address). This is the standing direction for a defect in the shared component, and it serves
   every project using it rather than this one.
2. **Carry the sort in our own filterset's form** as a hidden field populated from the request. This
   is our form, rendered by the component from `filter.form`, so it forks no upstream template and
   overrides no block — the measure lives entirely in `literature/ui/filters.py`. If it turns out to
   need a template override to work, it is abandoned and the limitation is documented instead: a
   fork of someone else's markup is explicitly not what this feature does.

The task carries that abort condition in its brief, so the decision does not get made silently by
whoever implements it.

### D-8 — The empty-result message is the filterset's, not the empty catalogue's

FR-030: a search matching nothing must read differently from an empty catalogue, and must keep its
controls. django-mvp's list and table pages both render an empty state; the distinction is ours to
draw from whether a query is in force. The wording is a translatable string on each view, and the
test asserts both messages appear in their own circumstance and never together.

### D-9 — Packaging, and the assertions that pin it

`django-filter` is added to the `ui` extra and the django-mvp floor rises to `>=0.19.1`. Three
things move together, in one task: `pyproject.toml`, the exact-list assertion in
`tests/test_ui/test_packaging.py` (research R7), and `poetry.lock`, which pins django-mvp at 0.19.0
today. `django_filters` also joins `INSTALLED_APPS` in the test settings and the demo settings, and
the installation documentation, in the three places django-tables2 occupies.

### D-10 — The floor rise makes the pagination assertions move

`tests/test_ui/test_views.py` lines 119 and 340 assert `'href="?page=2"'` exactly. Once the floor
carries the fix, the rendered link preserves the rest of the address, so those assertions become
what the fixed component emits. The demo guard needs no change: its regex already tolerates other
parameters either side of `page=2` (research R6). This is what closes #88, and the task's test is
the one that proves a sort survives a page move rather than merely that a link changed shape.

### D-11 — The demo needs language values before its filter means anything

Research R8: not one of the 28 seed references carries a `language`. The seed gains language values
across several distinct languages, and the guard then has something to filter on. The same task
settles how the guard reaches a second page of a narrowed result, given a page size of 24 over 28
references — either the narrowing is a search broad enough to leave more than 24, or the seed grows.

### D-12 — The README loses a paragraph it should no longer carry

The front-end section currently tells readers that a chosen sort is discarded on a page change and
points at #88. This feature removes that limitation, so the paragraph goes, and the section gains
what the search matches, what it deliberately does not, what each filter narrows on, and how the
three compose (FR-036). A stale limitation left in place is worse than no documentation, because it
tells a reader not to rely on something that now works.

## Story → task shape

| Story | Tasks, in order |
|---|---|
| Foundational | Packaging and floor (D-9), then `filters.py` with `SEARCH_FIELDS`, the filterset, the annotation and the distinct rule (D-1, D-4, D-5) |
| US-1 #91 | Table gains `search_fields` and its actions (D-3); no-results message (D-8); query-count guarantee |
| US-2 #92 | The four filters, their composition, invalid-value behaviour (D-1, FR-017) |
| US-3 #93 | Floor-driven assertion moves (D-10), sort-survival tests, the hidden sort field and its upstream issue (D-7) |
| US-4 #94 | Card list gains the same definition (D-2); contributor page holds them off (D-6); the two-presentations agreement test |
| US-5 #95 | Seed languages, guard walks search + filter + page move (D-11); README and CHANGELOG (D-12) |

## Complexity Tracking

No deviations. The one thing that could have become a deviation — reimplementing filtering because
no filtered-table class exists upstream — is avoided by composing the documented mixin instead
(D-2).

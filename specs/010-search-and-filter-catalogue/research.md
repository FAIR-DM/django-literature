# Research — 010 Find a reference in a large catalogue

Everything here is read from django-mvp at `origin/main` (v0.19.1, tagged 2026-08-19) and from this
repository's own tree, on 2026-08-20. Findings that change the plan are marked as such.

## R1 — The search is upstream already, and needs a field list and nothing else

`mvp/views/list.py` carries `SearchMixin`, which `MVPListViewMixin` composes through
`SearchOrderMixin`. Declaring `search_fields` is the whole integration:

- It reads `?q=`, strips it, and splits on whitespace.
- Each word is matched with `icontains` across every declared field path, combined with `OR`.
- ORM field paths are permitted, so `item_names__name__family` reaches contributors through the
  through-model.
- With `search_fields` unset or empty the mixin is a complete no-op, which is the state both
  catalogue views are in today — each names it out explicitly with a comment pointing at this issue.
- It puts `search_query` and `is_searchable` into the context.

**Consequence:** FR-002's field list is a literal declaration, not code to write. The spec's
case-insensitive-fragment requirement (FR-003) is what the mixin already does, so it is satisfied by
adopting it rather than by anything of ours.

## R2 — Filtering needs `django-filter`, a new dependency in the `ui` extra

`mvp/integrations/django_filters/views.py` imports `django_filters.views.FilterView` at module
import and raises a `missing_dependency` error if it is absent. django-mvp does not depend on
django-filter itself, and it is not installed in this project's environment today (`django_filters`
is missing; `django_tables2` is present).

**Consequence:** `django-filter` joins the `ui` extra, under Article VII — a stated justification,
`deptry` clean, and the core resolving none of it. It is the same shape as the django-tables2
addition FS-009 made, and it satisfies the stack constraint that a front-end package is reached
through django-mvp's own integration where one exists: this one exists.

## R3 — The composition point is the mixin, and it is documented for exactly this

There is no `MVPFilteredTableView`. `MVPFilteredListView` is a two-line convenience class composing
`MVPListViewMixin` with `FilterView`, and `MVPListViewMixin`'s own docstring names the pattern:

> Subclass this directly (instead of `MVPListView`) when you need to compose with another base
> class (e.g. `FilterView`).

`MVPTableViewMixin` extends `MVPListViewMixin`, so the table's filtered form is
`MVPTableViewMixin, FilterView` by the same sanctioned route.

**Consequence, and it is the plan's central decision:** the card list becomes
`MVPFilteredListView`, the table becomes `MVPTableViewMixin, FilterView`. This is composition of
documented upstream extension points, not a workaround, so it does not fall under the standing rule
about not working around upstream defects. The absence of a ready-made filtered *table* class is a
convenience gap worth mentioning upstream, not a blocker, and nothing here forks upstream markup.

## R4 — The search box only submits when a filterset is configured *(confirms upstream #275)*

`cotton/page/list/actions/search.html` renders its input and its submit button with
`form="filterForm"`. `filterForm` is declared in `cotton/page/list/actions/filter.html`, inside
`{% if filter %}` — a context key only `FilterView` sets. So a view with `search_fields` and no
filterset renders a search box wired to a form that does not exist, and typing into it does nothing.

**Consequence:** this feature is unaffected, because it configures a filterset on both views, and
that is why the search box can be adopted at all. It also fixes the shape of the design: **search
and filters are one form and one submit**, so a search term and every filter value travel together.
FR-015's composition falls out of the markup rather than needing arranging. Upstream PR #279 would
decouple them; it is open and unmerged, and this feature neither waits for it nor is broken by it.

## R5 — Applying a filter drops the current sort *(finding — needs a decision in the plan)*

The filter form is `<c-form method="get" action=".">` carrying only the filterset's own fields plus
the search input. A GET form submission replaces the whole query string, so a sort held in `?sort=`
and a page held in `?page=` are both discarded when filters are applied.

Losing the page is right — a new filter should return to page one. Losing the sort is the same
defect class as #88, arriving from the opposite direction: the pagination links dropped the sort,
and now the filter form does.

**Consequence:** FR-018 and FR-019 are not fully satisfied by adopting the upstream components as
they stand. The durable fix belongs upstream — the filter form should carry the current sort as a
hidden field, exactly as the pagination link now carries the rest of the address.

**Superseded on the disposition, 2026-08-20:** no issue is filed, because that component is already
being worked on upstream. Plan D-7 settles what this feature ships instead — the hidden field on our
own filterset's form, with two abort conditions — and tasks T020 carries it.

## R6 — The pagination fix is in 0.19.1, and the floor and the lock both move

`cotton/pagination/link.html` now renders `href="{% querystring page=page %}"`, replacing the
hard-coded `?page=N`. The change landed in commit `e413b36` and the only tag containing it is
`v0.19.1`.

This project's `poetry.lock` pins django-mvp `0.19.0`, and the `ui` extra's floor is `>=0.19,<1.0`.
Both move, and so do the two tests that pin the old address exactly — `tests/test_ui/test_views.py`
lines 119 and 340, each asserting `'href="?page=2"' in content`. The demo guard does **not** move:
`demo/smoke.py`'s `SECOND_PAGE_LINK_RE` was already written to tolerate other parameters either side
of `page=2`, in anticipation of this fix.

## R7 — The packaging test pins the `ui` extra as an exact list

`tests/test_ui/test_packaging.py::test_the_ui_extra_is_exactly_the_front_end_packages` asserts the
extra's contents literally. Adding django-filter and raising the django-mvp floor both move that
assertion. That is the test doing its job, and it is the same move FS-009 made.

## R8 — No demo reference carries a language, so the language filter would render empty

`demo/seed/catalogue.json` holds 28 entries. Counted: thirteen distinct item types, twenty-four
distinct issued years, one entry with no issued date at all — and **zero entries carrying a
`language` value**.

**Consequence:** US-5's requirement that every filter offer more than one value is not met by the
current seed, so seeding language values is real work inside that story rather than a detail. A
second consequence for the same story: at a page size of 24 over 28 references, most filtered
results fit on one page, so the guard's "second page of a narrowed result" needs either more seed
entries or a narrowing that still leaves more than 24 — worth settling when the guard is written.

## R9 — The table already annotates the issued date; the card list does not

`ItemTableView.get_queryset()` annotates `issued` from a `Subquery` over `ItemDate` restricted to
the `issued` slot, deliberately avoiding a join so the paginator's count query stays correct and
rows are not multiplied. `ItemListView` has no such annotation.

**Consequence:** the year filter needs that annotation on both views if it is to be expressed the
same way for both, which is the shared-definition requirement (FR-023). The existing subquery is the
pattern to follow, and the reason not to reach for a join is already recorded in FS-009's research.

## R10 — Contributor and multi-value filtering can multiply rows

Filtering across `item_names` traverses a to-many relation, so a reference crediting the same
contributor in two roles matches twice, and a multi-value filter matching two rows of a to-many
returns the item once per matching row. FR-011 and FR-005 both require the reference to appear once.

**Consequence:** the filtered queryset needs distinct results, and the plan must say where that
happens so it is not left to whichever view is written first. Note that it interacts with ordering
on an annotated column, which is exactly where a careless `.distinct()` starts producing surprises,
so it belongs in the shared definition with a test rather than in each view.

## R11 — One route, two views, chosen by a setting

`literature/ui/catalogue.py` resolves `LITERATURE["CATALOGUE_VIEW"]` per request, defaulting to
`ItemTableView`. Both presentations therefore serve the same URL, and the contributor page subclasses
`ItemListView`.

**Consequence:** the contributor page inherits from the card list, so whatever the card list gains,
the contributor page gains unless it is explicitly held back. FR-025 requires it unchanged, so the
shared definition must be something the contributor page does not switch on by inheriting.

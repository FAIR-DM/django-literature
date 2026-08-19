# Research — 009 A tabular catalogue view

What was checked in the source rather than assumed, and what each finding forces. Every claim below
was read out of the code named beside it; nothing here comes from documentation alone.

## R1 — The dependency floor is django-mvp 0.19.0, not 0.17

`mvp.integrations.django_tables.views` has existed since django-mvp 0.13.0, but everything this
feature actually renders through arrived in **0.19.0** (tagged 2026-08-18, and on the package index):

| Behaviour | First released in |
|---|---|
| Import path `mvp.integrations.django_tables.views` | 0.13.0 |
| Full-screen table layout (`table_view.html` as a filled page) | 0.19.0 |
| `mvp-col-*` width classes and inferred column alignment | 0.19.0 |
| `table_actions` context key | 0.19.0 |
| Refusal of a view-level `order_by` | 0.19.0 |
| Action set without `sort` | 0.19.0 |

A 0.17 or 0.18 install imports fine and then renders the old card-in-a-scrolling-document layout,
with no `table_actions` key at all. The `ui` extra's floor rises from `>=0.17,<1.0` to `>=0.19,<1.0`.

**Consequence:** `tests/test_ui/test_packaging.py` asserts the extra's contents as an exact list, so
that assertion moves in the same change as the dependency. That is the test doing its job, not an
obstacle.

## R2 — `Item` has no `get_absolute_url()`, so `linkify=True` cannot be used

Grepped `literature/models.py`: no model defines `get_absolute_url`. The name appears only in three
comments in `literature/ui/views.py` explaining why `success_url` is mandatory on the write views.

django-tables2's `linkify=True` resolves the target through the record's `get_absolute_url()`, so it
would raise. Two ways out, and the second is rejected:

- **Chosen:** `linkify=("literature:item-detail", {"pk": A("pk")})` on the title column — the
  route name lives in the table class, inside `literature/ui/`.
- **Rejected:** adding `get_absolute_url()` to `Item`. It would hard-code the opt-in app's URL
  namespace into the headless core, which is the coupling Article X and the core/UI split exist to
  prevent. The core boots against a urlconf with no patterns at all
  (`tests/test_ui/test_boot.py`), so the method would raise `NoReverseMatch` in exactly the
  configuration the core is guaranteed to work in. Routing is `literature/ui/urls.py`'s contract and
  stays there.

## R3 — A cell whose value is empty never reaches its renderer

`django_tables2/rows.py:137-171`: the accessor is resolved first, and if the result is in the
column's `empty_values` — `(None, "")` by default — the cell short-circuits to the table's `default`
placeholder and **`render_<name>` is never called**.

This is the single sharpest edge in the whole feature, because it defeats the title fallback chain
in precisely the case the chain exists for: an item with `title = ""` renders the placeholder rather
than falling back to its short title. The same applies to any column with no model attribute behind
its name — the credited-names column and the edit column both resolve to nothing and would render
the placeholder.

**Consequence:** every column whose value is computed declares `empty_values=()`. This is the
library's own sanctioned pattern — `TemplateColumn` hardcodes it, `BooleanColumn` passes it.

## R4 — Two feared breakages do not happen

Checked directly in `mvp/templates/table_view.html` rather than assumed from the layout change:

- **Pagination markup is unchanged.** The table page renders `<c-pagination :page_obj="page_obj" />`
  from Django's own `page_obj`, not django-tables2's paginator templates. The demo guard's exact
  literal `href="?page=2"` and the suite's assertion on it both survive.
- **The position line survives.** The same `Showing {start}-{end} of {total} {name_plural}`
  translation block is in the table footer, fed by `get_model_info()`, so the existing override that
  makes it read "publications" rather than "items" carries over untouched.

What does change: `MVPTableView` sets no `paginate_by` at all, where `MVPListView` sets 24. Left
alone the catalogue would silently become unpaginated and the whole footer bar would vanish, because
it renders under `{% if page_obj %}`. The table view sets `paginate_by` explicitly.

## R5 — The empty state is gated behind the table's own `empty_text`

On a list view the empty state renders unconditionally. On a table it renders only inside
`{% if table.empty_text %}` in `django_tables2/bootstrap5-mvp.html`, and only when the table class
names `Meta.template_name = "django_tables2/bootstrap5-mvp.html"` — without that, django-tables2
falls back to its own stock template and none of the mvp column, alignment or empty-state behaviour
applies.

**Consequence:** the table class sets both. The existing `empty_state_heading` /
`empty_state_message` on the view are then rendered by the mvp template as they are today.

## R6 — An action column must declare `orderable=False` to be laid out correctly

`mvp/templatetags/mvp.py:187` identifies an action column by two signals together: no resolvable
model field **and** `orderable=False`. That combination gets `text-center`. A column with no
resolvable field that is still orderable gets no alignment at all, on the reasoning that its kind
cannot be determined. The edit column therefore declares `orderable=False` for layout as well as for
the reason the spec gives.

## R7 — Sorting by the issued date needs an annotation, and NULL placement is ours to state

django-tables2 passes ordering keys to `QuerySet.order_by()` verbatim and does nothing about NULLs;
placement would be whatever the database defaults to, which differs between SQLite and PostgreSQL —
both of which this package supports. Since FR-018 requires undated references to be kept and ordered
consistently, the ordering is explicit rather than inherited:

- The queryset annotates the `issued` slot's start date through a `Subquery` on `ItemDate` filtered
  to `date_type="issued"`. A join-based filter is rejected: it risks row multiplication and
  interacts badly with the paginator's count query.
- An `order_issued` method on the table returns `(queryset, True)`, applying `nulls_last=True` in
  both directions, so undated references sit at the end whichever way the column is sorted.
- `ItemDate.begin` is already indexed individually (`itemdate_begin_idx`), and there is a composite
  index on `(item, date_type)`, so the subquery has index support without any model change.

## R8 — The date partial is shared, and a Python-rendered column would silently fork it

`literature/ui/templates/literature/ui/date_value.html` carries the whole precision-and-range
rendering rule in one line and is included by both the catalogue row and the reference page. Its own
comment states the constraint: the two must not drift apart.

A `Column` with a Python `render_` method would reimplement that rule in a second place. The issued
column is therefore a `TemplateColumn` over a small wrapper that includes the same partial, so the
rule stays in one file and the guard against drift keeps working.

## R9 — The credited-names column must not touch the manager

`ManyToManyColumn` is unusable here: its default filter calls `.all()` on the relation, and
`rows.py` special-cases it with an `.exists()` check **per row** before rendering. Both defeat any
prefetch.

The column is a plain `Column` with a `render_` method reading a `Prefetch(..., to_attr=...)`
attribute, filtered in Python over the already-fetched list. Filtering through the manager
(`record.item_names.filter(...)`) would issue a query per row and is what the existing query-count
test is there to catch. The existing test asserting a constant query count across page sizes is
extended to the table rather than duplicated.

## R10 — The card's readability tests are pinned to the default route

`tests/test_ui/test_views.py` carries a `TestCatalogueListReadability` class of roughly a dozen
assertions written against the card at the catalogue route: the type badge, the pluralised role
headings, the abstract snippet and its truncation, the cite-key label, the `link-hover` class on
both links. All of them are about the **card**, and the card is not being removed.

**Consequence:** these tests move to the card view's own route rather than being deleted or loosened.
The test urlconf gains a second route serving the card view, which is also the honest test of FR-022
— it exercises the routing change the documentation tells a project to make. Deleting or weakening a
passing test to accommodate a change of default would be discarding the evidence that the card path
still works, at the exact moment the feature promises it does.

`tests/test_demo/test_seed.py` separately reads the card template off disk and asserts it truncates
the abstract, and reads `ItemListView.paginate_by`. Both keep working because the card view keeps its
name, its template and its page size.

## R11 — Host projects must install `django_tables2`

Both `<c-addons.django-table>` and the mvp table template `{% load %}` the `django_tables2`
templatetag library, and Django resolves those only from installed apps. There is no
`DJANGO_TABLES2_*` setting anywhere in django-mvp, and no template-pack setting — the template is
chosen per table class through `Meta.template_name`.

**Consequence:** `django_tables2` joins `INSTALLED_APPS` in the test settings and the demo settings,
and the README's installation block — which a host copies verbatim — gains the same entry. This is
host configuration the package cannot supply for them, so it is documented rather than assumed.

`tests/test_ui/test_architecture.py` forbids the core importing any front-end root; `django_tables2`
is added to that list so the core stays provably free of it.

---

## Amendments after design review

Three of the eleven findings above were checked again and two of them were wrong in a way the
original wording hid. Both are recorded here rather than edited in place, because the shape of the
mistake is the useful part.

### R1 — the width classes exist, but the default is not the safe one

R1 established that the mvp table ships `mvp-col-*` width classes. It did not establish what a
column gets when it names none, and the answer is not benign: `MVP_CONFIG["table"]["wrap"]` defaults
to `False`, so an unclassed cell renders `white-space: nowrap` with no maximum width. One long
container title then stretches its column until the table scrolls sideways. The free-text columns
name `mvp-col-wrap` with a maximum, the short ones name `mvp-col-shrink` on both `td` and `th`
(plan D-5).

**"The mechanism exists" is not "the default is right."** R1 confirmed availability and read as
though it had confirmed behaviour.

### R4 — the pagination markup survives *because* it carries nothing

R4 checked that the pagination component and the position line both render on the table page, and
they do. What it did not check is whether a page link carries anything other than the page number.
It does not: the href is `?page=N`, an outright replacement of the query string, so a chosen sort is
discarded the moment the reader turns the page. The sort links on the same page do the opposite —
they preserve what is already there. Plan D-14 owns the fix, upstream.

**A survival check is not a behaviour check.** The finding "unchanged" was true and useless, and it
was true for the reason that makes the feature fail.

### R3 — right, and its consequence runs the other way too

R3's finding stands: a cell whose value is empty short-circuits and its renderer never runs, which is
why every computed column declares `empty_values=()`. The consequence R3 did not draw is that the
same switch is what makes the table's empty-value marker unreachable, so a column declaring it owns
its own empty case (plan D-4).

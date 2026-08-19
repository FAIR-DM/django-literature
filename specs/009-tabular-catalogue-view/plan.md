# Implementation Plan: A Tabular Catalogue View

**Branch**: `009-tabular-catalogue-view` | **Date**: 2026-08-19 | **Spec**: [`spec.md`](spec.md)

**Input**: Feature specification from `specs/009-tabular-catalogue-view/spec.md`

## Summary

Add a second list presentation to `literature.ui` — a table built on django-mvp's django-tables2
integration — and route the catalogue at it by default, while keeping the existing card list as a
public, routable, still-exercised alternative. Presentation only: no model, no field, no migration.

The shape follows django-mvp's own vocabulary, `MVPListView` beside `MVPTableView`: the existing
`ItemListView` keeps its name, its card template and its behaviour, a new `ItemTableView` sits
beside it, and the default route moves from one to the other. Everything a row shows comes from a
column on one new `ItemTable` class, with the sortable columns ordering in the database and the two
computed columns declining to sort.

## Technical Context

**Language/Version**: Python ≥3.11 for the core, ≥3.12 wherever the front end is installed (the `ui`
extra carries a `python_version >= '3.12'` marker because django-mvp requires it).

**Primary Dependencies**: django-mvp `>=0.19,<1.0` (raised from `>=0.17`, see research R1) and
django-tables2 `>=3.0,<4`, both in the `ui` extra only. The core's three runtime dependencies are
untouched.

**Storage**: unchanged. Every column reads what the store already holds.

**Testing**: pytest + pytest-django, `tests.settings`. New module `tests/test_ui/test_tables.py`
mirrors `literature/ui/tables.py`, as Article XIV requires; view behaviour extends
`tests/test_ui/test_views.py`.

**Target Platform**: server-rendered Django, SQLite and PostgreSQL both supported — which is why
NULL ordering is stated explicitly rather than inherited from the database (research R7).

**Project Type**: reusable Django package with an opt-in front-end app.

**Performance Goals**: a page costs a constant number of queries regardless of how many rows are on
it (FR-012), which is the existing guarantee for the card list extended to the table.

**Constraints**: the core must stay free of any front-end import; the card list must keep working
and keep being tested; the demo guard must keep walking.

**Scale/Scope**: two view classes, one table class, two small templates, one settings entry in two
places, one documentation section. Around a dozen new tests plus the re-pointing of an existing
class.

## Constitution Check

Checked against `memory/constitution.md` v4.0.0 (this branch amends it — see D-13).

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every task writes its test before its code | Applies, no tension |
| II Simplicity / III Anti-Abstraction | Two view classes and one table class, no base class invented to share between them | Pass |
| V Escaping | Every cell that composes markup does it in a template, so autoescaping is the control and no column builds markup in Python (D-6, D-7). The credited-names cell is the one that had to move to satisfy this | Applies, tasked |
| VI Documentation | README's front-end section and installation block both change; CHANGELOG entry in the same PR | Applies, tasked |
| VII Dependency discipline | One new runtime dependency in an optional extra, justified in research R1/R11; `deptry` must stay clean | Applies, tasked |
| VIII i18n (non-negotiable) | Every column header, the "and N others" suffix and the empty-value marker are translatable; `ngettext` for the suffix because it is countable | Applies, tasked |
| IX CSL JSON | No conversion path touched | N/A |
| X Embeddable package | The new dependency is host configuration, so it is documented in the installation block rather than assumed; routing stays the host's to own | Applies, tasked |
| XI Data integrity | No model change, no migration | Pass by construction |
| XII Living demo | Demo settings, and the guard extended to the table's row link and edit control | Applies, US-5 |
| XIII Data-model conventions | No field added, so no indexing decision to record. The ordering added leans on `itemdate_begin_idx` and `itemdate_item_date_type_idx`, which already exist | Pass |
| XIV Test structure | `literature/ui/tables.py` → `tests/test_ui/test_tables.py`, one module, split by class. Not a `non-mirror-paths` entry — its subject is a Python module | Applies, tasked |
| Stack constraints | Amended on this branch: the clause requiring a constitutional amendment before adopting a further front-end package is removed, and django-tables2 is admitted under Article VII | See D-13 |

No entry in Complexity Tracking: nothing here is a deviation.

## Project Structure

### Documentation (this feature)

```text
specs/009-tabular-catalogue-view/
├── spec.md
├── decisions.md
├── research.md
├── plan.md          # this file
├── progress.md
├── tasks.md
└── feature-state.json
```

### Source code

```text
literature/ui/
├── tables.py                      # NEW — ItemTable
├── views.py                       # ItemListView unchanged; ItemTableView added
├── urls.py                        # "" now serves ItemTableView
└── templates/literature/ui/
    ├── item_list_item.html        # unchanged (card, still used by the contributor page)
    ├── _date_value.html           # unchanged (now also included from a table cell)
    ├── _table_issued.html         # NEW — one-line wrapper so the table reuses _date_value.html
    ├── _table_contributors.html   # NEW — the credited names, escaped by the template layer
    └── _table_actions.html        # NEW — the row's edit control

tests/
├── settings.py                    # + django_tables2
├── urls.py                        # + a route serving the card view, for the re-pointed tests
└── test_ui/
    ├── test_tables.py             # NEW — mirrors literature/ui/tables.py
    ├── test_views.py              # + ItemTableView; card readability re-pointed
    ├── test_urls.py               # + the new default
    ├── test_packaging.py          # exact dependency lists updated
    └── test_architecture.py       # + django_tables2 to the forbidden roots

demo/
├── settings.py                    # + django_tables2
└── smoke.py                       # walk asserts the row link and the edit control
```

## Design decisions

### D-1 — Two view classes, and the card keeps its name

`ItemListView` stays exactly what it is: the card list, the same `list_item_template`, the same
`paginate_by`, the same behaviour. A new `ItemTableView` is added beside it, and `urls.py` points
the `item-list` route at the table.

Rejected: renaming so that `ItemListView` becomes the table. It reads tidier — the default view
holding the default name — and it silently changes what every downstream import already resolves to,
including anything that subclassed it. The name a project already depends on keeps meaning what it
meant. This also mirrors the layer this app is built on, where `MVPListView` and `MVPTableView` are
siblings rather than one shadowing the other.

`ContributorDetailView` goes on subclassing `ItemListView` and so stays on cards with no change of
its own (FR-023).

**The route name does not change.** `literature:item-list` still reverses, still means "the
catalogue", and every breadcrumb, success URL and `crud_views` entry that names it keeps working.
Only the class behind it moves.

### D-2 — `ItemTableView` composes the mixin, and sets what the mixin does not

```python
class ItemTableView(MVPTableView):
    model = Item
    table_class = ItemTable
    paginate_by = 24
    page_title = CATALOGUE_TITLE
    actions = ["create"]
    directory = ["create"]
    show_create_action = True
    crud_views = CRUD_VIEWS
    search_fields = None
    empty_state_heading / empty_state_message  # as ItemListView has them
```

- `paginate_by = 24` is **mandatory, not inherited**: `MVPTableView` sets none, and without it the
  catalogue becomes unpaginated and the whole footer bar disappears because it renders under
  `{% if page_obj %}` (research R4). 24 is the card list's current page size, kept so the change of
  presentation does not also change how much is on a page.
- `actions = ["create"]` replaces the mixin's `["search", "filter", "create"]`. Search is #49's and
  filter renders nothing on a non-`FilterView` anyway, but both are named out explicitly for the
  reason `ItemListView` already names `search_fields = None` out explicitly: so a later change to an
  upstream default cannot put an unspecified control on the package's default page (FR-025, D-6 in
  `decisions.md`).
- **No `order_by`.** The mixin raises `ImproperlyConfigured` at instantiation if it finds one.
  Ordering lives on the table class.
- `get_queryset()` carries **both** prefetches and the issued-date annotation (D-5, D-6). Two, not
  one: the credited-names prefetch into `to_attr="contributors"`, and `item_dates`, because the
  issued cell reaches for the whole `ItemDate` row — `_date_value.html` needs its `end`, `begin` and
  `literal`, which the D-8 annotation cannot supply since it carries only the start date. The card
  view already pays for `item_dates` for the same reason. Omitting it costs one query per row and
  breaks FR-012.

### D-3 — One table class, in a new `literature/ui/tables.py`

New module, because a table class is neither a view nor a form and `views.py` is already long. Its
mirror test is `tests/test_ui/test_tables.py` — one module, split by `Test<Column>` classes, never a
`non-mirror-paths` entry.

`Meta` carries three things:

- `template_name = "django_tables2/bootstrap5-mvp.html"` — without it django-tables2 falls back to
  its own stock template and none of the mvp column widths, alignment or empty state apply
  (research R5).
- `empty_text` — load-bearing, but as a **flag rather than a string**: the mvp template renders its
  empty state inside `{% if table.empty_text %}` and then shows the view's `empty_state_heading` and
  `empty_state_message` instead of the text itself. Set it, and do not spend words on its wording.
- `default` — the empty-value marker FR-010 asks for, translatable, replacing the library's `"—"`.

**No `Meta.order_by`.** An earlier draft had `order_by = ("-created",)` and called it the default
order. It is a no-op: django-tables2 validates every order-by alias against the declared orderable
columns and drops what it cannot find, and there is no `created` column — FR-002 forbids one. The
page is newest-first because `Item.Meta.ordering` says so, which is exactly what `ItemListView`
already relies on and says out loud. FR-013 is satisfied by the model, and stating it twice would
have left a line that looks load-bearing and does nothing.

`fields` is not used: every column is declared explicitly, so a field added to `Item` later never
silently becomes a column.

`ItemTable`'s docstring states the contract its rows require, because this is a public class in a
published package and a consumer can pair it with a plain `SingleTableView`: the credited-names cell
reads the `contributors` attribute that `ItemTableView.get_queryset()` places. `render_contributors`
reads it defensively so a wrongly-shaped queryset degrades rather than raising per row. A shared
queryset method on `Item` would be the Django-first move if a second caller ever appears; one caller
does not justify it.

### D-4 — `empty_values=()` on every computed column

The one edge that would otherwise defeat this feature silently. A column whose accessor resolves to
`""` or to nothing at all short-circuits to the table's placeholder and **its renderer never runs**
(research R3). That is exactly the case the title fallback chain exists for, and it is also the
state of the credited-names and edit columns, which have no model attribute behind their names.

Every column with a `render_` method declares `empty_values=()`. `_table_actions.html` goes through
`TemplateColumn`, which sets it itself.

**And the consequence, which cuts the other way:** `empty_values=()` is the same switch that stops
the table's `default` marker ever being reached, so a column that declares it owns its own empty
case. The two that have one — credited names with nothing credited, and an issued cell on a
reference whose only date is `accessed` — must render the marker themselves rather than an empty
`<td>`. FR-010 is delivered by those two cells and by `Meta.default`, not by the library.

### D-5 — The columns, one row of the table each

| Column | Mechanism | Sorts on | Notes |
|---|---|---|---|
| `citation_key` | plain `Column` | `citation_key` (indexed) | nothing computed |
| `type` | `Column(order_by="type")`, **no renderer** | `type` (indexed) | django-tables2 resolves a choice field through `get_FOO_display()` before any renderer runs, so the translated label arrives on its own and a `render_type` would only restate it. Recorded here so nobody adds one back. Plain text, not a badge — the badge is the card's idiom and a cell of badges reads as noise. FR-017's documentation note attaches here |
| `title` | `Column(empty_values=(), order_by="title", linkify=(...))` + `render_title` | `title` (indexed) | fallback chain in `render_title`; `linkify` wraps its output rather than replacing it |
| `container_title` | plain `Column` | `container_title` (indexed) | |
| `contributors` | `TemplateColumn(template_name="literature/ui/_table_contributors.html", empty_values=(), orderable=False)` | — | reads the prefetch, never the manager; the markup is built in the template, not in Python (D-6) |
| `issued` | `TemplateColumn(template_name="literature/ui/_table_issued.html", empty_values=())` + `order_issued` | the `issued` annotation, from US-3 onward | reuses `_date_value.html` (D-7). Ships `orderable=False` in US-1 and is switched on when the annotation lands, so the header never advertises a sort that would raise |
| `actions` | `TemplateColumn(template_name="literature/ui/_table_actions.html", orderable=False, verbose_name="")` | — | `orderable=False` is also what earns it centred alignment (research R6) |

**The column is named `contributors` and its header reads "Authors".** The spec says authors
throughout and the glossary deprecates `Author` for the model-side term, so the two artefacts were
using different words for the same column without either saying which one a reader sees. The
attribute follows the glossary, the header follows the reader — the cell falls back to editors, but
"Authors" is what a person scanning a bibliography expects, and FR-006 describes it that way.

**The long-title edge case needs width classes named per column, and the default does not handle
it.** Research R1 established that the mvp table ships width classes. It did not establish what
happens with none: the project-wide wrap default is `False`, so an unclassed cell is
`white-space: nowrap` with no maximum, and one long container title stretches its column until the
table scrolls sideways. The two free-text columns therefore name their own:

| Column | Classes |
|---|---|
| `title` | `mvp-col-wrap mvp-col-max-xl` |
| `container_title` | `mvp-col-wrap mvp-col-max-md` |
| `citation_key`, `type`, `issued` | `mvp-col-shrink`, on `td` and `th` both, since each holds a short value and would otherwise be widened by its own heading |

Wrapping is not truncating. The full text stays in the cell, on more than one line, so the
no-truncation rule below and the demo guard that depends on it are both unaffected.

**The title link is built from the route, not from the record.** `Item` has no `get_absolute_url()`
and will not be given one, so `linkify=("literature:item-detail", {"pk": A("pk")})` (research R2).
It carries `attrs={"a": {"class": "link link-hover"}}` so the table's links look like the card's;
those two classes are already in the allowlist the template guard enforces.

**The title cell must not truncate.** The demo guard follows a row's link and then asserts the link's
own text appears on the reference page it landed on. A truncated cell breaks the walk, and would
also make the catalogue's idea of a reference's name differ from the reference page's.

### D-6 — The credited-names column reads a `to_attr` prefetch

`ManyToManyColumn` is unusable: its default filter calls `.all()` on the relation and django-tables2
additionally runs an `.exists()` check per row before rendering (research R9). Both defeat the
prefetch, and the existing constant-query-count test is there to catch exactly that.

The view prefetches `item_names` filtered to the author and editor roles, `select_related` on the
name, ordered by `(role, order)`, into `to_attr="contributors"`. `render_contributors` filters that
already-fetched list in Python — authors if any, else editors, first three, and the count of the
rest — and returns those values to a template. It builds no markup.

**That split is the point, and it is a security decision, not a style one.** A contributor's name is
free text entered through the front end's own write pages, which this feature deliberately leaves
open (FR-020). A Python renderer emitting one `<a>` per name is one `mark_safe` away from executing
whatever a name contains, on what this feature makes the package's default page. So the cell is a
`TemplateColumn` over `_table_contributors.html`, exactly as the issued cell is over
`_table_issued.html`, and Django's autoescaping is the control. Nothing hand-builds an anchor.
`format_html_join` would also be safe, but a template is safe by default and the codebase already
has the idiom.

The template holds the "and N others" suffix under `blocktrans count`, and the empty case — no
credited names at all — renders the table's marker rather than nothing (D-4).

### D-7 — The issued column reuses the shared date partial

`_date_value.html` holds the whole precision-and-range rule and is included by both the card and the
reference page; its own comment says the two must not drift. Rendering the same rule again in Python
would fork it (research R8).

`_table_issued.html` is a thin wrapper that picks the `issued` slot off the record and includes
`_date_value.html` under the `item_date` name the partial expects. The rule stays in one file. It
renders the empty-value marker when the record carries no issued date — `_date_value.html` emits
nothing at all for a slot with no `end`, no `begin` and no `literal`, and this column's
`empty_values=()` means the table's own marker is never reached (D-4).

### D-8 — Sorting by issued date is annotated, and NULLs are placed deliberately

`get_queryset()` annotates the issued slot's start date with a `Subquery` over `ItemDate` filtered
to `date_type="issued"` — not a join filter, which risks row multiplication and interferes with the
paginator's count (research R7).

`order_issued(queryset, is_descending)` returns `(queryset, True)`, applying `nulls_last=True` in
both directions. django-tables2 does nothing about NULLs on its own, and SQLite and PostgreSQL
disagree about where they land, so FR-018's "ordered consistently rather than dropped" has to be
stated in code or it is not true on one of the two databases this package supports.

### D-9 — `django_tables2` in `INSTALLED_APPS`, in three places

The component and the mvp table template both `{% load %}` the library, and Django finds
templatetag libraries only in installed apps. It goes into `tests/settings.py`, `demo/settings.py`,
and the README's installation block, which a host copies verbatim (research R11). Unconditional in
all three — the `ui` extra installs it, and a project installing the front end without its extra was
already broken.

`tests/test_ui/test_architecture.py` gains `django_tables2` in its forbidden-roots tuple, so the
core is provably free of it in the same way it is provably free of django-mvp.

### D-10 — Packaging, and the test that pins it

The `ui` extra becomes django-mvp plus django-tables2 `>=3.0,<4`, both under the existing
`python_version >= '3.12'` marker. The django-mvp floor is the release carrying the pagination fix
D-14 requires — `0.19` is the floor the rest of this feature needs, and the final number is settled
at T001 rather than guessed here. `tests/test_ui/test_packaging.py` asserts the extra's
contents as an exact list and moves in the same commit — the assertion is doing its job.
`deptry` needs no name mapping: `django-tables2` resolves to `django_tables2` on its own.

### D-11 — The card's readability tests move to the card's route

`TestCatalogueListReadability` is about a dozen assertions written against the card at the catalogue
route: the type badge, pluralised role headings, the abstract snippet and its truncation, the cite-key
label, `link-hover` on both links. All of them are about the card, and the card is not going away.

They are **re-pointed, not deleted and not loosened**: `tests/urls.py` gains a second route serving
`ItemListView`, and the class targets it. That is also the honest test of FR-022, because it
exercises the exact routing change the documentation tells a project to make. Weakening a passing
test to accommodate a change of default would discard the evidence that the card path still works,
at the moment the feature promises it does.

`TestItemListView`'s own assertions split the same way: the ones about the card's content follow it,
and the ones about list behaviour that both presentations owe (ordering, page size, the position
line, the out-of-range 404, the empty state, the create action, the query count) are asserted against
both, because they are now two promises rather than one.

### D-12 — The demo guard gains the two things a table row is for

`demo/smoke.py` already reaches a reference by following a link found on the catalogue page and
already finds an edit link on the reference page. US-5 adds: the row's own edit control, followed
from the list page rather than from the reference page. The item-link pattern keeps working
unchanged (research R4). The pagination literal does not: it pins `href="?page=2"`, and D-14's fix
makes that link carry the rest of the query string, so the guard's pattern has to match a page link
that is no longer bare. That is a repair, and T025 owns it.

### D-13 — The constitution amendment rides on this branch

Recorded here because it is part of this change and is declared in the pull request's description:
the stack constraint requiring a constitutional amendment before adopting a further front-end
package is removed, front-end additions move under Article VII, and the governance clause forbidding
amendment alongside feature work becomes a disclosure rule. Version 4.0.0. Rationale and the reasons
for both edits are in `decisions.md` D8. Sam's ruling at spec sign-off.

### D-14 — A sort has to survive a page change, and today the pagination link discards it

FR-016 and SC-004 require the chosen order to hold when the reader moves to the next page. Nothing in
the design delivered that, and the reason research R4 missed it is worth recording: R4 checked that
the pagination *markup* survives the change of presentation, and it does — precisely because the link
carries nothing to lose. `mvp/templates/cotton/pagination/link.html:16` emits
`href="?{{ page_param|default:"page" }}={{ page }}"`, which replaces the whole query string, so
`?sort=` is dropped on every page move. The table header does the opposite: the mvp table template
builds its sort links with django-tables2's `querystring_replace`, which preserves what is already
there. The two halves of the same page disagree.

**The fix belongs upstream, not here.** The href is hard-coded inside a shared component, and every
consuming project's table and filter view has the same defect — #49's filtering would hit it next.
`literature.ui` overriding the footer block would fork fifteen lines of someone else's markup to work
around a bug that is one line away from being fixed at its source. So: django-mvp's pagination
component preserves the current query string and replaces only the page key, that lands as its own
change in that repository, and the `ui` extra's floor rises to the release carrying it.

Two knock-ons, both stated so they are not discovered late:

- The `ui` floor named in D-10 and T001 is **not final** until that release exists. T001 raises it to
  the version that carries the fix.
- `demo/smoke.py:29` pins the exact literal `href="?page=2"`. A query-string-preserving link changes
  that literal, so D-12's "the existing walk keeps working unchanged" no longer holds for the
  pagination pattern, and T025 repairs it rather than confirming it.

## Complexity Tracking

No entries. Nothing in this plan deviates from the constitution.

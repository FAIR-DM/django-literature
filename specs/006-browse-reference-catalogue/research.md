# Research — 006 Browse the Reference Catalogue in an Opt-In Front End

Phase 0. Everything the plan rests on that was not already known, established by reading the
source rather than by assumption. Each finding names where it was read.

## R1 — What a project must do to render django-mvp components

django-mvp 0.17.0 is a django-cotton component library with a prebuilt stylesheet. A consuming
project needs, at minimum (`django-mvp/docs/getting-started.md`, cross-checked against the working
`django-mvp/demo/settings.py`):

- `INSTALLED_APPS`: `django.contrib.sites`, `django_cotton`, `easy_icons`, `flex_menu`, `mvp`,
  ~~`crispy_forms`, `crispy_tailwind`~~. `mvp` must precede `crispy_tailwind` where both are
  installed, because django-mvp ships a template override for a crispy-tailwind help-text template
  and app order decides which is found.
- The context processor `mvp.context_processors.mvp_config`, without which the app shell cannot
  resolve its layout configuration.
- ~~`CRISPY_ALLOWED_TEMPLATE_PACKS = ["tailwind"]` and `CRISPY_TEMPLATE_PACK = "tailwind"`.~~
- `django.contrib.staticfiles` with the app-directories finder, so the packaged stylesheet is found.
- `SITE_ID`, and `django.contrib.sites.middleware.CurrentSiteMiddleware` if the page-title suffix
  `mvp/base.html` renders from `{{ request.site.name }}` is to be non-empty.

**The crispy entries are struck out — D-1 removed their only caller.** They were justified below by
`list_view.html` loading `crispy_forms_tags`, and D-1 rules that nothing in this app references
`list_view.html`. In django-mvp, `crispy` appears in `list_view.html`, `cotton/form/render.html`,
`cotton/form/formset/row.html` and `tailwind/layout/help_text.html`, none of which is in the
`mvp/base.html` → `<c-app>` → `<c-page.*>` / `<c-pagination>` / `<c-data-field>` chain this app uses;
cotton resolves components lazily at render time, so an unreferenced component costs nothing. Two
fewer apps and two fewer settings in the host contract T023 documents.

They still arrive transitively as *packages*, just not as installed apps — django-mvp's
own `[project].dependencies` are `django>=5.2`, `django-cotton==2.6.1`, `django-flex-menus>=0.4.3`,
`django-easy-icons>=0.6`, `mergedeep`, `django-crispy-forms>=2.7`, `crispy-tailwind>=1.0.3`
(`django-mvp/pyproject.toml`). **Depending on `django-mvp` alone pulls the whole set**, so the
optional extra needs one entry, not seven.

**Consequence for FR-011 and the package floor.** django-mvp requires Django ≥ 5.2 and
`requires-python >=3.12`, while django-literature's core declares `django>=4.2` and supports 3.11.
The extra therefore narrows what a project installing it can run on; the core's own floor is
untouched. This is stated in the plan rather than resolved, because narrowing the core's floor to
match would break core-only consumers for the benefit of a feature they did not install.

## R2 — The `base.html` trap

`mvp/templates/page_view.html` — the template every packaged `MVP*View` falls back to — begins
`{% extends "base.html" %}`, an unqualified project-level name, not `mvp/base.html`. django-mvp's
own demo satisfies it with `demo/templates/base.html` containing `{% extends "mvp/base.html" %}`,
and the getting-started guide tells consumers to write one.

A package cannot rely on that. If `literature.ui`'s pages inherited the packaged `list_view.html` /
`detail_view.html` chain, a host that has not written its own `base.html` would get
`TemplateDoesNotExist` on every page, which fails FR-004 outright. A package shipping its own
top-level `base.html` is worse: it would silently become the fallback shell for the *host's* pages.

**Resolution**: `literature.ui` ships one namespaced base template,
`literature/ui/templates/literature/ui/base.html`, which extends `mvp/base.html` directly and
recomposes the page chrome from published components (`<c-container>`, `<c-page.content>`,
`<c-page.title>`, `<c-breadcrumbs>`). Every page template in the app extends that. Nothing in the
app extends `base.html`, `list_view.html`, or `detail_view.html`.

This also satisfies FR-010 rather than compromising it: the app deliberately does not inherit a
host's shell, which is exactly the stated trade — a UI complete on its own terms.

## R3 — What the packaged components do and do not cover

Read from `django-mvp/mvp/templates/cotton/`, with parameters taken from each component's
`<c-vars>` line.

Covered outright:

- `<c-pagination :page_obj="page_obj" />` (`cotton/pagination/index.html`, vars
  `label page_obj page_window="5" use_icons show_first_and_last`) — the whole pagination control,
  including first/last and a numbered window. Nothing about paging needs writing.
- `<c-data-field label= value= help_text= missing="–" />` (`cotton/data_field.html`) — a labelled
  value with a fallback dash, which is the reference page's scalar-field unit.
- `<c-section title= icon= level="2" actions= />`, `<c-grid>`, `<c-container>`, `<c-card>`,
  `<c-badge>`, `<c-link>`, `<c-page.title>`, `<c-breadcrumbs>` — headings, grouping, chrome.
- `<c-page.list.empty icon= heading= message= />` — the empty state.

Not covered, and hand-written as ordinary Django partials composing the above:

- **Per-row markup.** The packaged list renders each object through `render_list_item`, a template
  tag pointed at a plain partial (`<app_label>/<model_name>_list_item.html`). There is no row or
  table-row component. This is by design, not a gap to file upstream.
- **The detail body.** `django-mvp/docs/adr/0001-detail-views-do-not-take-a-field-list.md` states
  that `MVPDetailView` renders no field markup deliberately and that the empty body "is the finished
  behaviour, not a placeholder". Composing `<c-data-field>` into a layout is the consumer's job.
- **A list of names.** Nothing renders a set of contributor names as text. Joining them is a `for`
  loop in a partial.

**No component gap qualifies for an upstream request.** Every absence above is a documented
extension point, not a missing component, so FR-009's escalation path stays unused and the
specification's *Component gaps* section stays empty. If that changes mid-implementation the
requirement's process applies unchanged.

## R4 — Staying in Tier 1 (no stylesheet)

`django-mvp/docs/styling.md` defines two tiers. Tier 1 uses the prebuilt
`mvp/static/css/django-mvp.css` and requires no build step, on the condition that templates use only
packaged components and the utility classes listed in `django-mvp/docs/utility-classes.md`. Reaching
for a utility outside that list, or an arbitrary value such as `w-[37px]`, silently produces
unstyled markup and forces Tier 2 — a Tailwind build, which means shipping a stylesheet and
breaking FR-008.

The allowlist is generous: display, flex, grid, gap, padding, margin, width/height, text size and
alignment, borders, radius, font weight, truncation, and daisyUI's semantic colour names as
`bg-`/`text-`/`border-` utilities.

**Two traps recorded because django-accounts-center hit them.** Colour utilities ship base-only with
no opacity modifiers, so `text-base-content/60` — which dac uses — is *not* in the allowlist. And
responsive variants exist only at `md:`, `lg:`, `xl:`. Anything else is Tier 2 by accident.

**Rule for this feature**: only classes named in `utility-classes.md`, no arbitrary values, no
opacity modifiers, no `sm:` or `2xl:` prefixes. This is checkable, and T-VERIFY-CSS makes it a test.

## R5 — The precedent, and how far it actually goes

django-accounts-center (`/home/sam/projects/django-mvp/django-accounts-center`) is the family's
composition precedent and its constitution Article XVII states the rule this feature inherited. Read
in full, it is a weaker precedent than expected for the view layer: dac defines exactly one view
(`AccountCenterView`, an `MVPTemplateView` subclass) and serves every other page through
django-allauth's own views with overridden templates. It has no list or detail views at all.

What it does establish and this feature copies:

- `[project.optional-dependencies]` keyed by sub-app name, in PEP 508 parenthesised form
  (`"django-mvp (>=0.17,<1.0)"`), which is this family's declaration style.
- A sub-app with its own `AppConfig` and an explicit `label`, its URLs included from the parent
  package's `urls.py` behind an `app_is_installed` check.
- `tests/test_architecture.py` as a real, enforced boundary test — the shape US-3 needs.
- Composition through `<c-card>`, `<c-badge>`, `<c-button>`, named `<c-slot>`s, and nothing local.

Where dac departs from the rule, and why this feature does not follow it: dac ships a built
`dac/static/css/dac.css` and one local cotton component. The stylesheet is a Tailwind build carrying
exactly two hand-written rules, both labelled with the upstream issue they wait on
(django-mvp#124, #125). This feature ships neither, because it has no Tier 2 need — see R4.

## R6 — The model surface the pages query

From `literature/models.py`, read for exact names rather than recalled:

| Traversal | Accessor |
|---|---|
| An item's contributors | `item.item_names` → `ItemName.name`, `.role`, `.order` |
| An item's dates | `item.item_dates` → `ItemDate.date_type`, `.begin`, `.end`, `.literal`, `.raw` |
| An item's identifiers | `item.item_identifiers` → `ItemIdentifier.type`, `.value` |
| A contributor's credits | `name.item_names` → `ItemName.item`, `.role` |

`ItemName` declares `related_name="item_names"` on **both** its foreign keys, so the same accessor
name works from either side. `ItemName.Meta.ordering = ["item", "role", "order"]`, and `order` is
assigned per `(item, role)` in `save()` (ADR-0005), which is exactly the grouping FR-022 asks for —
the reference page needs no ordering logic of its own.

`Item.Meta.ordering = ["-created"]` is the declared default FR-015 adopts. `Name` declares no
ordering, which matters for the contributor page: its item list orders by the *item's* `-created`,
not by anything on `Name`.

Indexes already present and load-bearing here: `ItemName` on `["name", "role"]` (the contributor
page's filter) and on `["item", "role", "order"]` (the reference page's grouping); `Item` on `type`,
`citation_key`, `title`.

**Iterating an item's non-empty scalar fields.** No helper exists. The idiom is written out three
times already (`literature/converters.py`, `tests/test_converters.py`, `tests/test_documentation.py`)
as `for field in item._meta.get_fields()` with `hasattr(field, "attname")` distinguishing concrete
scalars from relations, then a per-caller skip set. This feature extracts it once into
`literature/utils/fields.py` and uses it from the UI. It does **not** rewrite the three existing
callers: that is a refactor of working code outside this feature's scope, and touching
`converters.py` would put the run into the tamper guard for no requirement.

`verbose_name` is present and translated on every field, so FR-020's "human-readable label" is
`field.verbose_name` and needs nothing invented.

## R7 — Test surface

`tests/settings.py` installs the core only, `tests/urls.py` is `urlpatterns = []`, and the suite has
**no HTTP-layer test of any kind** — no `client` fixture use anywhere. This feature writes the
repo's first view tests. `pytest-django` is already available transitively, and `tests/factories.py`
already carries a factory per model with `SubFactory` wiring, so fixtures cost nothing new.

The suite runs under one `DJANGO_SETTINGS_MODULE`. Adding the UI apps to `tests/settings.py` is
therefore the only way UI tests run at all — which removes "the existing suite runs with the app
absent" as a *literal* reading of SC-009. See D-4 in the plan for how US-3 is proved instead.

`ruff` runs at `line-length = 120` in this repo (an explicit local override), `mypy` covers
`literature/` with the Django plugin and `disable_error_code = ["django-manager-missing"]`, which is
what keeps reverse accessors like `item.item_names` from erroring. `deptry` runs in CI and will see
a new optional dependency — the extra must be declared correctly or it fails the build job.

There is no `makemessages` gate in this repo, despite the org note suggesting otherwise; i18n is
enforced by convention only. FR-007 is therefore verified by review and by a test asserting the
templates' strings are wrapped, not by CI.

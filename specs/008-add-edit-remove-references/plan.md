# Implementation Plan: Add, Edit and Remove References Through the Front End

**Branch**: `008-add-edit-remove-references` | **Date**: 2026-08-13 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `specs/008-add-edit-remove-references/spec.md`

## Summary

Three write flows join the opt-in front end, over a reference's own scalar record: create, update and
delete. All of it lives in `literature/ui/`, composed from django-mvp's `MVPCreateView`,
`MVPUpdateView` and `MVPDeleteView`, which already carry the form page, the delete confirmation, the
success messages and the breadcrumb machinery.

The one piece with real design content is the type scoping. `Item` declares 64 fields, 60 of which
reach the form, and CSL publishes no
mapping from item type to applicable fields, so the package authors one. It is authored at the level
of **field groups rather than individual fields** — around a dozen named groups, each type declaring
which groups it uses — which turns a 45×70 matrix of contestable cells into 45 short lists, matches
how `models.py` already organises its fields, and matches the unit the interface shows and hides.

Scoping is entirely a matter of visibility. One `ModelForm` carries every scalar field, every field
is rendered into the page and posted back, and Alpine hides the groups the chosen type does not use.
Nothing is filtered server-side, so a hidden field submits the value it already held and no stored
value can be lost by changing a type — FR-004a, FR-011 and FR-014 are satisfied structurally rather
than by a rule someone has to remember.

## Technical Context

**Language/Version**: Python 3.12+ (package floor), Django 5.2 / 6.0

**Primary Dependencies**: django-mvp `>=0.17,<1.0`, locked at **0.17.0** — plan against 0.17.0, not
the 0.18.0 working copy on this machine. Brings django-cotton, crispy-forms + crispy-tailwind,
easy-icons, flex-menu, Alpine.js. **No new runtime dependency.**

**Storage**: PostgreSQL/SQLite through the existing models. **No schema change, no migration.**

**Testing**: pytest + pytest-django, `DJANGO_SETTINGS_MODULE=tests.settings`, factory-boy factories in
`tests/factories.py`. This feature adds the repository's first POST tests.

**Target Platform**: a Django host project installing the `ui` extra

**Project Type**: reusable Django package with an opt-in front-end app

**Constraints**: no custom components, no custom CSS (FR-026) · no core dependency on the front end,
enforced by `tests/test_ui/test_architecture.py` · every user-facing string translatable (Article
VIII) · pages open, no auth (FR-024)

**Scale/Scope**: 45 item types, 64 declared `Item` fields (60 on the form), 4 user stories

## Constitution Check

| Article | Bearing | Verdict |
|---|---|---|
| I Test-First | Every task is a failing test first; the type-group mapping gets a test that fails on an unmapped type | Pass |
| II Simplicity / III Anti-Abstraction | One form class, one mapping module, three views. No form factory, no per-type form subclass, no registry | Pass |
| IV Integration-First | The demo guard walks the real flows over the real project (US-4) | Pass |
| V Security & data-safety | No hand-built interpolation; values render through the template layer. Data safety is the central concern and is answered structurally — see D-3 | Pass |
| VI Documentation | README gains the write flows and the mapping's rationale; CHANGELOG entry | Pass |
| VII Dependency discipline | No new runtime dependency; `deptry` unchanged | Pass |
| VIII i18n | Every form label, help text, page title, success message and template string wrapped. Group labels too — they are user-visible headings | Pass, watch item |
| IX CSL lingua franca | The mapping is a presentation artefact and changes no field name or structure. Its basis is recorded per type | Pass |
| X Embeddable | URLs stay namespaced and optional; no host-project structural change | Pass |
| XI Data integrity | No migration. The no-loss guarantee is D-3, tested by SC-003's round trip | Pass |
| XII Living demo | US-4 extends the demo and its guard in this PR | Pass |
| XIII Data-model conventions | No model field added or changed, so no indexing decision arises | N/A |
| XIV Test structure | One test module per source module, classes per story, factories reused | Pass |
| XV Cohesion | The mapping's helpers share a subject and go on a class rather than loose module functions | Pass |

No entry in Complexity Tracking: nothing here needs a deviation.

## Design decisions

### D-1 — The mapping is authored at group level, not field level

45 types × ~70 fields is 3,000 cells of editorial judgement that nothing published can support.
Appendix III names variables for only 14 of the 45 types and names nine distinct variables in total
(`research.md` §1). Authoring that matrix by hand would be mostly invention wearing a citation.

Instead, fields are gathered into named groups, and each type declares the groups it uses. Groups are
taken from how `models.py` already organises `Item`, which is itself CSL's own grouping:

| Group | Fields |
|---|---|
| `core` *(always shown)* | `type`, `citation_key`, `title`, `abstract` |
| `general` *(always shown)* | `note`, `annote`, `keyword`, `language`, `status`, `source`, `call_number` |
| `titles` | `title_short`, `original_title`, `part_title`, `volume_title`, `volume_title_short` |
| `container` | `container_title`, `container_title_short`, `journal_abbreviation`, `collection_title`, `collection_number` |
| `publication` | `publisher`, `publisher_place`, `edition`, `medium`, `genre`, `version` |
| `original` | `original_publisher`, `original_publisher_place` |
| `numbering` | `volume`, `issue`, `page`, `page_first`, `number`, `number_of_pages`, `number_of_volumes`, `chapter_number`, `section`, `part`, `supplement`, `printing` |
| `event` | `event_title`, `event_place` |
| `review` | `reviewed_title`, `reviewed_genre` |
| `legal` | `authority`, `jurisdiction`, `division`, `references` |
| `archive` | `archive`, `archive_collection`, `archive_location`, `archive_place` |
| `physical` | `dimensions`, `scale` |
| `processor` *(never offered by default)* | `citation_label`, `citation_number`, `first_reference_note_number`, `locator`, `year_suffix` |

`core` and `general` apply to every type. `processor` applies to none — a CSL processor assigns those
values and no person enters them — but it stays reachable like everything else. `categories` and
`custom` are not in any group because they are not on the form at all (D-4).

Every field of `Item` except `categories`, `custom`, `created` and `modified` belongs to exactly one
group. A test asserts that partition, so a field added to the model later cannot silently vanish from
the form.

**Assignment criteria**, applied per type in the order given, so the work is a task with stated rules
rather than a judgement call inside a code review:

1. A group Appendix III names for that type is used (`container` for book, broadcast,
   motion_picture, report, song, webpage; `publication` for the `medium` and `genre` statements).
2. A group whose fields Appendix IV defines in terms of that type is used. **Apply this against the
   full list of type-bound variable definitions in `research.md` §1 — the examples here are
   illustrations, not the whole set.** The ones that carry the most weight: `container-title`'s own
   definition names "the book title for a book chapter, the journal title for a journal article, the
   album title for a recording, the session title for multi-part presentation at a conference", which
   is C2 evidence for `container` on chapter, article-journal, song and speech on the strength of
   that one sentence; `version` names software; `section` names legislation and article-newspaper;
   `chapter-number` names chapter and song; `issue` names the serial types; `number-of-volumes` and
   `ISBN` name the book-like types; `scale` names map; `authority`, `jurisdiction` and `division`
   name patent and the legal types; the `archive*` variables name the archival types. The cluster
   assignments follow from the same reading: `legal` for legal_case, legislation, bill, hearing,
   regulation and treaty; `review` for review and review-book; `event` for event, speech,
   paper-conference and performance; `physical` for map.
2a. **A type that sits inside a container takes `container`, not `numbering` alone.** Recording
   where an item appeared is what the container group is for, and a form offering a page range
   without the name of the thing the pages are in is not a usable form. This is the correction the
   first pass at this mapping needed: it gave the journal article, the chapter, the dictionary entry,
   the conference paper and the review their pagination and left out the journal, the book, the
   reference work, the proceedings and the periodical.
3. `archive` is used by the types whose subject is a held object — collection, manuscript, classic,
   pamphlet, figure, graphic, personal_communication.
4. `numbering` is used where the type is or sits inside a numbered sequence.
5. `original` is used where republication or translation is ordinary for the type.
6. Otherwise the group is not used. Absence is the default, and the point is a short form.

Each type's entry carries a one-line note naming which criterion decided it. Set sizes get a
plausibility check against Zotero's counts (`research.md` §1: median 24 CSL variables per type,
range 16–35) — not a source to copy, and 13 types it does not cover at all.

**ADR:** to be decided at S5 against the ADR bar. This is durable, cross-cutting and non-obvious, so
it very likely graduates.

### D-2 — The mapping is data in one module, not behaviour spread across views

`literature/ui/fieldgroups.py` holds the group definitions and the per-type assignments as plain
data, plus one class carrying the lookups (`groups_for(item_type)`, `fields_for(group)`,
`groups_holding_values(item)`). Article XV puts those on a class because they share a subject;
Article III forbids making it a registry, a plugin point or a settings-overridable table. It is a
constant and a few functions.

It sits in `literature/ui/` and not in the core, because `tests/test_ui/test_architecture.py` forbids
the core importing anything the front end needs, and because a presentation mapping is not store
knowledge.

### D-3 — Scoping is visibility only. Every field is rendered and posted, always

One `ItemForm(ModelForm)` with every scalar field. The template renders every group. Alpine hides
the groups the current type does not use:

- The `type` widget carries `x-model="form.itemType"` **and `x-init="form.itemType = $el.value"`** in
  its `attrs`. `cotton/form/index.html` opens a literal `x-data="{form: {}}"` on the `<form>` element
  — an empty object in a django-mvp file this feature does not write, so there is no seam to seed the
  state from `self.object.type`. Without `x-init`, `x-model` writes its own undefined state onto the
  select at initialisation and deselects the stored item type, which then fails validation on save
  because `type` is required. The `x-init` reads the server-rendered value back into the scope. No
  second `x-data` is declared.
- Each group's wrapper carries
  `x-show="showAll || forcedGroups.includes(group) || (typeGroups[form.itemType] || []).includes(group)"`,
  driven by a JSON map of type → groups rendered once into the page. The `|| []` is load-bearing: on
  a blank create page `form.itemType` is the empty string and a bare lookup would throw inside every
  group's expression.
- **With no item type chosen, nothing but the type field renders.** Choosing one reveals `core`,
  `general` and that type's groups. This is FR-002 — the type is asked before anything else — and it
  falls out of the same guard rather than needing a second page.
- A "Show every field" toggle sets `showAll`.
- Groups already holding a value are forced visible from the server via
  `groups_holding_values(item)`, which is what FR-010 and FR-014 ask for.
- **`item_form.html` overrides `form_view.html`'s `{% block actions %}`** with a single translated
  Save button. django-mvp's default block renders submit buttons carrying `default_next=list`, and
  `NextURLMixin` consults `default_next` *before* `success_url` — so with the stock block every save
  through the rendered page would land on the catalogue rather than the reference, silently breaking
  FR-008 and FR-015. A test posting a bare field dict would not catch it, because only the rendered
  button sends that parameter.

**Why this shape and not per-type form classes:** a hidden input still holds its value and still
posts it — Alpine's `x-show` sets `style.display` and leaves the element in the DOM. A field the
mapping does not offer therefore round-trips untouched, and changing an item type cannot discard
anything, because the server never sees a narrower form. The alternative — building the form's field
list from the type — makes every omitted field submit as absent, and Django's `construct_instance()`
assigns every declared field from `cleaned_data`, so an absent field is written as empty rather than
left alone.

**The limit of the guarantee, stated honestly:** it is structural *for the rendered page*, not for
the endpoint. Any POST that omits a field still blanks it, for exactly that `construct_instance`
reason. That is why the demo guard has to post the whole form back with one field changed (D-9)
rather than posting the field it means to change.

The cost is honest: every form page carries all 60 fields' markup. For a form nobody submits at
volume, that is the right trade.

### D-4 — `categories` and `custom` are excluded at the form, and the exclusion is tested

`ItemForm.Meta.fields` enumerates the scalar fields and omits `categories`, `custom`, `created` and
`modified`. `ModelForm.save()` only assigns the fields it declares, so both JSON fields survive
untouched by construction. FR-013 is nonetheless written as preservation, so the test asserts the
stored values before and after a save rather than asserting the form's field list.

### D-5 — `CRISPY_TEMPLATE_PACK` is unset in this repository, and this feature is where that starts mattering

`crispy_tailwind` is installed in both `tests/settings.py` and `demo/settings.py`, but neither sets
`CRISPY_TEMPLATE_PACK`. crispy-forms 2.7's `get_template_pack()` is
`getattr(settings, "CRISPY_TEMPLATE_PACK")` **with no default**, so the current state is an
`AttributeError` on the first form render, not a silent fallback to another pack. Nothing has noticed
because the package renders no form today. Both settings modules gain
`CRISPY_TEMPLATE_PACK = "tailwind"`, and the README gains it in the install instructions, since a
host copying those instructions hits the same latent defect. A rendered-page test asserts the
tailwind pack's markup rather than the setting's value.

**`CRISPY_ALLOWED_TEMPLATE_PACKS` has to be set too, and an earlier version of this paragraph said
otherwise.** It claimed the allowlist is only consulted when the `{% crispy %}` tag is given an
explicit pack argument. That is wrong, and US-3 proved it by reproduction: the tag validates the
resolved pack against the allowlist **at template-compile time**, whose default is
`("uni_form", "bootstrap3", "bootstrap4")`, so *any* template carrying the tag fails to compile
under `tailwind` — regardless of the tag's arguments and regardless of which branch runs. It went
unnoticed through US-1 and US-2 because `item_form.html` deliberately bypasses
`cotton/form/render.html` entirely; the delete page, which renders django-mvp's own confirmation
template unmodified, is the first thing to reach it. django-mvp's own demo sets both settings
together, which is the corroboration this paragraph should have had the first time. Both settings
modules set both values.

**This reverses a recorded FS-006 decision and amends one of its tests, deliberately.** FS-006 struck
both crispy settings and its `tests/test_ui/test_smoke.py` asserted each was absent. That was
correct while nothing rendered a form and is wrong the moment something does. Constitution Article I
requires a recorded decision before a pre-existing test is changed: this paragraph is it. Both
assertions are dropped rather than flipped, because `T013` already asserts the tailwind pack's markup
actually renders, which is the claim worth testing.

### D-6 — One shared `CRUD_VIEWS` map, and every action needs its `show_*_action` flag

django-mvp resolves action URLs through a `crud_views` dict defaulting to unnamespaced names, and
under `app_name = "literature"` a plain `reverse("item-list")` raises `NoReverseMatch`. The
established pattern in `views.py` spreads the shared default and overrides two keys, which leaves the
other three unreversible. Rather than repeating a partial override on five views, `views.py` gains
one module-level `CRUD_VIEWS` mapping all five actions under the `literature:` namespace, assigned on
`ItemListView`, `ItemDetailView` and the three new views. That makes "every name in every view's
`crud_views` reverses" a literally true assertion instead of one the partial overrides would fail.

**`directory` alone shows nothing.** `CRUDDirectoryMixin` defaults every `show_<action>_action` to
`False`, and `resolve_crud_url()` returns `None` before reversing when the flag is falsy, so
`get_directory()` drops the entry. A view listing an action in `directory` without setting its flag
renders no button at all. The repository already knows this — `views.py` sets `show_list_action =
True` with a comment saying the default leaves it href-less — but the flag has to be set on each view
for each action it shows:

| View | `directory` | flags |
|---|---|---|
| `ItemListView` | `["create"]` | `show_create_action` |
| `ItemDetailView` | `["update", "delete"]` | `show_update_action`, `show_delete_action` |
| `ItemCreateView` | — | `show_list_action`, `show_detail_action` |
| `ItemUpdateView` | — | `show_list_action`, `show_detail_action` |
| `ItemDeleteView` | — | `show_list_action`, `show_detail_action` |

The form views need `list` and `detail` resolvable because `get_breadcrumbs()` reverses them, and an
action that is *shown* with no resolvable route raises `NoReverseMatch` there — an uncaught 500 on
the form page rather than a missing button. A test reverses every name in every view's `crud_views`.

`Item` has no `get_absolute_url()`, so `success_url` is mandatory on the create and update views;
both use the `detail` CRUD shorthand, and the delete view uses `list`. **The shorthand only resolves
when its flag is set** — `get_success_url()` falls through to returning the raw string, so
`success_url = "detail"` with `show_detail_action` unset redirects to the literal relative path
`detail` and 404s.

### D-7 — The delete confirmation is django-mvp's, configured rather than written

`MVPDeleteView` with `show_related_objects = True` renders the warning, names the object and lists
the related records that go with it, which is exactly FR-017 and FR-019 and lets a person see the
contributor links, dates and identifiers before confirming. `require_confirmation` stays off — typing
a value to confirm is friction this feature has no case for, and FR-017 asks only that the page name
the reference.

`Name` records are untouched by the cascade because nothing points from `Item` to `Name` directly;
the `ItemName` rows are what cascade. FR-020 is therefore already true of the model, and the test
asserts it rather than the code implementing it.

**Declining has to be pointed back at the reference.** `MVPDeleteView.get_back_url()` reads `?back`
from the query string and otherwise falls back to the catalogue list, and the detail page's delete
link carries no `?back` — only the *update* page's does. FR-018 requires returning to the reference,
so `ItemDeleteView` overrides `get_back_url()` to resolve the `detail` shorthand, honouring an
inherited `?back` first. The object still exists at that point, so its URL is available.

### D-8 — Entry points, and where each flow lands

- Catalogue page: an "Add" action, from `directory = ["create"]` **with `show_create_action = True`**.
  The list view's `create_form_class` stays unset, so the component renders a plain link to the
  create page rather than a modal — a thirteen-group form does not belong in a modal.
- Reference page: Edit and Delete, from `directory = ["update", "delete"]` **with
  `show_update_action` and `show_delete_action` set**.
- Create and update land on the reference's page (`success_url = "detail"`); delete lands on the
  catalogue (`success_url = "list"`). Both depend on the flags in D-6's table and on `item_form.html`
  overriding the default actions block (D-3).

### D-9 — The demo guard walks the flows over the demo's own project

`demo/smoke.py` already walks pages by following links. It gains a write pass: create a reference,
follow to its page, edit a field, confirm the change renders, delete it, confirm the catalogue no
longer lists it. It runs against the demo project's own settings and URLs, as FS-007 settled, so a
demo that has drifted from the package is caught there and not only in the suite.

Two mechanics the existing walk does not have and the write pass needs. It reads pages with a bare
`urllib.request.urlopen`, with no cookie jar and no CSRF token, and the demo runs
`CsrfViewMiddleware` — so a POST as the module stands today returns 403. And per D-3's stated limit,
each POST must carry the whole form back with one field changed, built by parsing the rendered form's
field names rather than assembled by hand; posting only the changed field would blank the rest. Both
stay inside the module's standard-library-only constraint.

Proving the guard works means breaking each flow in turn and confirming the guard fails — the same
method FS-007 used for its own guard (its D-8).

### D-10 — Tests are the first POST tests in the repository

No fixture, helper or pattern for posting exists in `tests/`. Each story's tests use pytest-django's
`client` with `client.post`, the existing factories, and assertions against the database rather than
the response body where the claim is about storage. No auth fixture is introduced, because there is
no auth (FR-024).

## Project Structure

### Documentation (this feature)

```
specs/008-add-edit-remove-references/
├── spec.md
├── decisions.md
├── research.md
├── plan.md            # this file
├── tasks.md
├── progress.md
└── feature-state.json
```

### Source code (repository root)

```
literature/ui/
├── fieldgroups.py          # NEW — group definitions, per-type assignments, lookups (D-1, D-2)
├── forms.py                # NEW — ItemForm (D-3, D-4)
├── views.py                # ItemCreateView, ItemUpdateView, ItemDeleteView; crud_views on existing views (D-6, D-8)
├── urls.py                 # item-create, item-update, item-delete
└── templates/literature/ui/
    └── item_form.html      # NEW — grouped form page over form_view.html's blocks (D-3)

demo/
├── settings.py             # CRISPY_TEMPLATE_PACK (D-5)
└── smoke.py                # write pass (D-9)

tests/
├── settings.py             # CRISPY_TEMPLATE_PACK (D-5)
└── test_ui/
    ├── test_fieldgroups.py # NEW — partition, per-type assignment, lookups
    ├── test_forms.py       # NEW — field list, exclusions, validation
    ├── test_views.py       # create/update/delete view classes
    └── test_urls.py        # route names, crud_views reversal
tests/test_demo/
    └── test_smoke.py       # the write pass, and that breaking a flow fails it
```

**Structure Decision**: everything new lives in `literature/ui/`. The core gains nothing, which
`tests/test_ui/test_architecture.py` already enforces.

## Phases

**Phase 0 — Foundational (sequential, before any story).** `fieldgroups.py` with its groups, the
45-type assignment against D-1's criteria, and its tests. `ItemForm`. `CRISPY_TEMPLATE_PACK` in both
settings modules. This is the shared spine every story sits on, and the type assignment is the single
largest piece of judgement in the feature.

**Phase 1 — US-1 (P1)** create view, URL, `item_form.html` with the grouped layout and the Alpine
scoping, catalogue entry point, tests.

**Phase 2 — US-2 (P2)** update view reusing the same form and template, detail-page entry point,
forced visibility for populated groups, the no-loss round-trip test.

**Phase 3 — US-3 (P3)** delete view, related-objects confirmation, cascade and contributor-survival
tests.

**Phase 4 — US-4 (P4)** demo wiring and the smoke write pass, proven by breaking each flow.

Stories 1–3 share `item_form.html` and `ItemForm`, so they run sequentially rather than fanned out.

## Complexity Tracking

No deviations. Nothing here adds an abstraction the constitution would question: one form, one
mapping module, three views composed from the toolkit, and a template.

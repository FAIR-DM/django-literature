# Implementation Plan: Add, Edit and Remove References Through the Front End

**Branch**: `008-add-edit-remove-references` | **Date**: 2026-08-13 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `specs/008-add-edit-remove-references/spec.md`

## Summary

Three write flows join the opt-in front end, over a reference's own scalar record: create, update and
delete. All of it lives in `literature/ui/`, composed from django-mvp's `MVPCreateView`,
`MVPUpdateView` and `MVPDeleteView`, which already carry the form page, the delete confirmation, the
success messages and the breadcrumb machinery.

The one piece with real design content is the type scoping. `Item` has 89 fields and CSL publishes no
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

**Scale/Scope**: 45 item types, 89 model fields, 4 user stories

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
2. A group whose fields Appendix IV defines in terms of that type is used (`legal` for legal_case,
   legislation, bill, hearing, regulation, treaty; `review` for review and review-book; `event` for
   event, speech, paper-conference, performance; `physical` for map).
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

- The `type` widget carries `x-model="form.itemType"` in its `attrs` — `cotton/form/index.html`
  already opens `x-data="{form: {}}"` on the `<form>` element, so no extra scope is declared.
- Each group's wrapper carries `x-show="showAll || groups.includes(form.itemType) || forced"`, driven
  by a JSON map of type → groups rendered once into the page.
- A "Show every field" toggle sets `showAll`.
- Groups already holding a value are forced visible from the server via
  `groups_holding_values(item)`, which is what FR-010 and FR-014 ask for.

**Why this shape and not per-type form classes:** a hidden input still holds its value and still
posts it. A field the mapping does not offer therefore round-trips untouched, and changing an item
type cannot discard anything, because the server never sees a narrower form. The alternative —
building the form's field list from the type — makes every omitted field submit as absent, and on a
`ModelForm` that means the value is left alone only by accident of `save()`'s field list. Making the
guarantee structural is worth more than the smaller HTML payload, and SC-003's round trip is the test
that proves it.

The cost is honest: every form page carries all 89 fields' markup. For a form nobody submits at
volume, that is the right trade.

### D-4 — `categories` and `custom` are excluded at the form, and the exclusion is tested

`ItemForm.Meta.fields` enumerates the scalar fields and omits `categories`, `custom`, `created` and
`modified`. `ModelForm.save()` only assigns the fields it declares, so both JSON fields survive
untouched by construction. FR-013 is nonetheless written as preservation, so the test asserts the
stored values before and after a save rather than asserting the form's field list.

### D-5 — `CRISPY_TEMPLATE_PACK` is unset in this repository, and this feature is where that starts mattering

`crispy_tailwind` is installed in both `tests/settings.py` and `demo/settings.py`, but neither sets
`CRISPY_TEMPLATE_PACK`, so crispy falls back to `bootstrap4`. Nothing has noticed because the package
renders no form today. Both settings modules gain `CRISPY_TEMPLATE_PACK = "tailwind"`, and the README
gains it in the install instructions, since a host copying those instructions hits the same latent
defect. A rendered-page test asserts the tailwind pack's markup rather than the setting's value.

### D-6 — `crud_views` is remapped on every view that shows an action, not only the new ones

django-mvp resolves action URLs through a `crud_views` dict defaulting to unnamespaced names.
`ItemDetailView` already overrides it for `list` and `detail` and sets `directory = []`. Showing the
new actions means extending that dict with `create`, `update` and `delete` under the `literature:`
namespace on the list view, the detail view and each new view, and setting `directory` accordingly.

The failure mode is specific and worth naming in the task: an action that is *shown* with no
resolvable route raises `NoReverseMatch`, and inside `get_breadcrumbs()` that is an uncaught 500 on
the form page rather than a missing button. A test reverses every name in every view's `crud_views`.

`Item` has no `get_absolute_url()`, so `success_url` is mandatory on the create and update views;
both use the `detail` CRUD shorthand, and the delete view uses `list`.

### D-7 — The delete confirmation is django-mvp's, configured rather than written

`MVPDeleteView` with `show_related_objects = True` renders the warning, names the object and lists
the related records that go with it, which is exactly FR-017 and FR-019 and lets a person see the
contributor links, dates and identifiers before confirming. `require_confirmation` stays off — typing
a value to confirm is friction this feature has no case for, and FR-017 asks only that the page name
the reference.

`Name` records are untouched by the cascade because nothing points from `Item` to `Name` directly;
the `ItemName` rows are what cascade. FR-020 is therefore already true of the model, and the test
asserts it rather than the code implementing it.

### D-8 — Entry points, and where each flow lands

- Catalogue page: an "Add" action, from `directory = ["create"]`. The list view's `create_form_class`
  stays unset, so the component renders a plain link to the create page rather than a modal — an
  89-field form does not belong in a modal.
- Reference page: Edit and Delete, from `directory = ["update", "delete"]`.
- Create and update land on the reference's page (`success_url = "detail"`); delete lands on the
  catalogue (`success_url = "list"`).

### D-9 — The demo guard walks the flows over the demo's own project

`demo/smoke.py` already walks pages by following links. It gains a write pass: create a reference,
follow to its page, edit a field, confirm the change renders, delete it, confirm the catalogue no
longer lists it. It runs against the demo project's own settings and URLs, as FS-007 settled, so a
demo that has drifted from the package is caught there and not only in the suite.

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

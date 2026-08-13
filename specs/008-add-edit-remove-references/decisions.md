# Decisions — 008 Add, edit and remove references through the front end

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without escalating. The
spec stands alone; this file explains why it says what it says.

## D1 — The type-to-field mapping is authored here, not derived

**Ambiguous:** the intake session settled that the form is scoped to the fields that apply to the
chosen item type. It did not say where the package learns which fields those are.

**Chosen:** the package authors the mapping itself, carries it as one readable artefact covering
all forty-five types, and states what each type's set was decided from.

**Why defensible:** there is nothing to derive from. Checked directly rather than assumed:

- `csl-data.json` (v1.0.2, MIT) declares 103 properties flat under `items.properties`, with
  `type` as a plain enumerated string. There is no `if`/`then`, `allOf`, `oneOf`, `dependencies`
  or `const` anywhere that references `type`. Any variable validates on any item type.
- The specification lists variables in Appendix IV by data category — standard, number, date,
  name — and types in Appendix III as a prose glossary. Type exists to drive `cs:choose`
  conditionals inside citation styles. Appendix III's per-type prose is advisory and runs the
  other way: the presence of `container-title` on a `book` *reinterprets* the item as republished
  in a collection rather than restricting it.
- Neither reference processor carries a table. citeproc-js has zero occurrences of
  `article-journal` in its bundle and its own documentation points readers elsewhere;
  citeproc-py ingests arbitrary keys with no type gating.
- The nearest published mapping is Zotero's schema, and it fails on three counts before the
  licence question: 32 of 45 CSL types covered, 29 CSL 1.0.2 variables absent, and eleven
  CSL-variable-to-Zotero-field pairs that reverse ambiguously. Then the licence question, which is
  decisive on its own: `github.com/zotero/zotero-schema` carries no `LICENSE` file and the GitHub
  API reports no licence, so vendoring it means redistributing unlicensed material. The Zotero
  client being AGPL does not extend to the schema repo by assertion. The same applies to z2csl,
  the community mapping both Zotero's and citeproc-js's docs point at, which is additionally four
  years stale.

**What keeps the cost bounded:** the mapping governs presentation and nothing else (FR-004a). It
decides which fields a blank form offers first; every scalar field stays storable on every type,
and no stored value is ever dropped for being off-type. A disputed entry produces a form that asks
in an odd order, never a reference that cannot be recorded. That is what makes an editorial
artefact acceptable where a data constraint would not be.

**Cost accepted:** the mapping joins the package's public surface and will attract issues arguing
individual entries. Raised at the specification gate as the decision most worth vetoing.

**ADR:** docs/adr/0020-the-item-type-field-mapping-is-ours.md

## D2 — `categories` and `custom` stay off the form and must survive it

**Ambiguous:** both are scalar-ish fields on the item, so a form covering "the reference's own
scalar record" would nominally include them.

**Chosen:** neither appears on the form, and a save must leave both exactly as they were (FR-013).

**Why:** they carry structured content the conversion boundary owns, in a shape the person editing
has no way to reason about. A textarea holding raw JSON is a way to lose data, not a way to edit
it. The requirement is written as preservation rather than omission because leaving a field off a
form is not by itself a guarantee it survives — a form that rebuilds the record rather than
updating it would drop them silently, and Article XI treats losing stored bibliographic content as
the failure to design against.

**ADR:** none — the preservation guarantee it states is recorded architecturally in ADR 0021; which two fields sit behind it is a detail of this form and nothing downstream inherits it.

## D3 — Changing an item type never discards values

**Ambiguous:** if the form is scoped by type, what happens to populated fields when the type
changes to one they do not belong to?

**Chosen:** the values stay, and stay visible (FR-014, FR-010).

**Why:** the alternative is a silent delete triggered by a dropdown, which is the exact shape
Article XI exists to prevent. The person is better placed than the mapping to judge whether a
now-off-type value is wrong, and they cannot judge it if they cannot see it. This also protects
imported data, which routinely carries fields the mapping would not have offered.

**ADR:** docs/adr/0021-type-scoping-is-presentation-never-storage.md

## D4 — No access control, recorded as a decision rather than an omission

**Settled at intake by the maintainer:** the write pages are open, exactly as the read pages are.
The package is developed for one person managing their own library, and permissions arrive as the
package matures.

**Recorded here because the consequence is larger than the read-side equivalent.** FS-006's open
pages let an anonymous visitor see the catalogue; these let one empty it. The demo ships that way
too, and its guard asserts no page redirects to a login, so the openness is actively tested rather
than merely untested. Access control for the front end currently has no issue and no roadmap item.
Flagged at the gate.

**ADR:** docs/adr/0022-the-front-ends-pages-are-open.md

## D5 — Citation-key collisions are not handled at all

**Settled at intake by the maintainer:** nothing warns, refuses, or rewrites. A citation key is a
handle for writing bibliographies, and keeping keys distinct is the person's business, as in every
other reference manager.

**Consequence worth stating:** the import path contradicts this. `_resolve_citation_key` in
`converters.py` looks a key up across the whole store and appends a numeric suffix until it finds
a free one, so an imported `smith2020` can land as `smith2020-2`. `CONTEXT.md` documents that
de-duplication as a contract. Both are wrong under this posture and are tracked as issue #69,
which resolves separately. This feature does not depend on that landing first: the create form
stores what it is given either way.

**ADR:** docs/adr/0023-citation-key-uniqueness-is-the-readers-concern.md — which supersedes ADR 0001.

## D6 — One reference per removal

**Ambiguous:** nothing in the request rules on acting over many references at once.

**Chosen:** removal takes one reference behind a confirmation naming it (FR-022).

**Why:** selecting rows and acting on them together is a different interaction with a different
failure mode — a mis-click removes a set rather than an item, and a confirmation page cannot name
what is going in any useful way. No issue in R6 asks for it. It stays available as its own request
if the need turns out to be real.

**ADR:** none — one interaction on one page, reversible by adding the other; no future work is constrained by it.

## D7 — A reference with no contributors is valid

Forced by the split with #48, which owns contributors, dates and identifiers. Between this feature
and that one the interface can create a reference nobody is credited on. Acceptable because the
catalogue and reference pages already render an item whose related collections are empty, and
because requiring a contributor would make this feature undeliverable until #48 lands.

## Planning inputs (not requirements)

Recorded here so they reach S3 without being mistaken for statements about what the feature does.

- **Alpine.js is available and is the preferred mechanism for type scoping** (maintainer,
  2026-08-13). django-mvp ships it, so showing and hiding the form's field sets on a change of
  item type belongs in the browser rather than in a server round trip.
- **The form stack is already present.** django-mvp ships create, update and delete view bases, and
  both settings modules already install crispy-forms and crispy-tailwind. FR-026's no-custom-
  components rule points the same way: compose what is there. *(Corrected at S3R: the apps are
  installed but `CRISPY_TEMPLATE_PACK` is not set, which raises `AttributeError` on the first form
  render — see plan D-5.)*
- **The detail view's inherited CRUD link names are currently unnamespaced.** `ItemDetailView`
  overrides `crud_views` with only `list` and `detail` under the `literature:` namespace, so any
  inherited create/update/delete link would fail to reverse. Wiring the new views is where that
  gets settled.
- **The architecture test is a live constraint.** `tests/test_ui/test_architecture.py` asserts no
  core module imports `mvp`, `crispy_forms` or `literature.ui`. Form code lives in the UI app.

**ADR:** none — a consequence of where #47 and #48 were split, and it stops being true when #48 lands.

## D8 — Design-review outcome (S3R, 2026-08-13)

One reviewer, three lenses, one round. Thirteen findings, three verified high, all applied as edits
to `plan.md` and `tasks.md`; the itemised list is at the end of `tasks.md`. Nothing was carried as a
watch item, because every finding was cheap enough to fix at plan time — which is the stage working
as intended.

The three that would have cost a rework cycle if they had surfaced against a diff:

- **Every `show_<action>_action` defaults to `False`.** Listing an action in `directory` renders no
  button without its flag, and a CRUD shorthand in `success_url` silently degrades to a literal
  relative redirect. Every entry point and every landing page in the plan depended on flags the plan
  never mentioned.
- **django-mvp's stock submit buttons post `default_next=list`, and that is consulted before
  `success_url`.** Every save through the rendered page would have landed on the catalogue instead of
  the reference. The tests as first written would not have caught it, because a test posting a bare
  field dict never sends the parameter the button does.
- **Nothing seeded the Alpine scope from the server.** `cotton/form/index.html` opens
  `x-data="{form: {}}"` with an empty object, so `x-model` on the type select would have written
  undefined over the stored item type on every edit page, and the group guard would have thrown on a
  blank create page.

The security lens produced no finding. The reviewer confirmed D-3's no-loss guarantee holds as a data
claim and supplied the limit now written into D-3: it is structural for the rendered page, not for
the endpoint, because any POST omitting a field still blanks it.

It also caught that `plan.md` and `research.md` both said `Item` has 89 fields. That was a count of
every field in `models.py` across all five models. `Item` declares 64, of which 60 reach the form.
Neither conclusion the figure was cited for changes at 60.

**ADR:** none — this is a record of one review round, not a decision anything downstream inherits.

## D9 — C4 and C5's sub-cases, T003 implementation note

**Decision:** D-1's criteria 4 (`numbering`) and 5 (`original`) name no worked examples, unlike
criteria 1–3. `literature/ui/fieldgroups.py` applies them through three stated sub-cases rather than
a single per-type judgement call each: C4a (a periodical article, published with its own
volume/issue/page — `article`, `article-journal`, `article-magazine`, `article-newspaper`), C4b
(embedded in a paginated host — `chapter`, `entry`, `entry-dictionary`, `entry-encyclopedia`,
`paper-conference`, `review`, `review-book`), C4c (identified by an official/report number — `bill`,
`hearing`, `legal_case`, `legislation`, `regulation`, `treaty`, `patent`, `standard`, `report`). C5
is applied only where republication or translation by a different publisher is ordinary for the type
itself, not merely possible for an instance of it — `book` and `classic`.

**Why:** naming the sub-case is what T003 asks the per-type comment to do ("naming the criterion
that decided it"), and a bare "C4" or "C5" on nine and two types respectively would not distinguish
why a periodical article and a legal filing both count as "numbered" for different reasons. The
sub-cases are visible in `fieldgroups.py`'s own comment block above `TYPE_GROUPS`, so this entry
records that they exist and why, not what they are — that would drift out of sync with the code.

**Revisit if:** a type is added or reclassified and its C4/C5 status is unclear from the three
sub-cases as stated — that is a sign the sub-cases themselves need a fourth case rather than a
one-off exception on the new type.

**ADR:** none — an implementation note on how one criterion was applied, superseded in substance by D12's re-derivation.

## D10 — T008 registers only the create route; update/delete wait for their own stories

**Decision:** `tasks.md` T008 reads "Add the three routes to `literature/ui/urls.py`", and T007's own
test asks that every action in every view's `crud_views` reverses. Taken literally, both would need
`literature:item-update` and `literature:item-delete` registered now, alongside `literature:item-create`.
This implementer's brief covers only Phase 1 and Phase 2 (US-1) — `ItemUpdateView` (T017) and
`ItemDeleteView` (T020) are separate stories' own tasks, dispatched to their own worktrees. `path()`
needs a real callable at import time, so registering those two routes now would mean either writing
stub view classes for stories not in this brief, or the routes 500ing on import. Neither is this
story's to do. `literature/ui/urls.py` gains only `add/ → item-create` here; T007's test (T007 in
`tests/test_ui/test_urls.py`) checks, per view, every action the view's own `show_<action>_action`
flags actually mark shown, rather than every key an eventually-shared `CRUD_VIEWS` dict happens to
carry. `CRUD_VIEWS` itself (`literature/ui/views.py`) is still defined with all five actions, matching
D-6's end state, and assigned to `ItemListView`/`ItemCreateView` now — safe, because neither view's
code path ever calls `resolve_crud_url("update")` or `("delete")`.

**Why defensible:** no functional guarantee is weakened. The specific failure D-6/T007 exist to
prevent — an action a view *shows* with no resolvable route, raising `NoReverseMatch` inside
`get_breadcrumbs()` — cannot occur from this story's diff, because nothing this story ships ever
shows "update" or "delete". Building placeholder view classes to satisfy the literal test text would
be scope creep into T017/T020, and duplicating work across worktrees is worse than a route arriving
one story later than `tasks.md`'s single-session phrasing assumed.

**Revisit if:** the US-2 or US-3 Implementer's brief does not already tell them to add their own route
alongside their view — if it doesn't, that is a gap in their brief, not something to patch here.

**ADR:** none — sequencing between two stories in one feature, resolved before the feature ships.

## D11 — `item_form.html` overrides `page.content` in full, not just `formset`/`actions`

**Decision:** `form_view.html`'s own `{% block page.content %}` invokes `<c-form :form-obj="form"
:formset="formset" ...>` unconditionally, and `cotton/form/index.html` renders `<c-form.render
:form="form_obj" />` whenever `form_obj` is truthy — before `{{ slot }}` (which is where
`{% block formset %}`'s content lands). That call dumps the *whole* form through crispy in one shot,
which is exactly the mechanism plan.md D-3 says this template avoids ("rendering the form group by
group rather than through one `c-form.render` call"). Overriding only `formset`/`actions` (the blocks
`form_view.html` exposes) cannot prevent it — the auto-render sits outside every block `form_view.html`
declares. `item_form.html` therefore overrides `{% block page.content %}` in full, invoking its own
`<c-form title="..." icon="..." method="post" action="...">` **without** `:form-obj`, so
`<c-form.render />` never fires, and puts the grouped markup in the default slot instead. `before_form`,
`formset`, `actions` and `after_form` are re-declared as nested blocks inside this override, so a
future template extending `item_form.html` still has the same seams to hook.

Every value the grouped rendering needs (`showAll`, `typeGroups`, `forcedGroups`) is set as a property
of `form` — `form.showAll`, not a bare `showAll` — because `cotton/form/index.html` opens exactly one
`x-data="{form: {}}"` scope on the `<form>` element, and D-3 says no second scope is declared.
Alpine's expression evaluator runs `x-init`/`x-model` bodies through a JS `with(scope) { ... }`; a bare
identifier that is not already a property somewhere in that scope chain does not become a new
reactive property on assignment — in non-strict mode it silently becomes an implicit global instead.
`form.showAll = false` is a direct property write on an object (`form`) that already exists in scope,
which does not depend on `with`'s binding-lookup at all, and reads back correctly through `x-model`
and `x-show` because Alpine's reactive wrapper proxies nested objects on first access.

**Why defensible:** verified directly, not assumed — `tests/test_ui/test_views.py::TestItemCreateView`
posts through the rendered page and asserts on the response's actual behaviour (redirect target,
stored values, guarded groups), which would not pass against a page silently double-rendering the
form or a state variable that leaked to `window` instead of Alpine's reactive scope.

**Revisit if:** django-mvp ships a version of `form_view.html` that gates `<c-form.render />` behind
its own block, or exposes a `page.content` seam narrower than the whole block — either would let this
template go back to overriding only `formset`/`actions`, which is less to keep in sync with upstream.

**ADR:** none — a template mechanic local to this page; ADR 0021 records the guarantee it serves.

## D12 — T030's re-derivation applies plan.md D-1's full itemized C2 evidence, not only the named defect list

**Decision:** T030's defect paragraph names 11 types needing `container` plus `software` needing
`publication`. Its own instruction, though, is to "re-run the whole per-type assignment against the
corrected criteria... every type, not only the ones named above — the named ones are the symptom,
the criterion misreading is the cause." Reading plan.md D-1 point 2 in full (not just the sentence
quoted in the defect paragraph) surfaces the same misreading pattern in three more places: the
paragraph's closing sentence names four clusters (`legal`/`review`/`event`/`physical`) the first
pass evidently treated as the complete list, but the paragraph's itemized evidence ahead of that
sentence separately states `chapter-number` names song, `number-of-volumes`/`ISBN` name "the
book-like types", and `authority`/`jurisdiction`/`division` name patent *in addition to* the named
legal-types cluster — patent itself is not one of legal_case/legislation/bill/hearing/regulation/
treaty, so it needed the itemized reading and never got it. `song`, `book` and `patent` therefore
gained `numbering`, `numbering` and `legal` respectively, on the same evidentiary basis as the
container fix, with their own failing tests added first.

**Why defensible:** this is the same defect, not a new one — a partial reading of the same paragraph
of evidence, corrected by reading the whole of it, exactly as the task instructs. No group was
removed, no existing test weakened, and each addition has its own red-then-green test naming the
exact plan.md clause it rests on.

**Consequence:** `book`'s resolved field count (36) exceeds the stated 16–35 plausibility band by
one. That band is a check against Zotero's coverage, not a rule Zotero's schema is entitled to
enforce here — Zotero's own schema does not surface an equivalent of `number-of-volumes` for its
book type, so a set the criteria produce correctly can still sit outside a check built from a
different source's coverage. Documented in place in `TYPE_GROUPS`' own comment rather than trimmed
to fit the band.

**Revisit if:** a later pass finds plan.md D-1's itemized list names still more types this
re-derivation did not catch — check against the full text of point 2, not this decision's summary
of it, since the summary is necessarily lossy.

**ADR:** none — the correction is recorded in plan D-1 and in the mapping's own comments; ADR 0020 states the resulting rule.

## D13 — T018 sets `show_update_action` but not `show_delete_action` on `ItemDetailView`

**Decision:** tasks.md's T018 text reads `show_update_action = show_delete_action = True`. Only
`show_update_action` was set. `directory` still names `["update", "delete"]`, matching tasks.md and
`MVPDetailView`'s own default, and `crud_views = CRUD_VIEWS` still carries a `"delete"` key — neither
of those two is the part left out.

**Why:** the US2 task brief's `inherited_from_us1` is explicit that `item-delete` is US-3's own task,
not this story's: "US1 deliberately did not register item-update or item-delete because their views
did not exist... Registering item-update is yours; item-delete belongs to US3." `ItemDeleteView` does
not exist in this worktree and no route named `literature:item-delete` is registered.
`CRUDDirectoryMixin.resolve_crud_url()` (django-mvp) only calls Django's `reverse()` for an action
once `show_action()` — reading `show_<action>_action` — returns `True`; it returns `None` first for
every action whose flag is unset or falsy. Setting `show_delete_action = True` here, with no matching
route, would make every single GET to the reference page raise `NoReverseMatch` from
`ItemDetailView.get_context_data()` (`CRUDDirectoryMixin.get_directory()` iterates the whole
`directory` list unconditionally) — not a partial degradation, a 500 on every existing
`TestItemDetailView`/`TestReferencePageReadability` test and on the page itself. Leaving the flag
unset costs nothing at this action's own call sites: `resolve_crud_url("delete")` still returns
`None` safely (the `show_action()` check runs before `reverse()`, not after), so the key's presence
in `crud_views`/`directory` is inert until US-3 sets the flag.

**Consequence:** T018's own instruction to "Extend `TestItemDetailView` with a test that the Edit and
Delete actions render and point at the right routes" is only partly done — one test was added,
asserting the Edit action's href. No Delete-action test was added, since there is nothing for it to
assert yet (the button does not render, correctly, because `show_delete_action` is unset).

**Why defensible:** the brief that scopes this story's files and tasks is more specific than
tasks.md's general text on exactly this point, and following tasks.md literally here would ship a
broken reference page — verified, not assumed: `NoReverseMatch` is `CRUDDirectoryMixin`'s documented
behaviour for a shown action with no matching route ("A shown action whose route does not exist
raises `NoReverseMatch` rather than dropping the link, so the misconfiguration surfaces").

**Revisit if:** US-3 lands `ItemDeleteView` and its route — at that point `show_delete_action = True`
becomes safe to set on `ItemDetailView`, and the Delete-action test tasks.md's T018 describes belongs
there, not here.

**ADR:** none — sequencing between two stories, resolved when US-3 registered the route.

## D14 — T020 blocked at the time of writing: the delete confirmation page could not render

**Decision:** `ItemDeleteView`, its route and `ItemDetailView.show_delete_action = True` are
implemented exactly as T020 and plan.md D-7 specify. `TestItemDeleteView`'s three GET-rendering
scenarios (confirmation renders, decline returns to the reference, an inherited `?back` is honoured)
still fail — not from anything wrong in `ItemDeleteView`, but because django-mvp's `delete_view.html`
cannot be compiled at all under this repository's current settings. `TestItemDeleteView`'s four other
scenarios (POST removal and cascade, `Name` survival, empty-state, 404) and every other new/extended
test (`TestItemDetailView`'s delete-action render test, `TestDeleteRouteReverses`,
`TestCRUDViewsReverse` with `ItemDeleteView` added) pass, because none of them render that template.

**Root cause, verified directly, not assumed:**

```
$ DJANGO_SETTINGS_MODULE=tests.settings poetry run python -c "
from django.template.loader import get_template
get_template('cotton/form/render.html')"
django.template.exceptions.TemplateSyntaxError: crispy tag's template_pack argument
should be in ('uni_form', 'bootstrap3', 'bootstrap4')
```

That call carries no view, no request, no form — the template alone fails to *compile*.
`cotton/form/render.html` (installed `mvp` package) reads:

```
{% if form.helper %}
  {% crispy form %}
{% else %}
  {{ form|crispy }}
{% endif %}
```

Django's template parser compiles **both** branches of an `{% if %}` at first-compile time,
regardless of which branch a given render will take — `do_if` calls `parser.parse(("elif", "else",
"endif"))` immediately, which is what invokes crispy-forms' `{% crispy %}` tag compiler
(`do_uni_form`) unconditionally. `do_uni_form` (`crispy_forms/templatetags/crispy_forms_tags.py:242`)
initialises `template_pack` to `get_template_pack()` — this repo's `CRISPY_TEMPLATE_PACK = "tailwind"`
(plan.md D-5) — whether or not the tag was given an explicit pack argument, and always validates it
against `CRISPY_ALLOWED_TEMPLATE_PACKS`, which defaults to `("uni_form", "bootstrap3", "bootstrap4")`
when unset. Neither `tests/settings.py` nor `demo/settings.py` sets it. `"tailwind"` is therefore
never a valid pack, and the template cannot compile — not intermittently, not only when `form.helper`
is truthy, always.

**Why plan.md D-5's own text is what let this through:** D-5 states "the `CRISPY_ALLOWED_TEMPLATE_PACKS`
assertion beside it stays, because that setting is only consulted when the `{% crispy %}` tag is given
an explicit pack argument, which `cotton/form/render.html` does not do." That is the claim the probe
above disproves: `do_uni_form` validates the *default* pack from `get_template_pack()` exactly the same
way it validates an explicit one — the `if template_pack is not None` guard is true either way, since
`template_pack` is seeded from `get_template_pack()` before any explicit-argument parsing runs. Nothing
caught this at plan time because no page rendered a form through `<c-form :form-obj="...">` until now —
`item_form.html` (US-1, D11) deliberately avoids that exact path for an unrelated reason (grouped
rendering, D-3), and `delete_view.html` is the first template in this feature that does not.

**Why this is not mine to fix:** the mechanical fix is `CRISPY_ALLOWED_TEMPLATE_PACKS = ("tailwind",)`
(or a tuple including it) in `tests/settings.py` and `demo/settings.py` — both `must_not_touch` for this
story, and `tests/test_ui/test_smoke.py` carries a pre-existing, not-mine-to-modify assertion
(`assert not hasattr(settings, "CRISPY_ALLOWED_TEMPLATE_PACKS")`) that a same-file fix would have to
contradict. The other route — writing `literature/ui/templates/literature/ui/item_delete.html` to route
around the broken upstream template — is exactly what plan.md D-7 and this brief both say not to do
("django-mvp's `delete_view.html` renders the whole confirmation page... Write no template"), and
`literature/ui/templates/` is `must_not_touch` regardless. No attribute on `MVPDeleteView` changes which
branch of `cotton/form/render.html` gets *compiled* — only which one runs, and the crash happens before
either runs.

**Consequence:** T020 ships `ItemDeleteView`, the route and the detail-page flag/test as specified, and
is reported `blocked` rather than `done` — three of `TestItemDeleteView`'s seven scenarios stay red
until a settings change lands that this story's scope cannot make.

**Revisit if:** a follow-up (settings-scoped) change sets `CRISPY_ALLOWED_TEMPLATE_PACKS` to include
`"tailwind"` in both settings modules, corrects plan.md D-5's mistaken claim, and updates
`test_smoke.py`'s assertion under its own Article I decision record — at that point the three blocked
scenarios need no further code change, only a re-run.

**ADR:** none — a finding, resolved by D15; the resulting configuration requirement lives beside the setting itself.

## D15 — The crispy allowlist, and why two stories passed over the same defect

*Resolves D14, which was written while the story was blocked and is left in place as the finding.*

**Found by US-3, by reproduction rather than inference:** `get_template("cotton/form/render.html")`
raises `TemplateSyntaxError: crispy tag's template_pack argument should be in ('uni_form',
'bootstrap3', 'bootstrap4')` with no request, no view and no form involved.

**Cause:** the `{% crispy %}` tag validates the resolved template pack against
`CRISPY_ALLOWED_TEMPLATE_PACKS` when the template is *compiled*, not when it is rendered. The
default allowlist does not contain `tailwind`, so every template carrying the tag fails to compile
— whatever arguments the tag is given, and whichever branch of a surrounding `{% if %}` would run.

**Why US-1 and US-2 did not hit it:** `item_form.html` overrides `page.content` in full and passes
no `:form-obj`, precisely so `cotton/form/render.html` never fires. The create and update pages
therefore never compile it. The delete page renders django-mvp's own `delete_view.html` unmodified,
per D-7, and that is the first template in the feature to reach the tag.

**Fixed on the feature branch rather than in the story**, because both settings modules are outside
US-3's editable scope and writing a replacement delete template — the only in-scope alternative — is
exactly what D-7 says not to do. `CRISPY_ALLOWED_TEMPLATE_PACKS = ["tailwind"]` now sits beside
`CRISPY_TEMPLATE_PACK` in `tests/settings.py` and `demo/settings.py`, matching what django-mvp's own
demo does, and `tests/test_ui/test_smoke.py`'s second stale assertion is dropped under the same
Article I decision as the first.

**The part worth keeping.** The claim this corrects came from the design review and I wrote it
into the plan without reproducing it. It was specific, plausible and cited real source lines, and it
was wrong — the reviewer read the code path for an explicit pack argument and generalised. A design
review is evidence, not a verdict, and a claim about *when* a check fires is exactly the kind that
costs three minutes to run and a story to discover.

**ADR:** none — a configuration requirement of a dependency this package already declares, and it
lands in the settings modules with its reason beside it.

## D16 — Changing `test_smoke.py`'s cookie-jar monkeypatch is in scope for T021

**Ambiguous:** `tests/test_demo/test_smoke.py`'s `TestUnauthenticatedWalk` predates this story and is
not a test I authored — the general rule (craft-tdd) is never to modify a test I did not write.

**Chosen:** updated its two tests to monkeypatch `urllib.request.OpenerDirector.open` instead of the
module-level `urllib.request.urlopen`, with no change to what either test asserts.

**Why defensible:** plan.md D-9 requires the write pass to reuse one cookie jar across the whole
walk — a CSRF cookie set while GETting a form page has to still be attached on the POST back to it,
which two independent `urlopen` calls cannot do. `DemoWalk._get` therefore now reads through
`self.opener` (an `OpenerDirector` built in `__init__`), and the two tests that stub the HTTP layer
have to stub the thing that layer now is, or they no longer test what `_get` actually calls. This is
the same class of change T001 made to this file's sibling assertions, under the same rule
(constitution Article I): a pre-existing test may change when a recorded decision requires it, and
the decision has to be on record rather than improvised. D-9 is that decision; this entry is the
record for the second test file it touches. Both tests keep their names, their fixtures and their
exact assertions — `test_a_redirect_to_a_login_page_fails_the_check` still expects
`SmokeCheckFailed` with `"login page"` in the message, `test_a_page_served_without_a_login_returns_its_body`
still expects the fetched body back unchanged.

**Revisit if:** never, short of the walk dropping the shared-opener requirement entirely.

**ADR:** none — a test mechanism this story's own design required; nothing downstream inherits it.

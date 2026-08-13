# Research — 008 Add, edit and remove references through the front end

What was checked rather than assumed, and what it settled. Two questions dominated: where a
type-to-field mapping can come from, and what the front-end toolkit already provides.

## 1. CSL publishes no item-type-to-variable mapping, and the gap is deliberate

Checked directly against the sources rather than inferred.

**The schema has no type conditionals.** `csl-data.json` (v1.0.2,
`https://resource.citationstyles.org/schema/v1.0/input/json/csl-data.json`, MIT) declares `items`
with `properties` (103 flat), `required: ["type", "id"]` and `additionalProperties: false`. There is
no `if`/`then`, `allOf`, `anyOf`, `oneOf`, `dependencies` or `const` anywhere in the file, and `type`
is a plain enumerated string. Every property validates on every type.

**The specification separates the two concepts on purpose.** Appendix III lists types as a prose
glossary; Appendix IV lists variables grouped by data category (standard, number, date, name). Type
exists to drive `cs:choose` conditionals inside citation styles.

**Appendix III is thin as evidence.** Only 14 of the 45 types name any variable at all, and across
the whole appendix just nine distinct variables are named. Three prose patterns account for nearly
all of it:

- "If a `container-title` is present, the item is interpreted as …" — book, broadcast,
  motion_picture, report, song, webpage. A statement about containment semantics, not applicability.
- "The format … may be specified using `medium`" — book, figure, graphic.
- "Use `genre` to specify the type of …" — broadcast, speech, thesis.

**Appendix IV carries the denser signal.** Around 35 of its 98 variable definitions include an
example that implies a type, and the name variables cluster hardest: five point at broadcast
(`executive-producer`, `guest`, `host`, `producer`, `series-creator`), three at motion_picture
(`director`, `script-writer`, `performer`), two each at review and interview. Standard variables
carry the same signal for the legal cluster (`authority`, `jurisdiction`, `division`, `references`),
the archival cluster (`archive`, `archive_collection`, `archive_location`, `archive-place`) and the
map case (`scale`).

**The gap is acknowledged upstream and unresolved.** `citation-style-language/documentation` issue
43, "Request: List of relevant field types for each reference type", has been open since 22 April
2016 asking for exactly this. On the CSL Discourse thread "Clarifications about variables and types"
one maintainer calls a per-type guideline "extremely valuable" while CSL's co-creator argues against
type restrictions on principle. The documentation repository contains only `specification.rst`,
`primer.rst`, `translating-locale-files.rst` and an attic — no mapping artefact of any kind.

**Nothing usable is published under a licence this package can take.**

| Source | Licence | Why it fails |
|---|---|---|
| `csl-data.json` | MIT | No type dimension at all |
| CSL specification text | CC BY-SA 4.0 | Usable as cited evidence; carries no matrix |
| CSL style files | CC BY-SA 3.0 | Type conditions are about rendering, not applicability — in `apa.csl`, 113 of 114 type conditions sit inside macros, and both branches of a type split routinely render the same variable |
| citation-js | MIT | Type maps are source-format-to-CSL-type only; just 15 type guards touching 8 variables |
| Zotero schema | **none** | No `LICENSE` file, no statement, GitHub reports none — redistributing it means redistributing unlicensed material |
| z2csl | none | Same problem, plus stale at Zotero 6.0.10-beta.7 (July 2022) |
| Mendeley/Elsevier mapping | all rights reserved, explicitly excluding text and data mining | Disqualifying |

**Conclusion:** the package authors its own mapping. That is FR-004 and decision D1 in
`decisions.md`.

**Zotero is still useful as a plausibility check, without being copied.** Composing its schema
(`csl.types` → Zotero item types → fields and creator types → `csl.fields`/`csl.names`) yields a CSL
variable count per type: minimum 16 (`post`), maximum 35 (`chapter`), median 24, over the 32 CSL
types it covers. It omits 13 types entirely: `classic`, `collection`, `entry`, `event`, `figure`,
`musical_score`, `pamphlet`, `performance`, `periodical`, `regulation`, `review`, `review-book`,
`treaty`. So a defensible per-type set is roughly a quarter of the model's fields, not most of them,
and the thirteen gaps are precisely the types no external source can help with.

**Two corrections to carry.** The often-quoted "103 CSL variables" is the schema's property count and
includes `id`, `type`, `custom` and `categories`, none of which are bibliographic variables;
Appendix IV defines 98. And the two disagree on names — the schema's `part`, `printing` and
`supplement` are legacy forms of Appendix IV's `part-number`, `printing-number` and
`supplement-number`, while `license` and `editor-translator` are in the specification and absent from
the schema. This package's model follows the schema's names, which is worth stating wherever the
mapping is documented.

## 2. django-mvp already provides the whole form stack

Pinned version is what matters: `pyproject.toml` declares the `ui` extra as
`django-mvp (>=0.17,<1.0)` and `poetry.lock` resolves **0.17.0**, which is what the virtualenv has.
The local checkout of django-mvp is 0.18.0. Everything below was verified against the installed
0.17.0, and the files cited are byte-identical between the two.

**View bases** — `mvp/views/edit.py`: `MVPCreateView`, `MVPUpdateView`, `MVPDeleteView`, all
descending from `MVPModelFormBase` → `MVPFormBase(SuccessMessageMixin, BaseTemplateNameMixin,
NextURLMixin, PageObjectMixin)`. They take the ordinary Django `model` + `fields` or `form_class`,
plus `page_title`, `success_message`, `crud_views`, `directory`. Create and update render
`form_view.html`; delete renders `delete_view.html`, which extends it.

**`success_url` is mandatory here.** `MVPModelFormBase.get_success_url()` falls through next-URL →
`success_url` → `self.object.get_absolute_url()` → `ImproperlyConfigured`, and `Item` defines no
`get_absolute_url()`. `MVPDeleteView` does not consult `get_absolute_url()` at all and falls back to
the resolved `list` CRUD URL.

**`crud_views` is how a namespaced app wires its own routes.** The default names come from
`MVP_CONFIG["view_names"]` (`{model_name}-list`, `-detail`, `-create`, `-update`, `-delete`), and a
namespaced app overrides the dict on the view — which `literature/ui/views.py:104` already does for
`list` and `detail`, building a new dict rather than mutating the shared config. An action that is
not shown resolves to `None` harmlessly; an action that *is* shown with no matching route raises
`NoReverseMatch`, and inside `get_breadcrumbs()` that is an uncaught render-time 500. So the create,
update and delete names have to be added to every view's `crud_views` that shows them, not only to
the new views.

**Forms render through crispy-forms.** `cotton/form/render.html` uses `{% crispy form %}` when the
form carries a helper and `{{ form|crispy }}` otherwise. **`CRISPY_TEMPLATE_PACK` is not set in this
repository** — neither `tests/settings.py` nor `demo/settings.py` sets it — so it currently defaults
to `bootstrap4` while `crispy_tailwind` is installed. Nothing has noticed because the package renders
no forms yet. This feature is the first that would, so setting it to `tailwind` is part of the work.

**There is no fieldset, tabs, accordion or collapse component** anywhere in django-mvp 0.17.0's 85
cotton templates. What exists for grouping is `c-card` (title, icon, slots), `c-section` (title,
icon, level), `c-divider` and `c-group`. `c-form.render` renders a whole form in one crispy call, so
splitting a form into visible groups means either a crispy `FormHelper`/`Layout` or rendering
field-by-field. `form_view.html` exposes `before_form`, `formset`, `actions` and `after_form` blocks.

**Alpine is on every page.** In 0.17.0 it arrives as three deferred CDN tags from `mvp/base.html`;
in 0.18.0 it is bundled. Either way it is available without the consumer doing anything. django-mvp
uses it inline throughout (`x-data`, `x-show`, `x-transition`, `$persist`, `$watch`), and
`cotton/form/index.html` already opens a scope on the `<form>` element itself
(`x-data="{form: {}}"`), so markup inside the form's blocks can read and write `form.*` without
declaring its own scope. The one seam that does not exist: the item-type `<select>` is rendered by
crispy, so an `x-model` on it has to come from the form's widget attrs.

**Delete confirmation ships complete.** `delete_view.html` renders a warning alert, an optional
related-objects summary (`show_related_objects`), an optional type-to-confirm field
(`require_confirmation`, backed by `DeleteConfirmForm`), a protected-objects branch that suppresses
the delete button, and Back/Confirm actions. Nothing needs writing.

**Messages are wired.** `MVPFormBase` inherits `SuccessMessageMixin`, `MVPDeleteView.form_valid`
calls `messages.success` directly, and `mvp/base.html` renders `c-messages`. Both `demo/settings.py`
and `tests/settings_core.py` configure the app, middleware and context processor, so a `client.post`
in a test will not fail on `MessageFailure`.

**Do not design against `InlineFormSet`.** `MVPInlineCreateView`/`MVPInlineUpdateView` exist in
0.17.0 with the older `inline_*` attribute API; the checkout's `InlineFormSet` rewrite is a 0.18.0
breaking change. Irrelevant to this feature, which touches no related records, but worth stating so
a later feature does not read the wrong source.

## 3. The repository's own starting point

- `literature/ui/` has no `forms.py`, no POST handler, no `<form>`, no CSRF token. Every view is a
  `ListView` or `DetailView` subclass. This feature writes the first write path in the package.
- `Item` declares 64 fields — 60 scalar, plus `categories`, `custom`, `created` and `modified`.
  `fields = "__all__"` is not a viable form. (An earlier draft of this file said 89, which was a
  count of every field in `models.py` across all five models rather than `Item`'s own.)
- Six of those fields are processor-generated or cite-level rather than bibliographic —
  `citation_number`, `first_reference_note_number`, `year_suffix`, `citation_label`, `locator`, and
  arguably `citation_key` itself. A CSL processor assigns most of them. They are still storable and
  must stay reachable per FR-004a, but no item type has a case for offering them up front.
- `tests/` contains no POST test, no auth fixture, no `client.post` anywhere. The test patterns are
  pytest classes with the `db` and `client` fixtures passed per method, factories in
  `tests/factories.py`, and shared fixtures in `tests/conftest.py` plus `tests/test_ui/conftest.py`
  (`populated_item`).
- `tests/test_ui/test_architecture.py` asserts no core module imports `mvp`, `crispy_forms` or
  `literature.ui`. All form code belongs in the UI app.

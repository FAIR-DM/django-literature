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

## D3 — Changing an item type never discards values

**Ambiguous:** if the form is scoped by type, what happens to populated fields when the type
changes to one they do not belong to?

**Chosen:** the values stay, and stay visible (FR-014, FR-010).

**Why:** the alternative is a silent delete triggered by a dropdown, which is the exact shape
Article XI exists to prevent. The person is better placed than the mapping to judge whether a
now-off-type value is wrong, and they cannot judge it if they cannot see it. This also protects
imported data, which routinely carries fields the mapping would not have offered.

## D4 — No access control, recorded as a decision rather than an omission

**Settled at intake by the maintainer:** the write pages are open, exactly as the read pages are.
The package is developed for one person managing their own library, and permissions arrive as the
package matures.

**Recorded here because the consequence is larger than the read-side equivalent.** FS-006's open
pages let an anonymous visitor see the catalogue; these let one empty it. The demo ships that way
too, and its guard asserts no page redirects to a login, so the openness is actively tested rather
than merely untested. Access control for the front end currently has no issue and no roadmap item.
Flagged at the gate.

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

## D6 — One reference per removal

**Ambiguous:** nothing in the request rules on acting over many references at once.

**Chosen:** removal takes one reference behind a confirmation naming it (FR-022).

**Why:** selecting rows and acting on them together is a different interaction with a different
failure mode — a mis-click removes a set rather than an item, and a confirmation page cannot name
what is going in any useful way. No issue in R6 asks for it. It stays available as its own request
if the need turns out to be real.

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
- **The form stack is already present.** django-mvp ships create, update and delete view bases and
  the demo already installs crispy-forms with the Tailwind template pack. FR-026's no-custom-
  components rule points the same way: compose what is there.
- **The detail view's inherited CRUD link names are currently unnamespaced.** `ItemDetailView`
  overrides `crud_views` with only `list` and `detail` under the `literature:` namespace, so any
  inherited create/update/delete link would fail to reverse. Wiring the new views is where that
  gets settled.
- **The architecture test is a live constraint.** `tests/test_ui/test_architecture.py` asserts no
  core module imports `mvp`, `crispy_forms` or `literature.ui`. Form code lives in the UI app.

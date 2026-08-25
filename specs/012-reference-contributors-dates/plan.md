# Implementation Plan: Manage a Reference's Contributors, Dates and Identifiers

**Branch**: `012-reference-contributors-dates` · **Spec**: [`spec.md`](spec.md) · **Research**: [`research.md`](research.md) · **Decisions**: [`decisions.md`](decisions.md)

**Input**: Feature specification approved at the specification gate on 2026-08-25.

## Summary

The reference form gains three related-row sections — contributors, dates, identifiers — saved with
the reference in one transaction. django-mvp 0.19.3 supplies almost all of the machinery:
`MVPInlineUpdateView`/`MVPInlineCreateView` with three `InlineFormSet` declarations give the
transaction, the per-set validation, the error survival across an invalid submission, and browser
add and remove. What this feature writes is the three declarations, the forms behind them, a
template that renders them in the tabular layout, a date-slot mapping beside the existing
field-group one, an `ItemDate.clean()` that finally enforces the span rule its help text has always
claimed, and one recovered distinction inside the ISBN validator.

The single interesting design question — how a contributor is named without the interface deciding
who the person is — resolves to a plain HTML element rather than a component, for the reason set out
in D-1.

## Technical Context

**Language**: Python 3.11+ (the `ui` extra requires 3.12+) · **Framework**: Django 4.2–6.0

**Dependencies**: django-mvp rises `>=0.19.1` → `>=0.19.3` (the tabular formset layout, commit
d80be75). No new dependency is added. django-partial-date, django-tables2 and django-filter are
unchanged.

**Storage**: no schema change. No field is added, removed, widened or constrained, and no migration
is generated. `ItemDate` gains a `clean()` and a `save()` — Python-level validation, not a database
constraint, which is what keeps FR-039 true.

**Testing**: pytest + pytest-django, mirroring the source tree under `tests/test_ui/`, one factory
per model, class-grouped tests. The demo guard extends `tests/test_demo/`.

**Target**: the opt-in `literature.ui` app, plus two files in the core — `literature/validators.py`
for the ISBN message and `literature/models.py` for the `ItemDate` span rule. Both are core because
a project that never installs the front end should get the same diagnosis and the same protection
(FR-037).

**Constraints**:

- No custom UI component and no custom CSS (FR-038). Everything renders through django-mvp's
  existing set plus native HTML.
- The core acquires no front-end dependency (FR-036). `literature/ui/` is not imported from the
  core, and `tests/test_ui/test_architecture.py` already asserts it.
- Which identifier values are accepted or rejected does not change (FR-029). The existing
  parametrised validator tests are the guard and must pass untouched.

## Constitution Check

| Article | Bearing on this feature |
|---|---|
| I — Test-First | Every task writes its failing test before its production code. The date-span rule and the ISBN distinction are both defects with no test today, so each begins by reinstating the defect as a failing assertion. |
| II — Simplicity | The formset machinery is composed, not reimplemented. The one place this feature could have grown a subsystem — a contributor picker — is answered with `<datalist>` (D-1). |
| V — Security & data-safety | No stored value is lost by a round trip (FR-034, SC-006). The pages stay open, per ADR-0022, and that is unchanged rather than newly decided. |
| VI — Documentation | `docs/` gains the editing flows and the date-slot mapping in this PR, not after it. |
| VIII — Internationalization | Every new string is `gettext_lazy`-wrapped, and the message catalogue is regenerated as an explicit task (research R7 — nothing automates it). |
| XI — Data integrity | The end-without-begin path is a live export data-loss route (research R5); closing it is squarely this article. |
| XIII — Data-model conventions | No model field is added, so the `help_text`/`verbose_name` obligation applies only to the new form fields. |
| XIV — Test structure | Tests mirror the source tree; factories exist for all four models already. |

No violation to record in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```
specs/012-reference-contributors-dates/
├── spec.md              approved 2026-08-25, refined for ISSN the same day
├── decisions.md         D1–D10 from specification, D11+ from planning
├── research.md          R1–R7
├── plan.md              this file
├── tasks.md
├── progress.md
└── feature-state.json
```

### Source code

```
literature/
├── models.py                     ItemDate.clean() + save() — the span rule (FR-016)
├── validators.py                 ISBN: shape and check digit reported apart (FR-027)
├── locale/en/LC_MESSAGES/        regenerated
└── ui/
    ├── fieldgroups.py            + TYPE_DATE_SLOTS, the sibling mapping (D-5)
    ├── forms.py                  + NameForm, ItemDateForm, ItemIdentifierForm
    ├── inlines.py                NEW — the three InlineFormSet declarations
    ├── views.py                  create/update views compose the inline mixin
    └── templates/literature/ui/
        ├── item_form.html        renders the three sets, tabular layout
        └── contributor_datalist.html   NEW — the suggestion list (D-1)

tests/test_ui/                    mirrors the above
tests/test_models.py              the span rule
tests/test_validators.py          the ISBN distinction
tests/test_demo/                  the guard over the three flows
demo/                             seeded catalogue reaches the flows
docs/                             the editing flows, the date-slot mapping
```

## The decisions worth naming before implementation

### D-1 — the contributor name field is a `<datalist>`, not a widget

Settled in specification D1: accepting a completion asserts spelling, never identity, and a new
`Name` record is created every time. Research R4 found django-mvp ships no combobox, autocomplete or
enhanced select of any kind, and this looked like the feature's one external dependency.

It is not, because `<datalist>` is native HTML and does exactly this: a text input with attached
suggestions, filtered as the person types, where accepting one writes its text into the input and
nothing else happens. No record is referenced, nothing is posted but the text, and a value absent
from the list is equally acceptable.

The point worth keeping: **a binding select would have needed a component; completion needs an
element.** The decision that made the feature correct is the same one that removed its only external
dependency. FR-038 is satisfied without an upstream request.

The list is rendered once per page from the distinct stored names, referenced by every contributor
row's family-name input through `list=`. A separate template keeps it out of the row markup, which
the formset's `__prefix__` cloning rewrites.

### D-2 — three `InlineFormSet` declarations, one view

`literature/ui/inlines.py` declares `ContributorInline` (over `ItemName`), `DateInline` (over
`ItemDate`) and `IdentifierInline` (over `ItemIdentifier`). The create and update views compose
django-mvp's inline mixin and list all three. Each targets a different relation, so the default
per-relation prefixes are distinct and the duplicate-prefix guard does not fire.

The transaction, the accumulate-all-errors validation and the survival of an invalid submission come
from the library (research R1). This feature adds no save path of its own — FR-033 is satisfied by
composing the machinery correctly, not by writing it.

### D-3 — a contributor row edits its `Name` through the link

`ItemName` carries `item`, `name`, `role` and `order`; the person types into `Name`. So
`ContributorInline`'s form is over `ItemName` and declares the name parts as unbound fields, creating
or updating the `Name` in the form's `save()`. A nested formset is not supported by the library and
is not needed: a contributor row is exactly one name.

Because entry never reuses a stored record (FR-006), the create path is unconditional — every row
that is not editing an existing link creates a `Name`. Editing an existing row updates the `Name` it
already points at, which is that reference's own record and shared with nothing unless an import put
it there.

Family and given are the row's columns. The particles, the suffix and the unparsed organizational
form are reachable rather than laid out (FR-009), which in a tabular row means a disclosure the row
opens rather than five more columns. The three citation-processor flags are never form fields
(FR-010), so `ModelForm` never writes them and they are preserved by construction.

### D-4 — position is a number, because dragging would mean a component

FR-004 requires reordering within a role. Research R3 found django-mvp has no reordering support at
all and deliberately dropped `@alpinejs/sort` from its bundle. Building drag-and-drop here would mean
a custom component, which FR-038 forbids, and the standing rule sends a gap upstream rather than
solving it locally.

Django's own `can_order` is reachable through the declaration's escape hatch and renders as an
ordinary number input, which django-mvp's own documentation gives as the example of a setting with
no shorthand. So a contributor row carries a position column, and reordering means changing numbers.

This is honest rather than elegant, and it is what Django's admin did for years. A drag affordance is
filed upstream as a django-mvp request, and when a release carries one this becomes a template
change. Recorded as a decision rather than a silent limitation, because someone will ask.

`ItemName.order` is `editable=False`, which excludes it from a generated form but places no
restriction on what a view writes. The form declares its own position field and assigns `order` in
`save()`. Positions are renumbered per `(item, role)` on save so that a person entering 1, 1, 3
gets a coherent sequence rather than a rejection.

### D-5 — a sibling mapping, not a wider `GROUPS`

FR-013 asks for the item-type-to-field mapping extended to cover date slots. Research R6 measured
what folding them into `GROUPS` would do: `GROUPS` is flattened into `ItemForm.Meta.fields`, so a
name that is not an `Item` column raises `FieldError` at class-definition time; a test asserts the
flattened set equals exactly `Item`'s scalar form fields, and it exists precisely to catch this; the
context builder resolves each name as a bound field on `ItemForm`; and the populated-group check
would see a related manager and force the group permanently visible.

So `fieldgroups.py` gains `TYPE_DATE_SLOTS`, mapping each of the 45 item types to the slots that lead
for it, beside `TYPE_GROUPS` rather than inside it. Same module, same criteria, same ADR-0020
obligations: every entry carries a comment naming the criterion that decided it, and the evidence is
CSL's own appendices.

`issued` is always-on, the way `core` and `general` are. A type adds at most one or two others —
`accessed` for a webpage, `event-date` for a conference paper, `original-date` for a translated or
reissued work.

### D-6 — the no-loss guarantee moves into the view, as ADR-0021 said it would

ADR-0021's guarantee is that the server never builds a narrower form, so a hidden field keeps and
re-posts its value and changing item type discards nothing. Its stated revisit condition is a write
path that is not the rendered page — a partial update — and **inline formsets over related rows are
exactly that**: an omitted row means no row, not a blanked column.

The guarantee is therefore carried explicitly rather than inherited:

- The date set declares a row for every slot the reference already holds, whatever the type mapping
  says, plus the slots the mapping leads with. A slot holding a value is always rendered (FR-018),
  hidden client-side at most.
- The date form declares only the parts a person meets. Everything else on `ItemDate` — season,
  circa, literal, raw, raw date parts — is absent from the form, so `ModelForm` never writes it
  (FR-017). The one exception is a stored date whose only content is unparsed, which is rendered
  read-through so it can be repaired rather than being invisible (FR-018).
- Deletion is explicit through the formset's `DELETE`, never implied by a row's absence.

An ADR is warranted here and is proposed at convergence, because it amends how ADR-0021's guarantee
is upheld once the write path includes related rows.

### D-7 — the ISBN distinction is a refactor, not a new rule

Research R7: `_isbn10_valid` and `_isbn13_valid` each begin with a standalone shape regex and only
then compute the checksum, collapsing both outcomes into `False`. The distinction exists in the code
and is discarded one line before the raise. Recovering it moves no value between accepted and
rejected.

The helpers return which of the two they failed on; `validate_isbn` raises the check-digit message
only when a value matched one of the two shapes, and the existing shape message otherwise. Codes stay
distinguishable (`invalid_isbn` and a new `invalid_isbn_checksum`) so a caller can branch without
matching on prose.

The two consumers that use these validators as raise-or-not discriminators — the BibTeX identifier
branch and the RIS `SN` router — are unaffected by wording, and the RIS routing tests are the proof.

ISSN is out, per the spec's refinement note and issue #118.

### D-8 — a second identifier of the same type is caught in the formset, not the database

FR-030 requires a message naming the limit rather than a database error. The `(item, type)`
uniqueness constraint fires at the database, after the transaction has opened. So the identifier
formset validates across its own rows in `clean()` and reports the collision against the offending
row before any write is attempted. The database constraint stays as the backstop it already is.

The same applies to the date set and `(item, date_type)`.

### D-9 — the type match for identifier kinds is case-insensitive at the form, not in the validator

FR-025: a kind typed as `isbn` is treated as ISBN and checked. Research R7 found the dispatch is a
plain dict keyed by exact-case acronyms, and that a type stored as `doi` is never validated today.

Changing the dispatch would alter what the import path validates, which is beyond this feature's
scope and would change behaviour FR-029 protects. So the normalization happens in the identifier
form: a submitted kind matching a known one other than by casing is cleaned to the canonical
acronym, and what reaches the model is already canonical. Values arriving by any other path behave
exactly as they do today.

## Complexity Tracking

Nothing here requires a constitution exception. The two core-side changes are each a defect being
closed rather than a new subsystem, and both were measured before being planned.

The one accepted awkwardness is D-4: reordering by typing a number, because the alternative is a
component this package is not allowed to write. It is recorded, filed upstream, and reversible in a
template when django-mvp carries a drag affordance.

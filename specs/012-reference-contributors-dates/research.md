# Research — FS-012

Measurements taken against the code before planning. Every claim below was read out of a file or
run, not inferred. Line references are to the state of the tree on 2026-08-25.

## R1 — django-mvp already carries the parent-plus-related-sets machinery

`mvp/views/inline.py` exposes `InlineFormSet`, `MVPInlineCreateView` and `MVPInlineUpdateView`. A
consumer declares `inlines = [SomeInline, AnotherInline]`, and the view builds one formset per
declaration against the same parent instance, validates them all with `all_valid`, and saves the
parent and every set inside one `transaction.atomic()` block, parent first.

Three properties matter for this feature, all of them things the spec asks for and none of which
have to be built here:

- **One transaction covering the parent and all three sets.** ADR-0005 and ADR-0008 in django-mvp
  record why: `ATOMIC_REQUESTS` cannot be assumed of a consuming project, so the view opens its own
  transaction. FR-033's "a rejected save leaves the catalogue exactly as it was" is this behaviour,
  not new work.
- **`all_valid` rather than `all`.** Its list comprehension defeats short-circuiting, so every set
  accumulates its errors instead of the first failure hiding the rest.
- **Errors survive re-rendering.** The constructed formsets are memoised on the view, so
  `form_invalid` re-renders the bound sets rather than discarding them. FR-033's second half —
  returning the form carrying what was entered — is also existing behaviour.

`min_num`/`max_num` are enforced per set, never against a page-wide total. Two declarations
resolving to the same prefix raise `ImproperlyConfigured` naming both classes; the three sets here
target three different relations, so the default per-relation prefixes are distinct.

**Version floor.** These classes are present from 0.19.1. The tabular layout is 0.19.3
(django-mvp/django-mvp#299, commit d80be75). The floor rises to 0.19.3 in this feature.

## R2 — the tabular layout is opted into in the template, not the view

`layout="tabular"` is an attribute on `<c-form.formset>`. There is no view-level equivalent:
`InlineFormSet` has no `layout` attribute, and django-mvp's own `form_view.html` renders every set
as `<c-form.formset :formset="inline" />` with no layout passed, which is the stacked default.

**Consequence for the plan:** the reference form template overrides the formset block and renders
the three sets by hand with `layout="tabular"`. This is a documented extension point, not a
workaround, and it introduces no component and no CSS.

What tabular renders: a heading row built from `empty_form.visible_fields()` excluding `DELETE`,
one column per field, each heading carrying the field's label, a required marker, and the field's
help text beneath. Column tracks are an inline `grid-template-columns` style because the column
count is only known at render time. Rows are separate grids, deliberately not a `<table>`. Below
the `sm` breakpoint the whole thing reverts to the stacked layout.

Per-row errors keep their stacked treatment on purpose: a field's error renders in its own cell
under the control, and the row's non-field errors render full width above the grid. An invalid row
is therefore taller than its neighbours. django-mvp's own comment on this is that an error breaking
no rhythm is an error nobody notices.

## R3 — adding and removing rows is provided; reordering is not

`mvp/static/js/formset.js` is 76 lines and registers two Alpine components. Adding clones a
`<template>`, replaces `__prefix__` with the running total, inserts the row and calls
`Alpine.initTree`. Removing sets `removed = true`, hides the row rather than detaching it — so a
removal survives an invalid submission — and binds the `DELETE` checkbox to that state through a
hidden input.

**Reordering has no support at all.** Searched for `can_order`, `ORDER`, `sortable`, `drag`,
`reorder`, `x-sort` and SortableJS across django-mvp's `mvp/`, `demo/`, `docs/` and `specs/`. There
are no drag handles, no up/down controls and no ORDER-aware markup. `@alpinejs/sort` was
deliberately removed from the bundle — the comment in `assets/js/index.js` says nothing in the
package used it and it cost a quarter of the built output, and that a project wanting `x-sort` adds
the plugin from its own base template.

Django's own `can_order` is reachable through the declaration's escape hatch,
`factory_kwargs = {"can_order": True}`, and django-mvp's formset documentation uses it as the
example of a setting with no shorthand. Nothing renders it specially, so an `ORDER` field appears as
an ordinary number input and becomes one more column heading.

**Decision this forces:** see plan D-4. Position is entered as a number, not dragged.

## R4 — nothing in django-mvp offers a filterable text input, and nothing needs to

Searched django-mvp for a combobox, autocomplete, typeahead, tag input or enhanced select:
`mvp/widgets.py` does not exist, `mvp/forms.py` is 27 lines holding one delete-confirmation form,
`mvp/static/js/` holds only the built bundle and `formset.js`, and `pyproject.toml`/`package.json`
name no Select2, Tom Select, Choices.js, Tagify or Fuse.js. `<datalist>` appears nowhere in the
repository. The bundled Alpine carries only `@alpinejs/persist`.

This looked like the feature's one external dependency. It is not, and the reason is the same
decision that made the completion field correct in the first place.

**A binding select would have needed a component. Completion needs an HTML element.** `<datalist>`
is native: a text input with an attached list of suggestions, filtered as the person types, where
accepting a suggestion writes its text into the input and nothing else happens. No record is
referenced, no identifier is posted, and a value not in the list is equally acceptable. That is
precisely the semantics D1 settled on, expressed in markup that ships with every browser and needs
no JavaScript, no styling and no library.

So the risk raised at the specification gate does not bite. It would have bitten a design that
asked the person to choose a person.

## R5 — how a partial date reaches a form, and what it does not check

`django-partial-date` 1.3.2 is two files. `PartialDateField` **does not define `formfield()`**, so
it inherits Django's default and produces a plain `CharField` with a `TextInput`. Its
`get_internal_type()` returns `"DateTimeField"`, which affects the column only.

The grammar is one regex: `^(?P<year>\d{4})(?:-(?P<month>\d{1,2}))?(?:-(?P<day>\d{1,2}))?$`.
Verified against a live model form:

| Input | Result |
|---|---|
| `2019` | stored, year precision |
| `2019-03` | stored, month precision |
| `2019-03-14` | stored, day precision |
| `2019-3` | stored as `2019-03`, month precision |
| `19`, `2019/03`, `2019-03-14T00:00`, `2019-13`, `2019-02-30` | rejected |

So FR-014 — a year, a year and month, or a full date, with no precision declared beforehand — is
what a plain text input over this field already does. A stored value renders back as its canonical
string, so what is displayed re-parses to the same value at the same precision.

An unparseable value raises `ValidationError` from `to_python` during the model's `full_clean()`,
which a model form runs in `_post_clean`, so it surfaces as an ordinary field error. The message is
`'%(value)s' is not a valid date string (YYYY, YYYY-MM, YYYY-MM-DD)`.

**Two defects in the library to design around, both confirmed by running them:**

- The precision setter calls `self._date.replace(day=1)` without assigning the result. `date.replace`
  is pure, so it is a no-op: a `PartialDate` built at year precision from a full date keeps the full
  date on `.date` while formatting as the year alone. Anything comparing `.date` sees the
  untruncated value.
- `__ge__` compares `self.date >= other.date and self.precision >= other.precision`, which is not a
  total order across precisions: neither `PartialDate("2020") > PartialDate("2019-05")` nor its
  reverse is true. **A begin-before-end check must not use the comparison operators.**

**And the gap FR-016 has to fill.** `ItemDate` defines no `clean()` and no `save()`, and its `Meta`
carries only the `(item, date_type)` uniqueness constraint. The `end` field's help text says "Must
not be set without begin" and nothing enforces it: a model form with `begin` empty and `end` set
validates, as does an `end` earlier than its `begin`. The export side assumes the invariant — it
emits `end` only when `begin` is not `None` — so an end-without-begin row silently loses its `end`
on export. That is a live data-loss path this feature closes.

## R6 — the type-to-field mapping cannot absorb date slots directly

`literature/ui/fieldgroups.py` holds three structures: `GROUPS` maps thirteen group names to tuples
of `Item` field names, `GROUP_LABELS` translates them, and `TYPE_GROUPS` maps each of the 45 item
types to the extra groups beyond an always-on baseline of `core` and `general`.

Four facts make "add the date slots to this mapping" the wrong shape:

1. `literature/ui/forms.py` builds `FORM_FIELDS` by flattening `GROUPS` and feeds it straight to
   `ItemForm.Meta.fields`. **A name in `GROUPS` that is not an `Item` column raises `FieldError` at
   class-definition time.** The date slots are rows in `ItemDate`, not columns on `Item`.
2. `tests/test_ui/test_fieldgroups.py` asserts the flattened `GROUPS` equals exactly `Item`'s scalar
   form fields. It exists so that a field added to the model later fails a test rather than
   vanishing from the form. Anything else added to `GROUPS` fails it immediately, correctly.
3. `field_group_context` in `literature/ui/views.py` resolves each group's names as
   `form[name]` — bound fields on `ItemForm`. A slot has no bound field there.
4. `groups_holding_values` reads `getattr(item, field_name, None)`. On a related name that returns a
   manager, which is never empty by its test, so any group naming one would be permanently visible.

**So the plan adds a sibling mapping in the same module rather than widening `GROUPS`** — see D-5.
The spec's FR-013 asks for the mapping "extended to cover date slots", and a second structure beside
the first, maintained under the same criteria and the same ADR, is that extension. Folding slots
into `GROUPS` is not.

ADR-0020 constrains how the new mapping is authored: every type entry carries a comment naming the
criterion that decided it, the evidence base is CSL's own appendices rather than any unlicensed
schema, and grouping is preferred to per-field lists because forty-five short lists can be argued
with and forty-five long ones cannot.

ADR-0021 constrains what it may do. Type scoping is presentation: the server never builds a
narrower form, every field is declared always and hidden client-side, so a hidden field keeps and
re-posts its value. That guarantee exists because `construct_instance` blanks a field the form
declares but the request omits. **Its stated revisit condition is a write path that is not the
rendered page — a partial update — and inline formsets over related rows are exactly that**, because
an omitted row means no row rather than a blanked column. The plan carries the guarantee into the
formsets explicitly rather than inheriting it: see D-6.

## R7 — the identifier validators, and why ISSN is out

`validate_identifier` dispatches on the type string through a plain dict keyed by the six
`IdentifierType` values, which are exact-case acronyms. A key that misses takes no validator at all,
which is how an unknown type is stored unchecked (ADR-0002). The lookup is therefore
**case-sensitive**: a type stored as `doi` is never validated today.

`ItemIdentifier` calls `validate_identifier` from both `clean()` and `save()`, so validation runs on
`full_clean()` and on every ordinary save. `bulk_create` bypasses it, deliberately and with a test
pinning that.

**ISBN separates cleanly.** `_isbn10_valid` and `_isbn13_valid` each begin with a standalone shape
regex and only then compute the checksum, returning `False` for both cases. The distinction exists
in the code and is thrown away one line before the `raise`. Recovering it changes no accepted or
rejected value. Two values in the existing invalid-value list are already commented as the
bad-check-digit case.

**ISSN does not separate, because there is nothing to separate.** `validate_issn` is one regex,
`^\d{4}-\d{3}[\dX]$`, and stops. The check character is named in the docstring and never verified,
so an ISSN of the right shape with a wrong check digit is **accepted today**. Distinguishing that
case means computing the checksum, which rejects values currently accepted — the one thing FR-029
and SC-005 forbid. `0000-000X` sits in the accepted-value test list and is not a valid ISSN by the
standard's arithmetic.

There is a second consumer to break: the RIS importer uses `validate_issn` and `validate_isbn` as
shape discriminators, routing an `SN` tag to whichever does not raise. Tightening ISSN moves where a
bad-check-digit value lands.

Hence the spec's refinement note, and issue #118.

**Messages.** All six are wrapped in `gettext_lazy`. No test in the repository asserts on message
text or on a `ValidationError` code for these validators — every negative test is a bare
`pytest.raises(ValidationError)`. The message change is therefore additive against the suite, and
the parametrised accepted/rejected value lists are the guard proving acceptance is unchanged.

**Where a message surfaces.** There is no form editing identifiers today, so the only current
surface is the import report: `_reason_for` joins `ValidationError.messages` and that string becomes
the report row's reason. Two importer paths swallow the message and use only raise-or-not — the
BibTeX identifier branch and the RIS `SN` discriminator — so neither is affected by wording.

**Translations.** One catalogue ships, `literature/locale/en/LC_MESSAGES/django.po`, every `msgstr`
empty, no `.mo` committed and no automation anywhere — no Makefile, no CI step, no pre-commit hook.
Changing a message breaks nothing at runtime, because gettext falls back to the source string, but
it leaves the catalogue stale with wrong line references. Regenerating is a manual
`django-admin makemessages -l en` and nothing will remind anyone, so it is an explicit task.

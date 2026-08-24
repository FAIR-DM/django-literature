# Progress — 011 Import a bibliography file through the front end

| When | Event |
|---|---|
| 2026-08-24 | Intake on issue #50. Four questions, all answered: report exists once and is not stored; the reader always lands on a report rather than a redirect with a summary; the entry point is an action in the catalogue toolbar rather than a control on every page; the import runs in the request, with background imports deferred to their own specification. |
| 2026-08-24 | Issue #50 accepted. |
| 2026-08-24 | `spec.md` and `decisions.md` written. Eleven further ambiguities resolved without escalating, recorded in the clarification scan and in nine numbered decisions. |
| 2026-08-24 | Branch `011-import-bibliography-file` pushed. Issue #50 promoted to the feature's parent issue; story sub-issues #100, #101, #102 created; draft PR #103 opened against the v1.0.0 milestone. Issue-title lint green. |
| 2026-08-24 | Specification gate: **approved** by Sam, in session, with no changes requested. |
| 2026-08-24 | Plan, research and task graph written. Core handle-type defect found and raised as #104; FR-023 narrowed (D11). |
| 2026-08-24 | Design review: approve with six findings, three of them medium. Two changed the design — the table view does have a supported way to add a toolbar action, so the table wrapper template is dropped, and the card list's block override must re-render the whole action row rather than replacing it. The unauthenticated, unbounded upload is recorded as an accepted specification-level risk (D12) rather than fixed. Research R2, the plan, the task graph and the documentation task amended. |

## 2026-08-24T13:13+02:00 · Implementer Phase 0 · T001

**Did:** Added `TestParseAcceptsEitherHandle` to `tests/test_importers/test_bibtex.py` — a binary
and a text read of `clean_multi_type.bib` must produce identical entry results, and
`latin1_encoded.bib`'s undecodable bytes must report a `ParseError` naming the encoding problem
rather than a `TypeError`. No production code touched.

**Verified:** `poetry run pytest tests/test_importers/test_bibtex.py -k TestParseAcceptsEitherHandle -v`
— 2 failed (exit 1), both for the reported reason: `TypeError: cannot use a string pattern on a
bytes-like object` at `bibtex.py:696`, matching research.md R1's measurement exactly.

**Next:** T002 — decode a bytes handle in `BibTeXFormat.parse`.

**Watch:** none.

## 2026-08-24T13:14+02:00 · Implementer Phase 0 · T002

**Did:** `BibTeXFormat.parse` now decodes a bytes handle with `utf-8-sig` before the existing
BibTeX-block check runs, raising the same shaped `ParseError` `RISFormat` already raises on
`UnicodeDecodeError`; a text handle passes through unchanged (the `isinstance(raw, bytes)` branch
is the only change).

**Verified:** `poetry run pytest tests/test_importers/test_bibtex.py -k TestParseAcceptsEitherHandle -v`
— 2 passed (exit 0). `poetry run pytest tests/test_importers/test_bibtex.py -q` — 243 passed (exit
0), confirming no regression in the file's other 241 tests.

**Next:** T003 — the mirror red test for RIS.

**Watch:** none.

## 2026-08-24T13:18+02:00 · Implementer Phase 0 · T003

**Did:** Added `fixture_text` (plain `utf-8`, no BOM-stripping) alongside the existing binary
`fixture` helper in `tests/test_importers/test_ris.py`, and `TestParseAcceptsEitherHandle` —
the mirror of `test_bibtex.py`'s class of the same name — asserting a binary and a text read of
`constructed/crlf_line_endings.ris` produce identical entry results. No production code touched.

**Verified:** `poetry run pytest tests/test_importers/test_ris.py -k TestParseAcceptsEitherHandle -v`
— 1 failed (exit 1), for the reported reason: `AttributeError: 'str' object has no attribute
'decode'` at `ris.py:117`, matching research.md R1's measurement exactly.

**Next:** T004 — accept a text read in `RISParser.parse`.

**Watch:** none.

## 2026-08-24T13:21+02:00 · Implementer Phase 0 · T004

**Did:** `RISParser.parse` now only decodes when the read is `bytes`; a `str` read passes through
unchanged. Amended the class's own docstring in place — it stated "Expects `file` opened in
**binary** mode" and cited spec 005's D19 for why — to say either mode is now accepted and name
D10 (this phase) as superseding D19 (mini-ADR: `decisions.md` D13).

**Verified:** `poetry run pytest tests/test_importers/test_ris.py -k TestParseAcceptsEitherHandle -v`
— 1 passed (exit 0). `poetry run pytest tests/test_importers/test_ris.py -q` — 343 passed (exit 0),
including the pre-existing `test_raises_parse_error_naming_the_encoding_and_offset_on_undecodable_bytes`,
confirming the binary decode-failure path is unaffected.

**Next:** T005 — `import_file`'s docstring in `base.py`, plus a `test_base.py` assertion that both
handle types reach `parse` unchanged.

**Watch:** none.

## 2026-08-24T13:25+02:00 · Implementer Phase 0 · T005

**Did:** Rewrote `import_file`'s `Args: file:` docstring line to say what is actually accepted —
text or binary, a shipped format decodes bytes itself (D10) — replacing "an open file object, or
anything with a `read()`". Added `TestHandleReachesParseUnchanged` to `tests/test_importers/test_base.py`,
parametrized over `io.StringIO`/`io.BytesIO`, asserting the exact object passed to `import_file`
is the exact object `parse` receives. No production behaviour changed — `import_file` already
passed `file` straight through with no decoding of its own — so this task is documentation plus a
regression test locking in existing correct behaviour, not a red/green pair.

**Verified:** `poetry run pytest tests/test_importers/test_base.py -k TestHandleReachesParseUnchanged -v`
— 2 passed (exit 0), immediately, as expected. `poetry run pytest tests/test_importers/test_base.py -q`
— 61 passed (exit 0). `poetry run pytest tests/test_importers/ -q` — 752 passed (exit 0).

**Next:** T006 — the CHANGELOG entry.

**Watch:** placing the new test class immediately before the pre-existing `TestOverridingImportEntry`
(a test I did not author) made that test fail — not from anything of mine, but because that test
calls `Item.objects.count()` with no `@pytest.mark.django_db` and no `db`-requiring fixture, and
only "passes" today by reusing a database connection a neighbouring `django_db`-marked class left
open; inserting an unmarked class between them breaks that reuse and exposes it. Per this phase's
prohibitions I did not touch that test. Worked around it by appending the new class at the end of
the file instead, where the full file (61 tests) and the whole `tests/test_importers/` directory
(752 tests) both pass. Flagged in the completion report's `concerns` for Forge to triage —
`TestOverridingImportEntry::test_overriding_import_entry_changes_only_that_step` is missing
`@pytest.mark.django_db` and its current pass is order-dependent, not correct in its own right.

## 2026-08-24T13:26+02:00 · Implementer Phase 0 · T006

**Did:** Added a `CHANGELOG.md` entry under `### Fixed`, matching its neighbour's shape (a lead
sentence naming the user-visible defect, then the mechanism, then the closing issue link), citing
issue #104.

Checked `docs/` for anything this phase's docstring changes made false. `docs/api/importers.md`
states nothing about handle type and its `## Reference` section auto-generates from
`literature.importers`'s own docstrings via Sphinx `automodule`, so it already inherits T005's
corrected wording with no manual edit needed. `docs/adr/0012-a-format-owns-its-own-decoding.md`
does make a claim this phase supersedes — "the format documents the mode it expects" and "two
formats may expect different modes" — but `docs/` is outside this phase's file scope
(prohibitions), so it is not edited; named in the completion report's `concerns` instead.

**Verified:** `poetry run pytest -q` — full suite, reported in the completion report below.

**Next:** none — Phase 0 complete.

**Watch:** the `TestOverridingImportEntry` ordering fragility noted at T005; ADR-0012's now-partly-
superseded claim, out of this phase's scope to fix.

## 2026-08-24T13:50+02:00 · Implementer Phase 1 · T101

**Did:** Added `TestImportForm` to `tests/test_ui/test_forms.py` — the format choice must be
exactly `available_formats()`'s own set, built at `__init__` time so a format configured after
import time still appears, both fields required, a submission with neither invalid with a reason
on each, and the form multipart.

**Verified:** `poetry run pytest tests/test_ui/test_forms.py::TestImportForm -v` — collection error
(exit 1): `ImportError: cannot import name 'ImportForm' from 'literature.ui.forms'`, the right
reason — the class does not exist yet.

**Next:** T102 — `ImportForm` itself.

**Watch:** none.

## 2026-08-24T13:52+02:00 · Implementer Phase 1 · T102

**Did:** Added `ImportForm(forms.Form)` to `literature/ui/forms.py` — a `ChoiceField` whose choices
are read from `available_formats()` inside `__init__` (never declared on the class, so a format
configured after import time still appears) and a `FileField`. Both carry translated `label`/
`help_text`.

**Verified:** `poetry run pytest tests/test_ui/test_forms.py -q` — 12 passed (exit 0), green T101.

**Next:** T103 — the report adapter's own red test.

**Watch:** the T102 progress entry above landed in the same commit as T101's rather than its own
(process slip, not a content error) — flagged in the completion report's `deviations`.

## 2026-08-24T13:58+02:00 · Implementer Phase 1 · T103

**Did:** Added `tests/test_ui/test_importing.py` — `TestImportReport` covers source order, position
as index+1, outcome carried through unchanged, citation key present/absent with the source's own
handle, reason present only on failures, a created row's item URL and a non-created row's absence
of one, and the created/skipped/failed/total counts against the result's own. `TestImportReportRow`
checks the row is frozen.

**Verified:** `poetry run pytest tests/test_ui/test_importing.py -v` — collection error (exit 1):
`ModuleNotFoundError: No module named 'literature.ui.importing'`, the right reason.

**Next:** T104 — `ImportReportRow` and `ImportReport`.

**Watch:** none.

## 2026-08-24T14:00+02:00 · Implementer Phase 1 · T104

**Did:** Added `literature/ui/importing.py` — `ImportReportRow` (frozen dataclass) and
`ImportReport`, wrapping an `ImportResult` and exposing `rows`, `created`, `skipped`, `failed` and
`total`. The item URL is resolved with `reverse("literature:item-detail", ...)` rather than
`item.get_absolute_url()` — `Item` has none (`literature/ui/views.py`'s own comment on
`ItemCreateView.success_url`).

**Verified:** `poetry run pytest tests/test_ui/test_importing.py -q` — 11 passed (exit 0), green T103.

**Next:** T105 — the report table's own red test.

**Watch:** none.

## 2026-08-24T14:10+02:00 · Implementer Phase 1 · T105

**Did:** Added `TestImportReportTable` to `tests/test_ui/test_tables.py` — a plain list of rows
with no queryset behind it, every column present, the outcome cell renders the outcome's own
translated label, a failure reason containing markup is escaped, a created row's position links to
the item while a failed row's does not, a created row with no citation key still links on its
position, and the citation key itself renders as plain text beside it.

**Verified:** `poetry run pytest tests/test_ui/test_tables.py::TestImportReportTable -v` —
collection error (exit 1): `ImportError: cannot import name 'ImportReportTable' from
'literature.ui.tables'`, the right reason.

## 2026-08-24T14:14+02:00 · Implementer Phase 1 · T106

**Did:** Added `ImportReportTable(tables.Table)` to `literature/ui/tables.py` — `position`
(linkified on `record.item_url`, so the link hangs on the position rather than the citation key,
AS-10), `citation_key`, `outcome` (`render_outcome` returns the label, not the stored value) and
`reason`. `Meta.orderable = False`: the report's order is fixed to the source file (FR-019), so no
header advertises a sort control that would not do anything.

**Verified:** `poetry run pytest tests/test_ui/test_tables.py -q` — 71 passed (exit 0), green T105
and every pre-existing test in the module.

**Next:** T107 — the import route's own red test.

**Watch:** none.

## 2026-08-24T14:22+02:00 · Implementer Phase 1 · T107

**Did:** Added `TestImportRouteReverses` to `tests/test_ui/test_urls.py` — the route reverses under
the `literature` namespace and resolves to `views.ItemImportView`.

**Verified:** `poetry run pytest tests/test_ui/test_urls.py::TestImportRouteReverses -v` — 2 failed
(exit 1): `NoReverseMatch: Reverse for 'item-import' not found` and a matching `Resolver404`, the
right reason — neither the route nor the view exists yet.

**Next:** T108 — the route itself.

**Watch:** none.

## 2026-08-24T14:24+02:00 · Implementer Phase 1 · T108

**Did:** Added `path("import/", views.ItemImportView.as_view(), name="item-import")` to
`literature/ui/urls.py`, ahead of the `<int:pk>/` patterns so it is never shadowed. Added
`"import": "literature:{model_name}-import"` to `CRUD_VIEWS`, matching the other four actions'
naming convention. Added a minimal `ItemImportView(MVPFormView)` stub (`model = Item`,
`list_view_title = CATALOGUE_TITLE`) so the route resolves to a real class — built out fully at
T110.

**Verified:** `poetry run pytest tests/test_ui/test_urls.py -q` — 16 passed (exit 0), green T107.
`poetry run pytest tests/test_ui/ -q` — 549 passed (exit 0), nothing else disturbed by the new
`CRUD_VIEWS` key (no view shows `import` yet, so `TestCRUDViewsReverse` does not iterate it).

**Next:** T109 — the import view's own red test.

**Watch:** none.

## 2026-08-24T14:35+02:00 · Implementer Phase 1 · T109

**Did:** Added `TestItemImportView` to `tests/test_ui/test_views.py` — GET renders the form with a
format choice and a file control; a valid BibTeX upload (`tests/data/publication.bib`) creates the
reference and responds 200 with a report, never a redirect; the response carries the counts and one
row per entry in source order; a created row links to its reference; the same shape uploaded as RIS
behaves the same way; a file mixing a converting entry with a failing one reports each correctly and
leaves the created one in the catalogue; the report carries no `page_obj` (not paginated).

**Verified:** `poetry run pytest tests/test_ui/test_views.py::TestItemImportView -v` — 7 failed
(exit 1), the right reason for six of them: `ItemImportView`'s stub carries no `form_class`, so
`get_form()` raises `TypeError: 'NoneType' object is not callable` on every POST, and GET 404s with
no template. Two design corrections made while writing the test, both recorded below rather than in
`decisions.md` (neither is a design choice, both are facts about existing code discovered while
building the fixture): `tests/data/publication.ris` cannot be used as the "same file as RIS" fixture
— its `Y2` tag ("1/26/2023") trips a pre-existing date-parsing defect in `literature.importers.ris`,
out of this phase's file scope to fix, so a minimal inline RIS entry is used instead. And a
BibTeX-side "mixed file" (one entry converting, one failing on a bad ISBN) does not actually fail —
`literature/converters.py`'s known-identifier lookup does not match bibtex.py's lowercase `isbn` key
against `IdentifierType.ISBN`, so it silently stores the identifier unvalidated as a custom type
instead of failing the entry (also out of scope, also a converters.py defect). The mixed-file
scenario instead uses RIS's own documented `EntryError` for a record missing its `TY` tag — a
genuine, contract-native single-entry failure, not a workaround.

**Next:** T110 — `ItemImportView` itself.

**Watch:** the `tests/data/publication.ris` date-parsing defect and the BibTeX/converters.py ISBN
identifier-type case mismatch are both flagged in the completion report's `concerns` — neither is
fixed here (prohibitions forbid touching `literature/importers/**` or `literature/converters.py`).

## 2026-08-24T14:45+02:00 · Implementer Phase 1 · T110

**Did:** Finished `ItemImportView(MVPFormView)` in `literature/ui/views.py` — `form_class =
ImportForm`, `template_name = "literature/ui/import_form.html"`. `form_valid` resolves the format
class through `get_format`, instantiates it (`get_format(name)().import_file(...)`, since
`get_format` returns the class and `import_file` is an instance method), and renders
`literature/ui/import_report.html` directly through `django.shortcuts.render` with an `ImportReport`
and an `ImportReportTable` in the context — never `redirect()`, never `get_success_url()`. Added the
two page templates (`import_form.html`, `import_report.html`) T112 was going to add anyway, because
T109's GET/POST scenarios cannot go green without a template to render; `import_form.html` overrides
only `form_view.html`'s `before_form` (the repeat-import warning) and `actions` (a single "Import"
submit) blocks, so the packaged multipart handling, field rendering and page chrome are untouched.
`import_report.html` extends `page_view.html` directly (neither a form nor a queryset-backed list)
and carries the counts, the table and a link back to the catalogue.

**Verified:** `poetry run pytest tests/test_ui/test_views.py::TestItemImportView -q` — 7 passed
(exit 0), green T109. `poetry run pytest tests/test_ui/ -q` — 562 passed (exit 0).

**Next:** T111 — the template-level red tests (the two pages already render; T111 is the i18n/
utility-class guard and the templates' own assertions).

**Watch:** none.

## 2026-08-24T14:55+02:00 · Implementer Phase 1 · T111/T112

**Did:** Widened `tests/test_ui/test_templates.py`'s `TEMPLATE_PATHS` to also glob
`literature/ui/templates/cotton/page/list/actions/*.html`, so the i18n and utility-class guards
reach the toolbar action component T114 adds — before this it only ever reached
`literature/ui/templates/literature/ui/*.html`. Added `TestImportFormPage` (multipart, a file
control, the repeat-import warning) and `TestImportReportPage` (the counts, the outcome table, a
link back to the catalogue, and no `<form>` at all — the surviving half of FR-023, an assertion of
absence).

**Verified:** `poetry run pytest tests/test_ui/test_templates.py -q` — 75 passed (exit 0), first run.
`poetry run pytest tests/test_ui/ -q` — 569 passed (exit 0).

**Next:** T113 — the toolbar action's own red test.

**Watch:** T111 and T112 land as one entry, not a red/green pair — every assertion passed on first
write. Both page templates were already built at T110, out of necessity: `ItemImportView`'s own
tests (T109) cannot pass without a template to render, and `MVPFormView` cannot render at all
without one (research.md R3). T111's genuinely new content — the widened glob — could not itself be
red either: the Cotton actions directory does not exist yet (`import.html` is T114's), so globbing
it returns an empty list rather than a collection error. Reported here rather than presented as a
red/green pair that did not happen (craft-tdd: "report what you executed, not what you believe").

## 2026-08-24T15:05+02:00 · Implementer Phase 1 · T113

**Did:** Added `TestCatalogueImportAction` to `tests/test_ui/test_views.py` — the table catalogue
carries a link to the import route, the card catalogue carries the same link, the contributor page
carries none, and both catalogues still render search, filter and create. Edited the one shipped
assertion the hazards name — `TestItemTableView::test_carries_search_and_filter_but_no_column_chooser`
— to expect `["search", "filter", "create", "import"]`, since the actions list genuinely gains a
member.

**Verified:** `poetry run pytest tests/test_ui/test_views.py::TestCatalogueImportAction "tests/test_ui/test_views.py::TestItemTableView::test_carries_search_and_filter_but_no_column_chooser" -q`
— 3 failed, 3 passed (exit 1). The right reason on all three: no view shows the import action yet,
so `directory.import_url` is absent and `table_actions` has no fourth member. The three that already
passed (create link, contributor page carrying nothing, and one of the "still renders search/filter"
pair) were already true before this task and stay true after it.

**Next:** T114 — the toolbar action itself.

**Watch:** none.

## 2026-08-24T15:15+02:00 · Implementer Phase 1 · T114

**Did:** `"import"` joined `CRUD_VIEWS`. `ItemTableView` gained `actions = [..., "import"]` (its own
hook, research R2) and `directory`/`show_import_action`. `ItemListView` gained `template_name =
"literature/ui/item_list_page.html"` (never on `CatalogueListMixin` — the contributor page composes
it too), `directory`/`show_import_action`, and a `list_actions` attribute
(`["search","sort","filter","create","import"]`) published into context. Both views also override
`get_url_kwargs()` for `"import"` — a genuine gap in django-mvp's own directory mechanism discovered
while wiring this, recorded as decisions.md D14. New templates:
`cotton/page/list/actions/import.html` (no icon — `BS5_ICONS` has no `upload`/`import` entry and
`EASY_ICONS_FAIL_SILENTLY` defaults to `settings.DEBUG`, unset/False in this suite, so an
unregistered name would raise rather than fail silently) and `item_list_page.html` (extends
`list_view.html`, overrides only `page.actions` against the full `list_actions`, never the import
link alone). Refreshed `TestPackagedChain::test_no_page_template_of_our_own_stands_in_for_a_packaged_one`'s
docstring per the task's own instruction, distinguishing `item_list_page.html` (a wrapper that
extends the packaged template) from the `item_list.html` the test guards against (one that would
stand in for it).

**Verified:** `poetry run pytest tests/test_ui/test_views.py::TestCatalogueImportAction "tests/test_ui/test_views.py::TestItemTableView::test_carries_search_and_filter_but_no_column_chooser" -q`
— 6 passed (exit 0), green T113. `poetry run pytest tests/test_ui/ -q` — 580 passed (exit 0).
`poetry run pytest -q` — 1764 passed (exit 0), full suite.

**Next:** none — Phase 1 complete pending final verification (pre-commit, `pytest tests/test_ui/`,
full suite once more).

**Watch:** the `get_url_kwargs()` fix (D14) forced a second shipped-test edit beyond the one the
hazards name — `TestCRUDViewsReverse::test_every_action_the_view_shows_reverses` mirrors
`CRUDDirectoryMixin`'s own "list/create take no pk" rule as a hardcoded set, independently of
`get_url_kwargs()`, and needed `"import"` added to stay a correct mirror rather than a stale one.
Flagged in the completion report's `deviations`, not folded in silently.

**Watch:** `BoundRow.get_cell()` (the helper every other class in this module uses) returns a
column's raw Python value with no escaping at all for a plain, unlinked column — escaping happens
only in the outer table template's `{{ cell }}`, or inside `format_html()` for a linkified column.
`ItemTable`'s own escaping tests only exercise a linkified column (`title`) and a `TemplateColumn`
(`contributors`), both of which escape through a different mechanism, so this did not surface there.
Discovered here because `reason` is a plain column; fixed by rendering the whole table through
`as_html()` and reading the cell back out of the real HTML, the same path a page actually renders.

## 2026-08-24T15:30+02:00 · Implementer Phase 2 · T201

**Did:** Added `TestItemImportViewRejects` to `tests/test_ui/test_views.py` — five cases: no file
attached, no format chosen, an empty file, a file the chosen format cannot read (RIS content posted
as bibtex), and undecodable bytes (posted as ris). Each asserts `response.status_code == 200`,
`Item.objects.count() == 0`, and a stated reason — either on `form.errors` (the first three) or on
the report's failed row (the last two).

**Verified:** `poetry run pytest tests/test_ui/test_views.py::TestItemImportViewRejects -v` — 5
passed (exit 0) on first write. Not RED: every case was already satisfied by existing behaviour, not
by anything this task wrote. Confirmed each is the right pass for the right reason rather than a
tautology, by printing the actual response content for all five cases outside pytest — `form.errors`
carries "This field is required." (no file, no format) and "The submitted file is empty." (empty
file); the report's single failed row carries "No BibTeX entries found. Is this a BibTeX file?"
(wrong format) and "Could not decode this file as utf-8: invalid byte at offset 0." (undecodable
bytes) — the exact messages `literature/importers/bibtex.py` and `ris.py` already raise. The
`logger.warning(..., exc_info=True)` traceback these last two print to the test log is expected
(hazards: "an assertion about the response, not about whether an exception was logged"), not a
failure.

**Why all five already pass:** Django's `forms.FileField` defaults `allow_empty_file=False` and
`required=True`, and `forms.ChoiceField` defaults `required=True` — `ImportForm` (T102) declares
neither field to override either default, so "no file", "no format" and "empty file" are all
rejected by Django's own form validation before the view's `form_valid` ever runs, and
`FormMixin.form_invalid` (inherited unchanged through `MVPFormView`'s MRO — confirmed no
`form_invalid` override exists anywhere in it) renders rather than redirects. "Wrong format" and
"undecodable bytes" are exactly what Phase 0's D10 fixed: both formats already turn a bad file into
one failed `EntryResult` with a reader-actionable reason, and `ItemImportView.form_valid` (T110)
already renders that as a report rather than letting anything escape.

**Next:** T202 — whatever T201 shows is missing. Nothing is.

**Watch:** none.

## 2026-08-24T15:32+02:00 · Implementer Phase 2 · T202

**Did:** Nothing in `literature/ui/views.py` or `forms.py`. T201's five cases were all green on
first write (see above) — the empty-file path the brief flagged as the expected gap turned out to
already be covered by `FileField`'s own `allow_empty_file=False` default, and `form_invalid`
already renders rather than redirects because nothing in `ItemImportView`'s MRO overrides it. Per
the brief's hazards, writing a validator for any of these five cases would be a second place the
rule lives, so none is written.

**Verified:** No new command — T201's own run above is the verification that nothing is missing.

**Next:** T203 — the form-errors-render-beside-their-fields test.

**Watch:** none.

## 2026-08-24T15:40+02:00 · Implementer Phase 2 · T203

**Did:** Added `TestImportFormPageFieldErrors` to `tests/test_ui/test_templates.py` — two cases (a
missing file, a missing format), each asserting the field's own crispy-tailwind error id
(`id="error_1_id_file"` / `id="error_1_id_format"`) is present in the response.

**Verified:** `poetry run pytest tests/test_ui/test_templates.py::TestImportFormPageFieldErrors -v`
— 2 passed (exit 0) on first write, for the reason recorded below rather than by chance.

**Why this was already true:** `import_form.html` (T110) overrides only `before_form` and `actions`
on `form_view.html` — never `formset`, which is what carries `<c-form.render />` (`cotton/form/
index.html`) through to `{{ form|crispy }}` (`cotton/form/render.html`). `item_form.html` reaches
crispy through a different route (`{{ field|as_crispy_field }}`, one call per field, since it
overrides `page.content` in full for its group-by-group layout — plan.md D-3), but both routes
terminate in the same `CRISPY_TEMPLATE_PACK = "tailwind"` field template, `crispy_tailwind/
templates/tailwind/layout/field_errors.html`, which is what actually mints `id="error_{n}_
{field.auto_id}"` beside the control. Confirmed by posting an invalid submission to the create page
(`literature:item-create`) outside pytest before writing this test: it renders `id="error_1_
id_type"` in the identical shape. Asserted against that id rather than the paragraph's `text-red-500
text-xs italic` classes — the id is crispy-tailwind's own field-association mechanism, the classes
are its swappable presentation.

**Next:** none — Phase 2 complete pending final verification.

**Watch:** none.

## 2026-08-24T16:05+02:00 · Implementer Phase 3 · T301

**Did:** Added `demo/seed/import-sample.bib` — three entries: `ImportFixtureAlpha2024` (`@report`,
French, an institution) and `ImportFixtureBeta2023` (`@unpublished`, no language) convert cleanly;
`ImportFixtureGamma2022` (`@article`) carries a 331-character `address`, over
`Item.publisher_place`'s 255-character limit, so it fails at `full_clean()`. None of the three
values collides with `demo/seed/catalogue.json` or with the specific strings
`walk_narrowed_catalogue`'s exact-membership assertions name (`demo/smoke.py:218-256`) — see D15 and
the completion report's `fixture_collision_check`.

**Verified:** Ran the fixture through `BibTeXFormat().import_file()` directly, against a migrated
`tests.settings` database, from a scratch `@pytest.mark.django_db` test written for this check only
and deleted afterwards (never committed): `poetry run pytest tests/test_demo/test_scratch_fixture_check.py -q -s`
printed `0 created ImportFixtureAlpha2024 None`, `1 created ImportFixtureBeta2023 None`,
`2 failed ImportFixtureGamma2022 Ensure this value has at most 255 characters (it has 331).`,
`3 skipped None None` (the leading `%`-comment header). Confirms the fixture produces exactly the
create/skip/fail mix `walk_import` (T304) will assert against.

**Next:** T302 — the two red tests (`TestMultipartEncoder`, `TestImportLinkPattern`).

**Watch:** none.

## 2026-08-24T16:12+02:00 · Implementer Phase 3 · T302

**Did:** Added `TestMultipartEncoder` and `TestImportLinkPattern` to `tests/test_demo/test_smoke.py`,
importing `encode_multipart` and `IMPORT_LINK_RE` from `demo.smoke` — neither exists yet.
`TestMultipartEncoder` round-trips an encoded body through `django.test.RequestFactory`, which
builds the same `WSGIRequest` a live view receives and parses `.POST`/`.FILES` from the body and
`Content-Type` header exactly as the demo server would. `TestImportLinkPattern` asserts the pattern
against markup `client.get(reverse("literature:item-list"))` really renders, the same discipline
`TestCreateLinkPattern` above it uses.

**Verified:** `poetry run pytest tests/test_demo/test_smoke.py -k "TestMultipartEncoder or TestImportLinkPattern" -v`
— collection error (exit 2): `ImportError: cannot import name 'IMPORT_LINK_RE' from 'demo.smoke'`.
Red for the right reason — neither new name exists in `demo/smoke.py` yet.

**Next:** T303 — `encode_multipart` and `IMPORT_LINK_RE` in `demo/smoke.py`. Green T302.

**Watch:** none.

## 2026-08-24T16:15+02:00 · Implementer Phase 3 · T303

**Did:** `demo/smoke.py`: `IMPORT_LINK_RE` beside `CREATE_LINK_RE` (same shape — href only, no
captured text), and `encode_multipart(fields, files)` beside `form_fields` — a second encoder for
the import form's file upload, which cannot ride inside `post`'s urlencoded body. `post` itself is
unchanged.

**Verified:** `poetry run pytest tests/test_demo/test_smoke.py -k "TestMultipartEncoder or TestImportLinkPattern" -v`
— 2 passed (exit 0). `poetry run pytest tests/test_demo/test_smoke.py -q` — 27 passed (exit 0), no
regression in the file's other 25 tests.

**Next:** T304 — `walk_import()`, wired into `run()` last.

**Watch:** none.

## 2026-08-24T16:30+02:00 · Implementer Phase 3 · T304

**Did:** `demo/smoke.py`: `DemoWalk.walk_import()` — follows `IMPORT_LINK_RE` from the already-fetched
catalogue body, reads the import form's fields, submits `demo/seed/import-sample.bib` through
`encode_multipart`, asserts the response lands back on the import URL itself (never a redirect, D1/
D11), asserts the report names both created citation keys and the failing one with its reason, then
re-fetches the catalogue and asserts both created titles are listed. Wired into `run()` last, after
`walk_write_pass` — the code comment states why (T301/T304 hazards: it leaves its references behind
and the catalogue accumulates across runs).

**Verified against a running demo**, `DEMO_DB_PATH=/tmp/demo-smoke-T304.sqlite3` (a scratch database,
never the developer's own):
- `poetry run python manage.py migrate -v0`
- `poetry run python manage.py seed_demo` — `seed_demo loaded 31 references from
  .../demo/seed/catalogue.json`
- `poetry run python manage.py runserver 127.0.0.1:8000 --noreload &`
- `poetry run python demo/smoke.py http://127.0.0.1:8000` — twice in a row, against the same,
  now-mutated database, to prove the persistence hazard T301/T304 name does not bite:
  - Run 1: `OK: walked the demo catalogue, its second page, a reference and a contributor,
    created/corrected/removed a reference, and imported a bibliography file, at
    http://127.0.0.1:8000` — exit 0.
  - Run 2 (against the database run 1 already left the fixture's references in): identical `OK`
    line, exit 0. `walk_narrowed_catalogue`'s exact-membership assertions did not fail on the second
    run, confirming the fixture collides with nothing it accumulates.

`poetry run pytest tests/test_demo/ -q` — 51 passed (exit 0), no regression.

**Next:** T305 — verify the guard fails when it should.

**Watch:** none.

## 2026-08-24T17:05+02:00 · Implementer Phase 3 · T305

**Did:** No file left changed — this task is verification only. Against a running demo
(`DEMO_DB_PATH=/tmp/demo-smoke-T304.sqlite3`, `manage.py runserver 127.0.0.1:8000 --noreload`,
restarted after each Python-code probe since `--noreload` caches imported modules; template edits
alone did not need a restart but one was taken anyway for certainty), three probes, each made,
observed failing, then reverted with `git checkout --` before the next:

1. **Removed the toolbar action** — `literature/ui/templates/cotton/page/list/actions/import.html`,
   `{% if directory.import_url %}` → `{% if False %}`. `poetry run python demo/smoke.py
   http://127.0.0.1:8000` → `FAILED: http://127.0.0.1:8000/catalogue/ [200]: no Import link on the
   catalogue list` (exit 1). Names exactly what was missing.
2. **Broke the import** — `literature/ui/views.py`, `ItemImportView.form_valid`:
   `format_class().import_file(form.cleaned_data["file"])` → `format_class().import_file(None)`.
   `poetry run python demo/smoke.py http://127.0.0.1:8000` → `FAILED:
   http://127.0.0.1:8000/catalogue/import/ [200]: the import report does not carry the fixture's
   created entry 'ImportFixtureAlpha2024'` (exit 1). The response itself stayed 200 — `import_file`
   catches the `AttributeError` a `None` file raises internally and reports one failed, handle-less
   entry rather than crashing (FR-014, `base.py::import_entries`) — so this genuinely exercises
   `walk_import`'s own content assertion, not just a status-code check (D1's own discipline).
3. **Emptied the report** — `literature/ui/importing.py`, `ImportReport.rows`:
   `return [self._row(entry) for entry in self.result]` → `return []`. `poetry run python
   demo/smoke.py http://127.0.0.1:8000` → `FAILED: http://127.0.0.1:8000/catalogue/import/ [200]:
   the import report does not carry the fixture's created entry 'ImportFixtureAlpha2024'` (exit 1).
   The summary counts (`report.created`/`.skipped`/`.failed`) read off `self.result` directly and
   stayed correct even with `rows` emptied — only the table went blank — so this is a genuine "the
   table lost its rows" defect, not a coincidence of the first assertion this probe happened to hit.

Each probe reverted with `git checkout -- <file>` immediately after its run, confirmed with `git
diff --stat` (empty) before the next probe started. After the third revert and a server restart,
`poetry run python demo/smoke.py http://127.0.0.1:8000` → the ordinary `OK` line, exit 0 — the walk
is not left in a broken state itself. Server stopped (`pkill -f "manage.py runserver
127.0.0.1:8000"`, confirmed no stray process with `ps aux | grep runserver`); scratch database and
server log removed (`rm -f /tmp/demo-smoke-T304.sqlite3 /tmp/demo-smoke-server.log`). Final `git
status --short` and `git diff --stat` in the worktree: both empty.

**Verified:** the three `FAILED` runs above, plus the final clean `OK` run and the empty `git
status`/`git diff` after every revert.

**Next:** none — Phase 3 complete pending final verification.

**Watch:** none.

## 2026-08-24T17:20+02:00 · Implementer Phase 4 · T401

**Did:** Added `docs/importing-through-the-interface.md` — reaching the page, choosing a format
and a file, what the report shows, then a "Before you upload" list covering the four things a
reader most needs to know: the format is chosen rather than detected, a repeat import creates the
references again, entries created before a failure stay created, and the import runs while the
reader waits with the host's own upload and request limits bounding a large file — plus D12's
plain statement that the page carries no permission check of its own. Added to the Getting Started
toctree in `docs/index.md`. Written from `literature/ui/views.py::ItemImportView`, `forms.py`,
`importing.py`, both page templates, `tests/test_ui/test_views.py::TestItemImportView` and
`::TestItemImportViewRejects`, and `decisions.md` D2/D3/D4/D5/D6/D9/D12 — no sentence describes
behaviour this run did not check against one of those.

**Verified:** every item on T401's own checklist is present in the page (recorded in the
completion report's `t401_checklist`). `poetry run sphinx-build -W --keep-going -b html docs
docs/_build/html` — exit 1, 38 warnings, identical set to a same-command baseline run taken before
this task on the unmodified worktree (`diff` of the two sorted warning lists is empty) — the new
page and toctree entry add no warning of their own; the 38 are pre-existing and out of this task's
scope (`docs/ROADMAP.md`'s three broken cross-references, the ADR/agents pages carrying no
toctree, one ambiguous `type` cross-reference, and `usage.md`'s dead link to `quickstart.md`).

**Next:** T402 — the README section.

**Watch:** the pre-existing 38 sphinx warnings are flagged in the completion report's `concerns`,
not fixed — none is caused by this run and fixing them is outside T401-T406's file scope.

## 2026-08-24T17:24+02:00 · Implementer Phase 4 · T402

**Did:** Added "Importing a bibliography file" to `README.md`, directly after "Adding, editing and
removing a reference," matching its neighbour's length and voice: what the Import action opens and
what submitting produces, that the format is chosen rather than detected, that a repeat import
creates the references again, that a partial failure leaves the earlier successes in place, and
that the page carries no permission check and no size limit of its own — echoing D12's own wording
for the size-limit claim.

**Verified:** read against `literature/ui/views.py::ItemImportView.form_valid`,
`tests/test_ui/test_views.py::TestItemImportView` (report shape, source order, position linking)
and `::TestItemImportViewRejects` (the wrong-format reason), and `decisions.md` D5/D6/D9/D12.

**Next:** T403 — the API reference entries.

**Watch:** the "Try it: the demo project" section below this one still only names the Add, Edit
and Delete actions as live, not Import — true before this task and unchanged by it, since T402's
acceptance is the new section only. Flagged in the completion report's `concerns` rather than
extended past scope.

## 2026-08-24T17:27+02:00 · Implementer Phase 4 · T403

**Did:** Added `## literature.ui.forms` and `## literature.ui.importing` to `docs/api/ui.md`,
after the existing `literature.ui.views` section, matching its shape — one description paragraph
then an `automodule` block. Content checked against `ImportForm.__init__` (choices read at
instantiation, not class-definition time) and `ImportReportRow`'s field list in `importing.py`.

**Verified:** `poetry run sphinx-build -W --keep-going -b html docs docs/_build/html` — exit 1, 38
warnings, identical set to the pre-run baseline (empty diff) — both `automodule` directives resolve
with no new warning.

**Next:** T404 — the pointer from the code-facing importers page.

**Watch:** none.

## 2026-08-24T17:29+02:00 · Implementer Phase 4 · T404

**Did:** Added one line to `docs/api/importers.md`, after its intro paragraph, naming that a
project with the `ui` extra can run the same import from the front end with no code of its own,
linking to `docs/importing-through-the-interface.md`.

**Verified:** `poetry run sphinx-build -W --keep-going -b html docs docs/_build/html` — exit 1, 38
warnings, identical set to the pre-run baseline (empty diff) — the new relative link resolves with
no new warning.

**Next:** T405 — the glossary entry.

**Watch:** none.

## 2026-08-24T17:31+02:00 · Implementer Phase 4 · T405

**Did:** Added an `### import report` entry to `CONTEXT.md`'s glossary, directly after `import
result / entry result`, in the established entry shape — defining it as the UI app's own rendering
of one import result (FR-037), numbered from one where the result itself is zero-based (D3), and
distinct from an import result as one interface's presentation of it rather than the contract's own
return value.

**Verified:** read against `literature/ui/importing.py::ImportReport`/`ImportReportRow` and
`decisions.md` D3; cross-checked the new entry's two internal references (`import result / entry
result`, `UI app`) both already exist as glossary terms in this file.

**Next:** T406 — the changelog entry.

**Watch:** none.

## 2026-08-24T17:33+02:00 · Implementer Phase 4 · T406

**Did:** Added an entry to `CHANGELOG.md`'s `## [Unreleased]` / `### Added`, ahead of the existing
"Searching and filtering the catalogue" entry, matching its shape — a bolded lead sentence, then
the behaviour a reader most needs before using the feature. No new runtime dependency line: `plan.md`'s
Summary states this feature adds none.

**Verified:** read against the same sources as T401/T402; no command run beyond composing and
proofreading the entry against the shipped behaviour.

**Next:** none — Phase 4 tasks complete. Remaining: docs build (already run and clean at each of
T401/T403/T404 above), full suite once, `pre-commit run --all-files`, `makemigrations --check`
across every app, and the completion report.

**Watch:** none.

## 2026-08-24T18:45+02:00 · Refinement

**Ledger backfilled.** Implementation of T001–T407 had landed and been committed while the ledger
stayed at PLAN with every task open. Repaired from the per-task entries above and the branch
commits, verified independently rather than asserted: lint, type checks, the full suite, the build,
the structure checks and the documentation checks all green. The three story completion comments
were also missing and have been posted.

**Documentation gate.** The 26 decision records were reachable from no navigation, which the gate
caught because this branch amended one of them. They now have an index page, listed explicitly
rather than by glob so that adding a record is a visible act.

**Specification refined and re-approved in session.** Three changes, from using the shipped pages:

1. Importing previews by default, with a control to carry out the previewed import and a checkbox to
   skip the preview. Reverses FR-030 and amends FR-031. The submitted file is staged between the two
   requests, its identity held in the session rather than in the page. Recorded as D16.
2. The report's presentation — colour-coded outcome badges, a back button with a backward arrow, an
   "import another file" button, the form above the results with a divider, and a *Retry* control
   disabled until the attachment changes. Recorded as D17.
3. A skipped entry may carry a reason, amending the import contract and so FR-028. Recorded as D18,
   tracked in its own right as #107.

Two behaviours were queried and are not defects: an unmapped entry type falls back to a generic
document rather than failing, which spec 004 settled as recovery over rejection; and a skipped entry
carried no reason, which was the contract's rule and is what change 3 fixes.

**Stories added:** #108 (US-4, preview) and #109 (US-5, skipped reason). The report's presentation is
a refinement of #100. 33 tasks across four phases.

**Next:** Phase 5.

## 2026-08-24T19:05+02:00 · Implementer Phase 5 · T501/T502

**Did:** `tests/test_ui/test_staging.py` (`TestStagedUpload`) written first — saving returns a token
and the bytes read back match; an unissued token reads as nothing; discard removes a staged file and
is a no-op on a token never staged; a file older than the retention window is swept and a fresh one
is not; sweeping with nothing staged yet does not raise; two uploads sharing both a name and their
bytes still get different tokens. Then `literature/ui/staging.py::StagedUpload` — save / open /
discard / sweep over `django.core.files.storage.default_storage` by default, staged under a
`literature-imports/` sub-path, tokens from `django.utils.crypto.get_random_string(43)`. No new
dependency. `RETENTION_WINDOW = timedelta(hours=24)` recorded as `decisions.md` D19 — no requirement
names a figure, so this is a judgement call written down rather than left silent.

**Verified:** `poetry run pytest tests/test_ui/test_staging.py -v` — red first (`ModuleNotFoundError:
No module named 'literature.ui.staging'`, the class not existing yet), then 7 passed after writing
the module. Nothing outside `tests/test_ui/test_staging.py` and `literature/ui/staging.py` touched.

**Next:** T503/T504 — the skip-preview control on `ImportForm`, and `ConfirmImportForm`.

**Watch:** `StagedUpload` has no idea which session issued a token — that scoping (FR-042) is the
view's job, exercised in `test_views.py`, not here.

## 2026-08-24T19:12+02:00 · Implementer Phase 5 · T503/T504

**Did:** `tests/test_ui/test_forms.py` gained `TestImportForm::test_carries_a_skip_preview_control_
unticked_by_default_and_not_required` and a new `TestConfirmImportForm` (carries no `file` field, no
`token` field, no field at all). Then `ImportForm` gained `skip_preview`
(`BooleanField(required=False, initial=False)`, FR-040) and `ConfirmImportForm(forms.Form)` — no
fields, since the staged file's token and format live in the session, never the page (FR-042,
decisions.md D16).

**Verified:** `poetry run pytest tests/test_ui/test_forms.py -q -k "skip_preview or
ConfirmImportForm"` — red first (`ImportError: cannot import name 'ConfirmImportForm'`), then the
whole file: 16 passed. `ruff check`/`ruff format` clean.

**Next:** T505/T506/T507 — the preview and confirm behaviour on the view.

**Watch:** none.

## 2026-08-24T19:38+02:00 · Implementer Phase 5 · T505/T506/T507/T508/T509

**Did:** `tests/test_ui/test_views.py` gained `TestItemImportPreview` (default submission imports
nothing and reports as a real import would, states nothing was imported, carries a confirm control,
the session holds the token and format, the page never carries the token, and a preview of a file
the chosen format cannot read is still labelled a preview but offers no confirm control — AS-12),
`TestItemImportConfirm` (confirming imports the staged file and matches the preview, the reader is
not asked for the file again, the staged file is gone afterwards, a session that staged nothing —
or a different session, or one whose staged file was already discarded — says "nothing to confirm"
and imports nothing, and a second confirmation of an already-confirmed token does the same), and
`TestItemImportSkipPreview` (ticking the control imports in one step, reports what was imported
rather than what would be, stages nothing).

Then `literature/ui/views.py`: `ItemImportView.dispatch()` sweeps abandoned stagings on every entry
to the view (T507's own requirement — removal after a successful confirm is not the only cleanup
path); `form_valid` stages the upload and runs `import_file(..., dry_run=True)` on the reopened
staged copy unless `skip_preview` is ticked, in which case it imports the uploaded file directly and
stages nothing. `IMPORT_TOKEN_SESSION_KEY`/`IMPORT_FORMAT_SESSION_KEY` are the only two places the
staged file's identity is written down — never the page, never `ConfirmImportForm` (FR-042). New
`ItemImportConfirmView` pops both from the session, opens the staged file if the token still
resolves to one, imports it for real, discards the staging, and renders the ordinary report; a token
that resolves to nothing (never staged, already confirmed, or swept) renders `nothing_to_confirm`
instead and imports nothing. New route `literature:item-import-confirm` in `urls.py`.
`import_report.html` now branches three ways (`nothing_to_confirm` / `preview` / an ordinary
completed report) sharing one template rather than three, and its confirm `<form>` only renders when
`report.created` is non-zero (AS-12 — nothing to carry out otherwise, though the preview label
itself still shows). `import_form.html`'s repeat-import warning was rewritten: its old wording
stated plainly that a submission imports directly, which decisions.md D16 makes false by default —
left unchanged it would have told a reader something the page no longer does.

**Verified:** `poetry run pytest tests/test_ui/test_views.py -k "TestItemImportPreview or
TestItemImportConfirm or TestItemImportSkipPreview"` — 11 of 16 red first (`NoReverseMatch` for
`item-import-confirm`, `KeyError` for the session keys, and the immediate-import assertions), then
16 passed after the view/template/urls work. `poetry run pytest tests/test_ui/` — 610 passed, 4
failed, all four foreseen and named below. `ruff check`/`ruff format` clean (one `# noqa: S105` on
`IMPORT_TOKEN_SESSION_KEY` — bandit's hardcoded-password heuristic matching a session key name, not
a secret). `DJANGO_SETTINGS_MODULE=demo.settings poetry run python manage.py makemigrations --check
--dry-run` — no changes detected.

**Next:** T510/T511 — the preview/confirm presentation tests and any template gap they find; T512
through T514 — the demo walk.

**Watch — four pre-existing tests are red, and were left untouched rather than edited:**

- `TestItemImportView::test_a_valid_bibtex_upload_creates_the_reference_and_responds_with_the_report`
- `TestItemImportView::test_a_created_row_links_to_its_reference`
- `TestItemImportView::test_a_file_mixing_a_converting_entry_with_a_failing_one_reports_each_correctly`
- `TestImportReportPage::test_carries_no_form_that_could_run_the_import_again`

Every one of them asserts the pre-refinement default — that submitting the import form imports
immediately and the report page carries no form — which FR-038 and FR-039 now make false by
definition: the default path previews (creates nothing) and, when it would create something, offers
a confirm `<form>`. There is no implementation that satisfies FR-038/FR-039 and also satisfies these
four assertions; the conflict is not a defect in this phase's work, it is the literal, named subject
of decisions.md D16 and D17. The brief for this run states plainly not to modify a pre-existing test
to make new work pass, so none of the four were touched. Each would go green again by adding
`"skip_preview": "on"` to its POST payload — restoring what it actually verifies, an immediate
one-step import — the same minimal, non-weakening shape decisions.md D14 used for the one shipped
test that phase's own work was sanctioned to touch. That sanction is not given here, so this is
reported rather than done. Full detail in the completion report.

**Fixed in the same commit — a leak, not a new task.** `ItemImportView.dispatch()` sweeps
`StagedUpload`'s storage directory on every request, so any test reaching the view at all — GET
included, and every pre-existing test in `TestItemImportView`/`TestItemImportViewRejects` reaches
it — now touches `default_storage`. With `MEDIA_ROOT` unset anywhere in the test settings, that
resolved to the process's own working directory, and a full-suite run left a `literature-imports/`
directory of real files sitting in the repository root afterwards (caught by `git status` after the
first full run, deleted, not committed). `tests/test_ui/conftest.py` gained an autouse
`_media_root_under_tmp_path` fixture pointing `MEDIA_ROOT` at `tmp_path` for every UI test, and the
three per-class copies of the same override added while writing T505/T506/T508 were removed as
redundant now that one fixture covers the whole directory.

## 2026-08-24T19:52+02:00 · Implementer Phase 5 · T510/T511

**Did:** `tests/test_ui/test_templates.py` gained `TestImportPreviewPage` — the preview is labelled
as one, states nothing has been imported, carries the confirm control (asserted on the form's
`action`, not just any `<form`), carries no token (the session's own token string is confirmed
absent from the body), and the report page after a real (skip-preview) import carries no confirm
control.

**Verified:** all five passed on first run — T507's own work already built the presentation these
tests check (`import_report.html`'s `preview`/`nothing_to_confirm` branches, `import_form.html`'s
warning), so there was nothing left for T511 to add. Recorded here rather than silently treated as
"nothing to do": these tests still needed writing test-first in the sense that they exist to lock
the behaviour in place, they simply did not have code missing under them when written. `poetry run
pytest tests/test_ui/test_templates.py -q` — 87 passed, 1 failed (the same, already-reported
`TestImportReportPage::test_carries_no_form_that_could_run_the_import_again`, no new failures).
`ruff check`/`ruff format` clean.

**Next:** T512/T513/T514 — the demo walk's preview step.

**Watch:** none new.

## 2026-08-24T20:10+02:00 · Implementer Phase 5 · T512/T513/T514

**Did:** `tests/test_demo/test_smoke.py` gained `TestConfirmImportPattern` — a preview really submitted
against the front end carries a `<form action="/catalogue/import/confirm/">`, matched by a new
`CONFIRM_IMPORT_RE` in `demo/smoke.py` (a form's `action`, not an `<a>`'s `href` — every other pattern
in the module is the latter). Then `demo/smoke.py::DemoWalk.walk_import()` rewritten for the two-step
flow: submit the fixture, assert the response lands directly and is labelled a preview, assert the
preview reports the same two created entries and the one failing entry with its own reason
(`_check_import_report()`, factored out since a preview and the real report both have to satisfy the
same three checks — decisions.md D15's fixture), assert the catalogue is still unchanged, follow the
preview's own confirm control (`CONFIRM_IMPORT_RE`, submitted with `form_fields()` off the preview
page — the confirm form is the only form the page carries, so this is the same "read the form"
discipline every other write step in the walk already uses), assert the same three checks against
the real report, then re-fetch the catalogue to confirm the references arrived.

**Verified:**
- `poetry run pytest tests/test_demo/test_smoke.py -q` — red first for `TestConfirmImportPattern`
  (`ImportError: cannot import name 'CONFIRM_IMPORT_RE'`), then 28 passed.
- Ran the walk against a live demo (`DEMO_DB_PATH` pointed at a scratch file, `manage.py migrate` +
  `seed_demo` + `runserver --settings=demo.settings`, `python demo/smoke.py http://…`) — passed
  clean: `OK: walked the demo catalogue, its second page, a reference and a contributor,
  created/corrected/removed a reference, and imported a bibliography file, at http://…`.
- T514, against the same live server: forced `preview = False` in `ItemImportView._render_report` —
  walk failed with `a default submission was not rendered as a preview`, naming exactly what broke.
  Restored, reran clean. Then forced the confirm branch to run `import_file(..., dry_run=True)`
  instead of a real import — walk failed with `the catalogue does not list the imported reference
  'Field Notes on Alpine Meltwater Monitoring'`. Restored (`git diff literature/ui/views.py` empty
  against the last commit before either sabotage), reran clean.
- `poetry run pytest -q` — 1802 passed, 4 failed (the same four, already reported, no new ones).
- `ruff check`/`ruff format` clean.

**Found and fixed along the way, not a separate task:** running the live demo surfaced the same
storage leak the test suite had, one layer up — `demo/settings.py` carried no `MEDIA_ROOT` of its
own, so a staged upload under `runserver` landed in the process's working directory (the repo root)
rather than anywhere the demo already cleans up. Added `MEDIA_ROOT = BASE_DIR / "demo" / "media"`,
which `.gitignore`'s existing `media/` entry already excludes. Separately, the same leak reappeared
in the test suite because `tests/test_demo/test_smoke.py`'s new test reaches the import view too, and
the autouse `MEDIA_ROOT` override T507 added lived only in `tests/test_ui/conftest.py` — moved to the
suite root `tests/conftest.py` so it covers every package that can reach a UI view, not just the one
that happened to need it first.

**Next:** Phase 5 complete. Full suite, pre-commit, and the completion report.

**Watch:** the four pre-existing failures from T505-T509 stand unchanged; nothing in T512-T514 alters
that picture.

## 2026-08-24T19:00+02:00 · Implementer Phase 6 · T601/T602

**Did:** `EntryResult.__post_init__` (`literature/importers/results.py`) relaxed for the skipped
outcome only (D18): a reason is now permitted, still optional, on `SKIPPED`; still forbidden on
`CREATED`; still required and non-blank on `FAILED` (unchanged). `test_results.py`'s
`test_reason_belongs_only_to_failure` — the one shipped test this phase's brief sanctions editing —
dropped `Outcome.SKIPPED` from its parametrize list, keeping `Outcome.CREATED`. Two new tests added:
a skipped entry may carry a reason, and one without a reason is still valid.

**Verified:** `poetry run pytest tests/test_importers/test_results.py::TestEntryResult -q` — red on
the new test before the guard change (`ValueError: only a failed entry result may carry a reason`),
21 passed after. `ruff check`/`ruff format` clean.

**Next:** T603/T604 — both shipped formats name what they skipped.

**Watch:** none new.

## 2026-08-24T19:20+02:00 · Implementer Phase 6 · T603/T604/T605

**Did:** Two new tests per format asserting a skipped entry's reason names what was skipped:
`test_bibtex.py::TestBlocks` for a `@preamble` and a `@comment` block, `test_ris.py` for header
material (`TestWholeFileOutcomes`) and a `TY`-only entry (`TestTyOnlySkipped`). Both red for the
right reason (`reason` was `None`). Then: `bibtex.py` gained `_NonRecord(kind, text)`, wrapping
`database.preambles`/`database.comments` so `to_csl_json` can tell a comment from a preamble — they
were indistinguishable plain strings before, since `bibtexparser` merges anything outside a block
into one flat list per kind. `ris.py`'s two `to_csl_json` `SkipEntry` sites (header material, a
`TY`-only entry) each gained a message naming what was skipped. `base.py`'s `import_entry` now
carries a caught `SkipEntry`'s message onto `entry_skipped`'s `reason` via a new `_skip_reason()`
helper (parallel to the existing `_reason_for()`, but message-less stays `None` rather than being
padded with the exception's type — skipping is not a failure that needs explaining).
`import_entries`'s separate reader-stage `SkipEntry` handling is deliberately left alone: neither
shipped format raises from there.

**Verified:** `poetry run pytest tests/test_importers/test_bibtex.py -q` — 245 passed.
`poetry run pytest tests/test_importers/test_ris.py -q` — 345 passed. `ruff check`/`ruff format`/
`mypy` clean on the three changed modules.

**Found and reported, not fixed:** `poetry run pytest tests/test_importers/test_base.py -q` — 1
failed: `TestReporting::test_skipped_is_distinguishable_from_failed` asserts
`result.skipped[0].reason is None` against a `SkipEntry("a comment")` raised by the generic test
double `make_echo_format`, through the exact runner path this task widens. This is not the test the
brief's hazards sanction editing, and there is no way to carry a real format's `SkipEntry` message
through `import_entry` without also carrying this test double's — recorded as D21 rather than
edited.

**Next:** T606/T607 — the report renders a skipped row's reason.

**Watch:** the one new red test above (D21); everything else from earlier phases unchanged.

## 2026-08-24T19:40+02:00 · Implementer Phase 6 · T606/T607

**Did:** One new test in each of `test_importing.py` (`ImportReport`'s row carries a skipped entry's
reason through) and `test_tables.py` (a skipped row's reason renders in `ImportReportTable`'s
existing `reason` column). Both passed on first run: `ImportReportRow`'s `reason=entry.reason` and
the table's `reason` column never branched on outcome, so once T602 permitted a reason on `SKIPPED`
the front end already carried and rendered it — T607 needed no code change in `literature/ui/`.
Recorded here rather than silently treated as nothing to do (the same call T511 made in Phase 5).

**Verified:** `poetry run pytest tests/test_ui/test_importing.py tests/test_ui/test_tables.py -q` —
21 passed. `ruff check`/`ruff format` clean.

**Next:** T608 — the decision record and changelog entry.

**Watch:** unchanged from the previous entry.

## 2026-08-24T20:00+02:00 · Implementer Phase 6 · T608

**Did:** `docs/adr/0027-a-skipped-entry-may-carry-a-reason.md`, added to `docs/adr/index.md`'s
toctree. Cites issue #107 and the amended FR-028, states the reader-stage carve-out (D18's own
wording — "no existing caller can be reading it" — undersold `test_base.py`'s generic test double,
which is exactly such a caller for the conversion-stage path this phase does widen). `CHANGELOG.md`
gained a `### Changed` entry under `[Unreleased]` citing #107. `decisions.md` gained D21, recording
the `test_base.py` finding from T603-605 with the reasoning for reporting it rather than fixing it,
mirroring D20's own precedent for exactly this situation.

**Verified:** `poetry run pytest -q` — 1812 passed, 1 failed (`test_skipped_is_distinguishable_from_failed`,
D21, unchanged from the previous entry — no new failures). `poetry run pre-commit run --all-files` —
clean (trim trailing whitespace, end-of-file, check yaml, poetry-check, ruff lint, ruff format, mypy,
deptry all passed). `DJANGO_SETTINGS_MODULE=demo.settings poetry run python manage.py makemigrations
--check --dry-run` — "No changes detected", exit 0.

**Next:** Phase 6 complete pending review of D21's finding.

**Watch:** D21 — one pre-existing test (`test_base.py::TestReporting::test_skipped_is_distinguishable_from_failed`)
is red, by design of this phase's own sanctioned change, and not authorized for this phase to fix.

## 2026-08-24T20:20+02:00 · Implementer Phase 7 · T701/T702

**Did:** `TestOutcomeColumn` (`tests/test_ui/test_tables.py`) — the three outcomes render three
distinct `<c-badge>` variants, asserted on the variant (`badge-success`/`badge-warning`/`badge-error`)
and on distinctness, never on a colour name (hazards). Red first: the outcome cell carried plain
text, no `badge-` token anywhere. `ImportReportTable`'s `outcome` column is now `OutcomeColumn`, a
`TemplateColumn` in the same shape as `ContributorsColumn`/`IssuedColumn`, rendering a new
`table_outcome.html` around the outcome's own translated label — the settled mapping (created =
success, skipped = warning, failed = error) lives on the column as `VARIANTS`, keyed by `Outcome`.
`render_outcome` is gone from `ImportReportTable`: a `TemplateColumn` never calls a table's
`render_<name>`, the same reason `ItemTable` carries no `render_contributors`/`render_issued`, so
the label's translation now happens where `get_context_data` reads `record.outcome.label` instead.

**Verified:** `poetry run pytest tests/test_ui/test_tables.py -q` — 77 passed. `poetry run ruff check`/
`ruff format --check` on `literature/ui/tables.py` and the test module — clean.

**Next:** T703/T704 — the report page's own presentation.

**Watch:** nothing outstanding from earlier phases — D21 was resolved by D22 before this phase began.

## 2026-08-24T20:40+02:00 · Implementer Phase 7 · T703/T704

**Did:** The report page (`import_report.html`) now carries the upload form above the results, with
a divider between them (decisions.md D17); a back-to-catalogue button with a backward arrow and a
second button to an empty import form (FR-021), replacing the bare `<c-link>`; and, where the
submitted file could not be read at all, the upload form's submit control reads *Retry* and stays
disabled (a static `disabled` plus `x-bind:disabled="!form.fileChanged"`) until the attachment
changes (`@change` on the form, delegated rather than bound to the file input directly, since
crispy renders that field and this phase does not touch `forms.py`) — FR-023a.

Two things this task worked out rather than invented, per hazards: which report is the *whole file
unreadable* one, and which of the two forms a `ConfirmImportForm`/`ImportForm`-shaped `form` context
variable is. Neither `ImportReportRow` nor `ImportReport` carries a flag for "unreadable" — a
whole-file `ParseError` is folded into the run as one synthetic failed entry and nothing else
(`literature/importers/base.py` `import_entries`), so `report.total == 1 and report.failed == 1` is
the shape already available to key on, and it is true of no other outcome mix. And
`{% if form.fields.file %}` is what tells `ImportForm` (has one) apart from `ConfirmImportForm` (has
none) without a new context variable — `ItemImportView` always supplies the former (the preview
state, and an ordinary report reached by skipping the preview), `ItemImportConfirmView` always
supplies the latter, so the upload form appears in the two states the first view renders and not in
the two the second one does.

**Found and reported, not fixed — decisions.md D23:** two pre-existing tests in
`tests/test_ui/test_views.py` assert the opposite of what T703/T704 now build, both written before
D17: `TestItemImportPreview::test_a_preview_of_a_file_the_chosen_format_cannot_read_offers_no_confirmation`
(line 1699, `assert "<form" not in content`) is exactly the Retry scenario, and
`TestItemImportSkipPreview::test_the_report_describes_what_was_imported_rather_than_what_would_be`
(line 1791, same assertion) is the ordinary report a skip-preview submission produces. Neither is
edited — the same guardrail D20/D21 record, and this phase's own prohibitions withhold the
authorization to adjudicate a casualty of a sanctioned change. D23 also names the gap the
`views.py` prohibition leaves: an ordinary report reached by *confirming* a preview never gets the
upload form, since `ItemImportConfirmView` never hands the template an `ImportForm`-shaped `form`.

New assertions in `tests/test_ui/test_templates.py`: `TestImportReportPage` gained three (form above
results with a divider, the back button's arrow, the second button's href), `TestImportPreviewPage`
gained one (both forms present, neither's presence displacing the other), and a new
`TestImportReportRetryState` (five tests) covers the Retry label, its starting-disabled state, the
Alpine wiring being present in the markup (not executed — the Django test client renders markup, it
does not run Alpine), and that a file which *did* read with a mix of created and failed entries
reads *Import*, never *Retry*.

**Verified:** `poetry run pytest tests/test_ui/test_templates.py tests/test_ui/test_tables.py -q` —
177 passed. `poetry run ruff check`/`ruff format --check` on the changed template's sibling test
module — clean (`ruff` does not lint `.html`).

**Next:** T705 — re-run the i18n and utility-class guards over every template this phase touched.

**Watch:** D23 (new) — the two `test_views.py` failures above, and the `ItemImportConfirmView` gap.

## 2026-08-24T20:50+02:00 · Implementer Phase 7 · T705

**Did:** Re-ran `TestUtilityClassAllowlist` and `TestI18nGuard` (`tests/test_ui/test_templates.py`)
— both discover templates by globbing `literature/ui/templates/literature/ui/*.html`, so the new
`table_outcome.html` and the edited `import_report.html` are covered without any change to the
guards themselves. No code change: both classes were already green against this phase's templates.

**Verified:** `poetry run pytest tests/test_ui/test_templates.py -q -k "Guard or Allowlist"` — 72
passed.

**Next:** Phase 7 exit checks.

**Watch:** unchanged — D23.

## 2026-08-24T21:00+02:00 · Implementer Phase 7 · exit

**Did:** Phase exit verification.

**Verified:** `poetry run pytest -q` — 1828 passed, 2 failed (D23's two `test_views.py` tests,
exactly as reported — no other regressions; D21 was already resolved by D22 before this phase
began, so this phase's own two are the only known-red tests in the suite). `poetry run pre-commit
run --all-files` — clean (trim trailing whitespace, end-of-file, check yaml, poetry-check, ruff
lint, ruff format, mypy, deptry all passed). `DJANGO_SETTINGS_MODULE=demo.settings poetry run
python manage.py makemigrations --check --dry-run` — "No changes detected", exit 0 (this phase
ships no migration, per prohibitions). `poetry run python demo/smoke.py` against a locally seeded
and served demo — walked clean, including the import pass: the preview page's confirm step posts
`form_fields(preview_body)`, which after this phase now reads the *first* `<form>` on the page (the
new upload form, not the confirm form) — harmless in practice, since `ConfirmImportForm` declares no
field and ignores whatever extra keys a POST carries, but noted here because it is a real change in
what that helper now extracts, confirmed by running the walk rather than by inspection alone.

**Next:** Phase 7 complete pending review of D23's finding.

**Watch:** D23 — the two `test_views.py` failures, and the `ItemImportConfirmView` gap, both named
above with file, line and cause.

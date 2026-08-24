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

**Watch:** `BoundRow.get_cell()` (the helper every other class in this module uses) returns a
column's raw Python value with no escaping at all for a plain, unlinked column — escaping happens
only in the outer table template's `{{ cell }}`, or inside `format_html()` for a linkified column.
`ItemTable`'s own escaping tests only exercise a linkified column (`title`) and a `TemplateColumn`
(`contributors`), both of which escape through a different mechanism, so this did not surface there.
Discovered here because `reason` is a plain column; fixed by rendering the whole table through
`as_html()` and reading the cell back out of the real HTML, the same path a page actually renders.

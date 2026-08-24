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

**Next:** T106 — `ImportReportTable`.

**Watch:** `BoundRow.get_cell()` (the helper every other class in this module uses) returns a
column's raw Python value with no escaping at all for a plain, unlinked column — escaping happens
only in the outer table template's `{{ cell }}`, or inside `format_html()` for a linkified column.
`ItemTable`'s own escaping tests only exercise a linkified column (`title`) and a `TemplateColumn`
(`contributors`), both of which escape through a different mechanism, so this did not surface there.
Discovered here because `reason` is a plain column; fixed by rendering the whole table through
`as_html()` and reading the cell back out of the real HTML, the same path a page actually renders.

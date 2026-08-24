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

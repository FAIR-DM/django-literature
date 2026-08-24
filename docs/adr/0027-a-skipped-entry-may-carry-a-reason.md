# ADR-0027 — A skipped entry may carry a reason

- **Status:** Accepted
- **Context date:** spec 011 (FR-018, amended FR-028), `literature/importers/results.py`, issue #107,
  issue #109

## Context

The import contract set a reason if and only if an entry's outcome was `FAILED`, and
`EntryResult.__post_init__` raised if a skipped entry carried one at all. That rule read as a
reasonable reading of "a reason explains a problem" when it was written.

Importing a file with a truncated record showed the reading was too narrow. A BibTeX `@comment` or
`@preamble` block, RIS header material before the first record, and an RIS entry whose only tag is
`TY` are none of them failures — nothing is wrong and nothing is stored — but every one of them is
something the format specifically recognised and specifically declined to store, for a reason the
format already knows. The old contract had nowhere to put that reason, so the report showed a row
with no citation key and no explanation: a skip a reader cannot act on or even interpret, which is
the outcome this whole feature exists to prevent.

## Decision

`EntryResult` now permits a reason on a `SKIPPED` outcome. It remains optional there — a format
that skips something for a reason it cannot name still produces a valid result with `reason=None`
— and remains forbidden on `CREATED`, which is unchanged. Both shipped formats now supply one:

- `BibTeXFormat` names a `@comment` block and a `@preamble` block distinctly.
- `RISFormat` names header material before the first record, and an entry carrying only a `TY` tag
  and no other content.

The runner carries a `SkipEntry`'s message onto the skipped entry's reason where the format supplied
one, the same handling `EntryError`'s message already receives for a failure. Both places a format
can raise `SkipEntry` do this: `BibFormat.import_entry`, for the conversion stage both shipped
formats use, and `BibFormat.import_entries`, for a format that raises while the file is still being
read. Whoever reads the report should not be able to tell which of the two recognised the element,
only what was skipped and why.

This changes the import contract, which FR-028 forbade changing outside a recorded decision. FR-028
is amended rather than worked around: the change is additive (a reason on a skipped entry is a field
that was previously always absent), and the invariant that a created entry carries none is
untouched.

The alternative — the front end inventing its own words for a skipped row — was rejected outright.
It would mean the interface stating an explanation the importer never gave, which is worse than
saying nothing.

## Consequences

- A skipped row in the import report renders its reason in the same column a failed row's reason
  already uses (`literature/ui/tables.py`'s `ImportReportTable.reason`, `literature/ui/importing.py`'s
  `ImportReportRow.reason`) — neither needed a code change, since neither ever branched on outcome to
  decide whether to carry a reason through.
- A format with an unusual `SkipEntry` may still leave the reason `None`; nothing requires one.
- Two tests in `tests/test_importers/` asserted the old invariant directly and were written before
  this decision, so both were reconciled with the wider contract rather than worked around:
  `test_results.py`'s `test_reason_belongs_only_to_failure` no longer covers the skipped outcome,
  and `test_base.py`'s `test_skipped_is_distinguishable_from_failed` now expects the reason its own
  test double supplies. Neither test's purpose changed; each still holds a created entry to the old
  rule and still separates a skip from a failure.

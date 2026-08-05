# Constructed RIS corpus

One file per malformation named in spec.md's Edge Cases and Requirements, so a failing test points
at the rule it broke rather than at a file with several problems in it (the same convention
`tests/fixtures/bibtex/README.md` uses for BibTeX).

| File | Isolates |
| --- | --- |
| `empty.ris` | An empty file — a successful import of nothing (spec Edge Cases). |
| `missing_final_er.ris` | The final entry's closing `ER` tag is absent; still recovered (FR-006). |
| `no_ty_anywhere.ris` | RIS tag lines present, no `TY` anywhere — a parse failure naming the missing tag (FR-008a). |
| `tag_block_no_ty_after_valid_entry.ris` | A block of tags with no `TY`, after the first entry has been seen — a malformed entry, not header material (FR-009, D4). |
| `header_before_first_entry.ris` | Banner material before the first `TY` — skipped, not failed, whatever its shape (FR-008, D4). |
| `byte_order_mark.ris` | A UTF-8 byte-order mark — imports normally (spec Edge Cases). |
| `crlf_line_endings.ris` | CRLF line endings throughout (FR-010). |
| `single_space_separator.ris` | The single-space `TAG - value` variant rather than the two-space one (FR-010). |
| `wrapped_prose.ris` | A scalar/prose tag (`TI`, `AB`) continued on indented untagged lines, joined with a single space (FR-007 amended). |
| `endnote_multivalue_continuation.ris` | A repeatable tag (`KW`, `SN`) continued on unindented untagged lines, each becoming another value (FR-007 amended, research R7). |
| `ty_only.ris` | An entry carrying a reference type and nothing else — skipped (spec Edge Cases). |
| `truncated_final_entry.ris` | A file cut off mid-entry; the entries before the cut are recovered (spec Edge Cases). |
| `cp1252_encoded.ris` | Bytes this decoder cannot read as `utf-8-sig` — a parse failure naming the encoding (FR-034, spec Edge Cases). |
| `long_unmapped_tag_value.ris` | A non-standard tag carrying a value over 500 characters, the `ItemIdentifier.value` cap a flat preservation write would hit (plan.md "Preservation"). |
| `bulk_several_hundred_entries.ris` | Several hundred entries — the file FR-004's whole-file-materialisation claim is asserted against. |
| `chapter_with_editors.ris` | A chapter carrying its book's editors in `A2` and the book title in `T2`. Not a malformation: it substitutes for a genuine chapter export, which no vendorable corpus supplies (spec.md *Verification corpus*, T002). |

Every file here is written by hand. None is presented as a genuine export — see `../genuine/` for
those.

One of them stands in for an export rather than isolating a malformation. `chapter_with_editors.ris`
exists because every record in all twenty-five CC0 baselines is a journal article, and the two
corpora that do carry genuine chapter records are GPL-3.0, which this MIT-licensed package cannot
redistribute. It is written in EndNote's shape — tags in alphabetical order after `TY`, unindented
`KW` continuation lines, a trailing `ID`, no byte-order mark — because EndNote is the producer whose
genuine file leaves the gap. Its bibliographic content is its own; nothing was copied out of a
licensed corpus.

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
| `equivalence_scopus.ris` | The matched ten references in Scopus's tag ordering and encodings. Not a malformation: it substitutes for a genuine Scopus export of those references, which upstream does not publish (spec.md *Verification corpus*, T028). |
| `equivalence_webofscience.ris` | The same ten in Web of Science's shape, for the same reason. |
| `control_characters_in_values.ris` | A null byte and other C0 control characters embedded inside otherwise well-formed field values — recovered rather than crashing the parser or the mapping (FR-035, T038). |
| `injection_looking_values.ris` | Field values shaped like a SQL statement, an HTML/JS payload, a format-string gadget, and shell/path-traversal syntax — stored as inert text, never interpreted (FR-035, SC-008, T038). |

Every file here is written by this project — by hand, except the two equivalence fixtures, which are
derived mechanically from a genuine file as described below. None is presented as a genuine
export — see `../genuine/` for
those.

Three of them stand in for an export rather than isolating a malformation. `chapter_with_editors.ris`
exists because every record in all twenty-five CC0 baselines is a journal article, and the two
corpora that do carry genuine chapter records are GPL-3.0, which this MIT-licensed package cannot
redistribute. It is written in EndNote's shape — tags in alphabetical order after `TY`, unindented
`KW` continuation lines, a trailing `ID`, no byte-order mark — because EndNote is the producer whose
genuine file leaves the gap. Its bibliographic content is its own; nothing was copied out of a
licensed corpus.

`equivalence_scopus.ris` and `equivalence_webofscience.ris` are the second and third files here that
stand in for an export. SC-005 judges that the same references, exported by EndNote, Web of Science
and Scopus, produce equivalent catalogue items — and the CC0 corpus turns out to publish Scopus and
Web of Science exports of entirely different reference sets, not of the ten `../genuine/endnote.ris`
holds (`../genuine/SOURCE.md`, decisions.md D36). Genuine equivalence therefore runs over
`endnote.ris` and `mendeley.ris`, and these two carry the two supported producers that have no
matched genuine export.

Both were derived mechanically from `../genuine/endnote.ris`'s ten records rather than written by
hand, so no bibliographic value differs from the genuine file except where the producer's own
encoding differs. Each carries the fields SC-005 judges — reference type, contributors in order,
dates, identifiers, and the container — re-encoded in its producer's conventions, taken from that
producer's genuine file rather than from documentation:

- **Scopus:** a byte-order mark, `TY`/`AU`/`TI`/`PY`/`T2`/`VL`/`IS`/`DO` ordering, `DB  - Scopus`,
  and `SN  - NNNNNNNN (ISSN)` with the hyphen stripped and the annotation appended.
- **Web of Science:** a byte-order mark, `J9`/`JI` alongside `T2`, `WE  - Science Citation Index
  Expanded (SCI-EXPANDED)`, no `UR` and no `DB`.

Nothing is invented. Neither file carries a Scopus record URI or a `WOS:` accession number, because
those are values that would have to be fabricated rather than re-encoded, and a fixture asserting
equivalence must not contain data no source supplied.

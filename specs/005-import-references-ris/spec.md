# Feature Specification: Import References from RIS Files

**Feature Branch**: `005-import-references-ris`

**Created**: 2026-08-05

**Status**: Draft

**Serves**: G5 (import references from common bibliography formats) · Roadmap R5 · Issue #23

**Input**: RIS is the other format researchers meet constantly. It is what Scopus and Web of Science hand back when a set of search results is downloaded, and often the only option offered. Someone who can already bring in a saved BibTeX library still cannot bring in the search results they exported this morning, which is the more common way a literature review actually starts. This feature reads a `.ris` file directly, with the same care for entries that do not fit the store cleanly, and it is the second real format the import contract has to carry.

## Clarifications

### Session 2026-08-05 — intake

- Q: RIS entries carry no cite key, but the catalogue requires a citation key and refuses a CSL JSON record that supplies neither `citation-key` nor `id`. Every RIS entry would fail on the existing conversion path. What becomes the citation key? → A: The format mints one from the entry's own content, in the author-year-title shape reference managers themselves use, and takes the file's `ID` tag verbatim where one is present. An entry too sparse to mint from falls back to its position in the file. Batch-scoped de-duplication then resolves collisions, which are common in a single-group export where several papers share an author and a year.
- Q: A minted key is a handle the package invented rather than one the researcher's reference manager gave them. Is that acceptable, or should entries without an `ID` be refused? → A: Minting is correct and refusing is not. Refusing would fail most real Scopus and Web of Science exports outright, which is the case this feature exists for. Matching an entry against what is already stored is explicitly not attempted: importing the same file twice creates duplicates, exactly as established reference managers behave. Selecting a citation-key style, regenerating keys, and de-duplication are all later features, and none of them is assumed here.
- Q: RIS has no specified dialects the way BibTeX has classic and BibLaTeX. The 1980s Reference Manager specification is the only written standard and every producer since has diverged from it in undocumented ways, most sharply in the contributor tags. What does acceptance mean when there is no document to be correct against? → A: Acceptance names the exports it reads. EndNote is the primary support target, with Web of Science and Scopus secondary, judged against real exports committed to the repository. Tags outside what those producers use are read where the original specification defines them and preserved on the item where it does not. There is no producer detection and no "which tool wrote this" setting: one format name, as with BibTeX.
- Q: Does the package claim to support RIS generally? → A: No, and it says so. The package cannot support every variation of every bibliographic format, the ecosystem is too inconsistent for that, and moving a library between two established tools loses detail today. The package supports the common producers as best it can, makes no promise that every RIS variant imports perfectly, and grows through bug reports and feature requests. That limit is stated in the README rather than left for a user to discover.
- Q: Does this feature change the import contract? → A: No. It supplies the two stages a format owns and inherits the rest, exactly as the BibTeX format does. The roadmap places the proof of the contract here, and a proof can come out either way: if RIS cannot be delivered without changing the contract, that is a finding raised as its own issue, not a widening folded quietly into this feature.

### Session 2026-08-05 — clarification scan

Resolved against the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: The draft called a source entry a *record* throughout, which is the word RIS itself uses. `CONTEXT.md` retires *record* on both sides of the import boundary: as a synonym for an item, and as a synonym for a source entry. Which word does this specification use? → A: **Entry**, as the glossary requires, with RIS's own word noted once where the file syntax is described. This is the same shape as *cite key* and *citation key*: one thing under the source's name and under the package's, and leaving it unpinned is how a synonym starts circulating. The glossary gains *record* as RIS's spelling of *entry* rather than as a term of its own.
- Q: Minting must be deterministic, and batch de-duplication may suffix a colliding key before it is stored. Those two cannot both describe the same value. Which key is deterministic, and which one does the import result report? → A: Minting is deterministic on the entry's content and happens before de-duplication, so the same entry always mints the same key. What is stored may carry a suffix. The result reports the key **as stored**, including any suffix, and in a dry run the key that would have been stored. This diverges from the BibTeX format, which reports the cite key the source wrote, and the reason it diverges is that a minted key appears nowhere in the source file: nobody can search the file for it, and its only use is finding the item in the catalogue afterwards.
- Q: Material before the first entry is skipped, while a block of tags carrying no reference type is failed. A header written as tag-shaped lines satisfies both descriptions. How are they told apart? → A: By position, not by shape. Everything before the file's first reference-type tag is header material and is skipped, whatever it looks like. After the first entry has been seen, a block of tags with no reference type is a malformed entry and is failed. The rule is mechanical, needs no guess about intent, and matches how a reader reads the file.
- Q: Acceptance rests on genuine exports from EndNote, Web of Science, and Scopus. EndNote is licensed software and the two databases need institutional subscriptions. What happens if an export cannot be obtained? → A: Sample exports the producers and third parties publish count as genuine, since what matters is that the file was written by the producer rather than by this project. Where no genuine file can be obtained for a producer, its coverage rests on a fixture built from that producer's published tag documentation, and the specification records which producers are evidenced that way. A constructed file is never presented as a genuine export.
- Q: "The author-year-title shape reference managers use" is not precise enough to implement against, yet the success criterion asserts only determinism. Does this specification fix the shape? → A: No. What the feature owes is that the key is derived from the entry's own bibliographic content, that it is deterministic, and that the scheme is documented where a user can read it. Fixing the exact shape here would pre-empt a later feature that lets a user choose a citation-key style, and the specification should not decide something no user has yet asked for.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import a set of search results from a `.ris` file (Priority: P1)

A researcher has downloaded search results from a database, or exported their library from a reference manager, and has a `.ris` file. Until the front end arrives at R6 the person running the import is a developer, or an administrator working on the researcher's behalf, and they call it the way any format is called: name the RIS format, hand over the file. Each entry becomes a catalogue item of the right kind, carrying its contributors in the order and roles the file gave them, its dates, and its identifiers. Because the file supplies no cite key, the catalogue gives each item a citation key built from the entry itself, and that key is what identifies the entry in the report and what the researcher searches for afterwards.

**Why this priority**: It is the feature. Nothing else here is reachable without it, and it is the whole of what the roadmap asks for in the plain case.

**Independent Test**: Fully testable with a well-formed EndNote export covering several reference types with multiple contributors, dates, and identifiers. Run an import and assert the catalogue holds an item per entry with the expected type, contributor order, date precision, and identifiers.

**Acceptance Scenarios**:

1. **Given** a well-formed `.ris` file, **When** the developer runs an import naming the RIS format, **Then** the catalogue holds one item per entry and every entry is reported as created.
2. **Given** an entry whose reference type has a direct CSL equivalent, **When** it is imported, **Then** the stored item carries that CSL item type.
3. **Given** an entry whose reference type has no CSL equivalent, **When** it is imported, **Then** the item is stored as a generic document rather than the entry being failed.
4. **Given** an entry listing several authors and an editor across repeated contributor tags, **When** it is imported, **Then** each contributor is stored in its stated role and the authors keep the order the file listed them in.
5. **Given** an entry naming an organization as its author, **When** it is imported, **Then** the contributor is stored as an unparsed institutional name rather than being split into given and family parts.
6. **Given** an entry carrying a publication year but no month, **When** it is imported, **Then** its issued date is stored to year precision rather than being padded to a day the source did not state.
7. **Given** an entry carrying a DOI and a URL, **When** it is imported, **Then** each is stored as an identifier of its own type.
8. **Given** an entry carrying no `ID` tag, **When** it is imported, **Then** the item's citation key is minted from the entry's own content, and the key as stored is the handle reported against that entry in the result.
9. **Given** an entry carrying an `ID` tag, **When** it is imported, **Then** that value becomes the item's citation key unchanged rather than a minted one.
10. **Given** two entries in one file that mint the same citation key, **When** they are imported, **Then** both are stored, the catalogue's existing batch de-duplication distinguishes them, both are reported as created, and each is reported under the key it was actually stored with.
11. **Given** any file, **When** it is imported, **Then** every entry between a reference-type tag and its end-of-entry tag is read as one entry, and the count of results equals the count of entries in the file.
12. **Given** material in the file that precedes the first reference-type tag, a banner or a header line among it, **When** it is imported, **Then** it is reported as skipped rather than failed, and no item is created for it.
13. **Given** the same file imported twice, **When** the minted keys are compared, **Then** each entry mints the same key both times, before any de-duplication suffix is applied.

---

### User Story 2 - A messy export still imports (Priority: P2)

The same researcher's file is a real one. A DOI has been written as a full URL, a date is a string no standard would recognise, an abstract runs across a dozen lines, and one entry has been hand-edited into something the database never wrote. None of that costs them a reference. Values whose meaning is recoverable are cleaned up on the way in, values that are not recoverable are kept rather than thrown away, and an entry is refused only when there is genuinely nothing left to build an item from.

**Why this priority**: A messy export is the normal case, not the exception, and a database download is messier than a curated library because nobody has ever looked at it. An importer that refuses a quarter of a real result set over formatting details fails the only test that decides adoption. It is second because a file has to import at all before it matters how forgiving that import is.

**Independent Test**: Fully testable with a file built from the malformations real exports contain, run alongside a clean file holding the same references, asserting the two produce equivalent catalogue items.

**Acceptance Scenarios**:

1. **Given** an entry whose DOI is written as a full `https://doi.org/…` URL or carries a `doi:` label, **When** it is imported, **Then** the item carries a DOI identifier holding the bare DOI, and the entry is not failed.
2. **Given** an entry carrying a value in a known identifier's tag that is not a valid identifier of that type and cannot be normalized into one, **When** it is imported, **Then** the entry is still stored and the value is preserved on the item rather than discarded or stored as a valid identifier.
3. **Given** an entry whose date cannot be resolved to a structured date, **When** it is imported, **Then** the date is kept in the item's existing fallback for unparseable dates and the entry is not failed.
4. **Given** an entry whose tag values are wrapped across several lines, which is how long abstracts and addresses are written, **When** it is imported, **Then** the continuation lines are read as part of the value they belong to rather than as unknown tags.
5. **Given** an entry the parser cannot read at all, **When** the file is imported, **Then** that entry alone is reported as failed with a reason, and the remaining entries are still stored.
6. **Given** a file whose entries are separated inconsistently, or which uses line endings from another operating system, **When** it is imported, **Then** the entries are still recovered rather than the file being reported as unreadable.
7. **Given** a file of several hundred entries mixing clean and malformed ones, **When** it is imported, **Then** every entry is accounted for once and no entry is refused for a reason normalization could have resolved.

---

### User Story 3 - A Web of Science or Scopus export imports the same way (Priority: P3)

A researcher downloads their search results from Web of Science or Scopus rather than exporting from EndNote, and runs the same import, naming the same format. They do not have to know which tool wrote the file. Tags that those producers use differently from EndNote are read correctly, and a file from any of the three imports without anyone intervening.

**Why this priority**: These are the two databases this feature's own reason for existing names, and they are where a literature review usually starts. It is third because the primary target has to be read correctly before a second and third producer's conventions can be folded into the same format.

**Independent Test**: Fully testable by committing a genuine export of the same references from each producer and asserting the three imports produce equivalent catalogue items.

**Acceptance Scenarios**:

1. **Given** exports of the same references from EndNote, Web of Science, and Scopus, **When** each is imported, **Then** the three produce equivalent catalogue items, judged on item type, contributors and their order, dates and their precision, and identifiers.
2. **Given** an entry whose contributor tag carries a role that differs by producer, **When** it is imported, **Then** the role stored is resolved deterministically from the entry's reference type and the resolution is documented.
3. **Given** an entry carrying a serial number tag whose meaning depends on the reference type, an ISSN for a journal article and an ISBN for a book among them, **When** it is imported, **Then** it is stored as the identifier type the reference type implies, and where it validates as neither it is preserved rather than stored as a valid identifier.
4. **Given** an entry carrying more than one date tag with conflicting values, **When** it is imported, **Then** precedence is deterministic and documented rather than depending on the order the tags appear in.
5. **Given** a file from a producer this feature does not name, **When** it is imported, **Then** tags the original specification defines are read, tags it does not are preserved, and the file imports rather than being refused.

---

### User Story 4 - Nothing in the file is thrown away (Priority: P4)

Databases and reference managers write their own bookkeeping into every export: tags recording which database a result came from, an accession number, a funding acknowledgement, or a set of custom fields the producer never documented. No bibliographic standard defines them and the catalogue has no column for them. They are kept on the item all the same, so a researcher who later wants to know what their download actually contained can still find out.

**Why this priority**: It is what makes the import lossless rather than merely successful, and a database export carries more of this bookkeeping than a curated library does. It is last because it changes nothing about whether a reference imports, only about what survives alongside it.

**Independent Test**: Fully testable by importing a file carrying tags that no standard defines and asserting they are retrievable from the stored item afterwards.

**Acceptance Scenarios**:

1. **Given** an entry carrying tags that map to no CSL variable, **When** it is imported, **Then** those tags and their values are retrievable from the stored item.
2. **Given** such an entry, **When** it is imported, **Then** it is reported as created exactly as an entry with no unmapped tags would be, with no additional outcome and no per-tag reporting.
3. **Given** an entry carrying a second value for something the catalogue holds one of, a print and an electronic serial number being the common case, **When** it is imported, **Then** the first is stored as an identifier, the second is preserved on the item, and the entry is not failed.

---

### Edge Cases

- **A file that is not RIS at all.** A file of prose, or one holding a different bibliography format, produces a reported parse failure rather than an unhandled error or a catalogue of nonsense. A BibTeX file under a `.ris` name is the case to test by name, since it is the mirror of the failure the BibTeX format found in its own parser.
- **An empty file** ~~, or one holding only a header~~ *(header-only clause superseded 2026-08-05 by FR-008a — see Refinements)*. A successful import of nothing, with an empty result and an unchanged catalogue.
- **A truncated file.** The entries recovered before the truncation are reported, and the entry cut off at the end is reported through the result rather than raised.
- **An entry opened by a reference-type tag but never closed.** Reported through the result. The last entry in a file whose final end-of-entry tag is missing is still recovered rather than discarded, since real exports do this.
- **A block of tags carrying no reference type, after the first entry has been seen.** It is not an entry, because RIS states the kind of thing first. Reported as failed with a reason naming what is missing, rather than stored as a generic document, which would invent a claim the source never made. The same shape *before* the first reference-type tag is header material and is skipped, since position is what tells the two apart.
- **An entry with a reference type and nothing else.** Reported as skipped. There is no bibliographic content to store, matching the equivalent decision in the BibTeX format.
- **Entries that mint identical citation keys.** The catalogue's existing behaviour applies unchanged: colliding keys are given distinguishing suffixes within the batch, each entry is still reported as created, and each is reported under the key it was stored with.
- **A file in an unexpected text encoding.** Reported as a parse failure with the encoding named in the reason, rather than storing corrupted text. A file carrying a byte-order mark imports normally, since exports routinely carry one.

## Requirements *(mandatory)*

### Functional Requirements

**The format**

- **FR-001**: The package MUST ship an RIS format that plugs into the import contract delivered under issue #21, supplying the file-to-entries and entry-to-CSL-JSON stages and the per-entry source handle.
- **FR-002**: The format MUST NOT change the contract's behaviour. Entry atomicity, per-entry reporting and its outcome vocabulary, source ordering, dry runs, and the configured-format lookup MUST apply exactly as delivered.
- **FR-003**: The format MUST be among the formats the package ships by default, alongside BibTeX, so a project that configures nothing can import RIS (Article X).
- **FR-004**: The format MUST consume a file's entries one at a time, so that the whole file's converted content is not materialised before any entry is stored, and the order entries are reported in MUST follow the order they occur in the source.
- **FR-005**: Where this feature cannot be delivered without changing the import contract's public surface, that MUST be raised as its own issue rather than resolved by widening the contract inside this feature.

**Entries**

- **FR-006**: The format MUST recover entries delimited by a reference-type tag and an end-of-entry tag, and MUST recover the final entry of a file whose closing end-of-entry tag is absent.
- **FR-007**: ~~A tag value continued across several lines MUST be read as one value.~~ *(Amended 2026-08-05 — see Refinements and research R7.)* An untagged line following a tag line MUST be resolved **per tag**, because producers use the same syntax for two different things. For a tag that is repeatable by nature — the author tags, `KW`, `UR`, `SN`, `N1` — an untagged line is **another value**. For a scalar or prose tag — `AB`, `TI`, `T2` — it is a **continuation** of the value and is joined with a single space. The classification MUST be documented. Indentation MUST NOT be used to decide, since the primary support target never indents and another producer does.
- **FR-008**: In a file that contains at least one reference-type tag, everything preceding the first one MUST be reported as skipped, whatever its shape.
- **FR-008a**: A file containing RIS tag lines but **no reference-type tag anywhere** MUST be reported as a parse failure naming the missing tag, not as a successful import of nothing. *(Added 2026-08-05 — see Refinements and research R8.)*
- **FR-009**: After the first entry has been seen, a block of tags carrying no reference type MUST be reported as failed with a reason naming what is missing. An entry carrying a reference type and no other bibliographic content MUST be reported as skipped.
- **FR-010**: Line endings and entry separation MUST be read tolerantly enough that a file written on another operating system, or by a producer that separates entries inconsistently, still yields its entries.

**Mapping**

- **FR-011**: Every RIS reference type MUST map to a CSL item type. A type with no CSL equivalent MUST map to the generic `document` type rather than failing the entry.
- **FR-012**: Every RIS tag with a CSL equivalent MUST map to it, and the mapping MUST be documented.
- **FR-013**: Contributor tags MUST become contributor records in the roles they name, preserving the order the source lists them in. Where a contributor tag's role differs between the producers this feature supports, the role MUST be resolved deterministically from the entry's reference type, and the resolution MUST be documented.
- **FR-014**: Contributor names MUST be parsed into their parts where the source states them, and a name the source gives as an unparsed or institutional string MUST be stored as such rather than split.
- **FR-015**: Dates MUST be stored at the precision the source states, without padding an unstated month or day. Where an entry carries more than one date tag for the same date, precedence MUST be deterministic and documented.
- **FR-016**: A date a source records as the date its subject was retrieved MUST be mapped to the item's access date.
- **FR-017**: Identifier tags MUST become typed identifier records. A tag whose identifier type depends on the entry's reference type MUST be resolved from that type, and a value that validates as no known type MUST be preserved under FR-024 rather than stored as a valid identifier.
- **FR-018**: A tag appearing more than once in one entry, where the catalogue holds only one of what it carries, MUST resolve deterministically: the first value is stored and the remainder preserved under FR-024. The rule MUST be documented.

**Citation keys**

- **FR-019**: Every entry MUST receive a citation key, since the catalogue requires one and RIS supplies no cite key.
- **FR-020**: Where an entry carries an `ID` tag, its value MUST become the item's citation key unchanged.
- **FR-021**: Where it does not, the citation key MUST be minted from the entry's own bibliographic content. Minting MUST be deterministic — the same entry always mints the same key — and the scheme MUST be documented where a user can read it. The exact shape of the key is not fixed by this specification. An entry too sparse to mint from MUST fall back to its position in the file rather than failing.
- **FR-022**: The source handle reported against an entry MUST be its citation key **as stored**, including any de-duplication suffix the catalogue applied, and in a dry run the key that would have been stored. A minted key appears nowhere in the source file, so the only value it has to a reader is finding the item afterwards.
- **FR-023**: A minted key MUST NOT be matched against items already stored. The catalogue's existing batch-scoped de-duplication applies unchanged, and importing the same file twice MUST produce two sets of items.

**Recovery and preservation**

- **FR-024**: An RIS tag with no CSL equivalent, and any value that cannot be normalized into something the catalogue accepts, MUST be preserved on the stored item and be retrievable afterwards, rather than discarded.
- **FR-025**: A value written in a form the catalogue would reject, but whose intended value is recoverable, MUST be normalized before it is stored. A DOI carrying a resolver URL prefix or a `doi:` label is the case this feature must handle by name.
- **FR-026**: A date that cannot be resolved to a structured date MUST be kept in the item's existing fallback for unparseable dates rather than discarded.
- **FR-027**: An entry MUST be reported as failed only where it cannot be parsed, where it carries no reference type, or where the catalogue rejects it after recovery has been attempted.
- **FR-028**: Preservation MUST NOT alter what an import reports. No outcome value is added, and no per-tag reporting channel is introduced.

**Support boundary**

- **FR-029**: One format MUST read the exports of every producer it supports under a single name, without the caller stating which tool wrote a file, and without the format detecting it.
- **FR-030**: EndNote MUST be the primary support target, with Web of Science and Scopus supported secondarily, and acceptance MUST be judged against genuine exports from all three committed to the repository. A file published by the producer or by a third party counts as genuine; a file this project constructed does not, and where no genuine file can be obtained for a producer, the specification's *Verification corpus* MUST record which producer is evidenced by a documentation-built fixture instead.
- **FR-031**: A file from a producer this feature does not name MUST still import: tags the original specification defines are read, and tags it does not are preserved.
- **FR-032**: The README MUST state the package's support boundary for bibliographic formats — that it reads the common producers as best it can, makes no promise that every variant imports perfectly, and grows through bug reports and feature requests.

**Package conventions**

- **FR-033**: Every name this feature makes public MUST be importable from the `literature` namespace (Article X).
- **FR-034**: Every human-readable string this feature produces, failure reasons among them, MUST be translatable (Article VIII).
- **FR-035**: File content MUST be treated as untrusted input. No content in a `.ris` file may cause code execution, filesystem access, network access, or an unhandled error (Article V).
- **FR-036**: The vocabulary this feature introduces MUST be added to `CONTEXT.md` in the same change (Article VI): the *minted citation key*; *record* as RIS's own spelling of *entry*, recorded the way *cite key* records the source's name for a *citation key*; and an extension of the existing *dialect* entry to cover producer conventions that are not specified variants. The existing *field* and *entry type* entries MUST record their RIS spellings, so the glossary's terms cover both formats rather than reading as BibTeX's alone.

### Requirement coverage

- **User Story 1** carries FR-006 through FR-017 and FR-019 through FR-023: reading a file, mapping what it holds, and giving every entry a key.
- **User Story 2** carries FR-025 through FR-027, together with FR-007 and FR-010, which are what a messy file exercises.
- **User Story 3** carries FR-029 through FR-031, together with FR-013, FR-015, FR-017 and FR-018, whose deterministic resolutions exist because producers disagree.
- **User Story 4** carries FR-024 and FR-028, together with FR-018's preservation of a second value.
- **FR-001 through FR-005** define the format's relationship to the import contract and constrain every story.
- **FR-032** is a documentation requirement covering the feature as a whole, verified by inspection of the README.
- **FR-033 through FR-036** are package-wide constraints, and each story's acceptance is judged against them.

### Key Entities

- **RIS format**: A `BibFormat` subclass reading the RIS syntax. It supplies the file-to-entries and entry-to-CSL-JSON stages and inherits the rest of the import workflow.
- **Entry**: One bibliographic entry as it appears in an RIS file, opened by a reference-type tag and closed by an end-of-entry tag. RIS's own name for it is a *record*, which is the source-side spelling of the glossary's *entry* and is not used as a term in its own right.
- **Minted citation key**: A citation key the format builds from an entry's own bibliographic content, because RIS supplies no cite key. Deterministic, and distinct from a key the source stated in an `ID` tag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A downloaded set of search results becomes a populated catalogue in one call, without converting the file first and without anyone naming which tool wrote it.
- **SC-002**: Across the committed corpus described under *Verification corpus*, no entry is refused for a reason that normalization resolves, and every entry that is refused carries a reason naming what could not be recovered.
- **SC-003**: Every entry in the corpus receives a citation key, and no entry fails for want of one.
- **SC-004**: Importing the same file twice mints the same key for the same entry both times, so keys are reproducible rather than incidental to a run. What is stored may differ by a de-duplication suffix, and the import result names the stored key in each run.
- **SC-005**: The same references exported from EndNote, Web of Science, and Scopus produce equivalent catalogue items, judged on item type, contributors and their order, dates and their precision, and identifiers.
- **SC-006**: Every tag present in a source entry is either mapped to its CSL equivalent or retrievable from the stored item afterwards. No tag is absent from both.
- **SC-007**: Contributor order and role survive the import, so an item's first author is the file's first author.
- **SC-008**: No content in a `.ris` file, however malformed, produces an unhandled error, and every malformed-input case is reported through the import result.
- **SC-009**: Adding this format required no change to the **public behaviour** of the import workflow, the reported result, or the code that builds an item from CSL JSON, which is what demonstrates the contract was drawn in the right place. ~~Any change that proved unavoidable is recorded as its own issue rather than made here.~~ *(Amended 2026-08-05 — see Refinements.)* A change that would **widen or reshape** any of those to suit this format is recorded as its own issue and not made here. A defect fix that changes none of their behaviour is not such a change, may land in this feature's pull request, and is recorded as its own issue so the fix is traceable.

### Verification corpus

The criteria above are judged against files committed to the repository, so the result is reproducible and no test reaches the network. The corpus holds three kinds of file:

- Constructed fixtures, each isolating one malformation this specification names, so a failure points at the rule it broke.
- A genuine export from each supported producer — EndNote, Web of Science, and Scopus — covering the same references, which is what the roadmap means by representative real-world files and is the only thing that catches malformations nobody thought to construct. A file the producer or a third party published counts as genuine; what disqualifies a file is this project having written it.
- At least one file large enough that a whole-file conversion would be visible, which is what FR-004 is asserted against.

Where no genuine export can be obtained for a supported producer, that producer's coverage rests on a fixture built from its published tag documentation, and this section records which producer that applies to. A constructed file is never presented as a genuine export.

**Outcome, settled at S3 (research R10): no producer falls back.** `asreview/citation-file-formatting` publishes the same ten references exported through twenty-five tools under **CC0-1.0**, including genuine EndNote, Web of Science and Scopus files, so all three supported producers are evidenced by real exports. One gap remains inside that: every record in the EndNote baseline is a journal article, so it evidences nothing about the chapter-editor question, and genuine chapter records come from other corpora whose licences are confirmed before vendoring. Where a licence cannot be confirmed, the case is reproduced as a constructed fixture and this section says so.

**One case is substituted: a chapter carrying its editors.** No producer falls back, but this single case does. Every record in all twenty-five CC0 baselines is a journal article, so none of them evidences it, and the two corpora holding genuine chapter records — `ESHackathon/CiteSource` for Web of Science and `tributetotobler/bibliotobler` for Scopus — are both GPL-3.0, which this MIT-licensed package cannot redistribute. JabRef's importer fixtures are MIT, but they are hand-written parser tests rather than producer output and carry no chapter export either. So the case rests on `tests/data/ris/constructed/chapter_with_editors.ris`, written in EndNote's shape because EndNote is the producer whose genuine file leaves the gap. The mapping it exercises — `A2` as the editor role on a chapter and `T2` as the containing book — is taken from the format's published reference-type matrix rather than from any licensed file.

Exported files carry bibliographic metadata only, with anything personal removed. Bibliographic metadata is factual and raises no licensing question.

## Assumptions

- **The import contract is inherited, not revisited.** The workflow, atomicity, reporting, dry runs, and configured-format lookup delivered under issue #21 apply unchanged. This feature supplies the two stages a format owns.
- **The BibTeX format is not modified.** The two formats share the contract, not each other. Where both need the same normalization, sharing it is a decision for the plan rather than an assumption made here, and it must not change what a `.bib` file imports as.
- **The caller names the format.** Detecting a file's format from its name or content remains out of scope, as settled for the contract.
- **CSL JSON is the intermediate representation.** The existing conversion builds the item and its related records, and this feature does not change its behaviour for callers using it directly.
- **The existing catalogue behaviour is inherited.** Batch-scoped citation-key de-duplication, partial-date fallbacks, and unknown-identifier storage apply exactly as they do today.
- **The model's single-value limits are not widened.** One identifier per type per item and one date per slot are documented design limits. A second value is preserved on the item, and widening either remains a feature in its own right.
- **De-duplication against already-stored items is out of scope.** Deciding when two entries are the same reference remains a separate problem, and established reference managers do not solve it either.
- **Citation-key style is not configurable.** Choosing a key style and regenerating existing keys are later features, and nothing here forecloses them.
- **Export is out of scope.** Writing a `.ris` file from the catalogue is a later feature, though the mapping this feature documents is what an export would run in reverse.
- **No user interface.** Nothing here assumes a view, a form, or an upload. The front end is roadmap item R6.

## Refinements

### 2026-08-05 — S3 research, after the Spec gate

Research at S3 (`research.md`) tested this specification against genuine exports from all three
supported producers and against the parsing libraries available. Two requirements were wrong. Both
amendments correct behaviour **inside** the approved scope — no story is added, removed or
re-prioritised, and no success criterion changes — so this is recorded here and notified rather than
re-gated.

- **FR-007 mandated the wrong thing for the primary support target.** It required an untagged
  continuation line to be read as part of one value. EndNote uses exactly that syntax to carry
  *additional* values: a genuine record puts eight keywords under one `KW` tag and two ISSNs under
  one `SN` tag, each on its own unindented line. Read as the original FR-007 required, that becomes
  one eight-word keyword and one nonsense serial number. Web of Science uses the same syntax for
  genuinely wrapped prose, and indentation does not separate the two cases: it is a Web of Science
  habit, and EndNote never indents. The rule is now per tag — repeatable tags take another value,
  scalar and prose tags join with a space — which is decidable from the tag alone and needs no guess
  about the file's origin. See research R7.
- **FR-008 left a legitimate Scopus export importing as nothing.** Scopus omits `TY` entirely when
  the person exporting unchecks "Source & document type", which Scopus support has acknowledged. The
  original FR-008 skips everything before the first reference-type tag; with no reference-type tag
  anywhere, that skipped the whole file and reported a successful import of nothing. A supported
  producer's real file yielding an empty catalogue in silence is precisely the failure the import
  contract's own reporting rule exists to prevent. FR-008 is now scoped to files that have a first
  entry, and **FR-008a** covers the file that has none. See research R8.

Two further findings changed no requirement and are recorded in `research.md` rather than here: the
parser is hand-rolled rather than taking a dependency on `rispy`, which fails four of these
requirements outright (R1, and `decisions.md` D11); and Scopus mistypes book chapters as `JOUR`,
which is not corrected, because inferring the real type from other tags is the guessing FR-031 rules
out (R9).

### 2026-08-05 — SC-009 amended, on Sam's instruction

SC-009 was written to keep one claim falsifiable: that the import contract delivered under #21 was
drawn in the right place, proven by a second real format needing nothing added to it. Its final
sentence over-reached, and at S3 it was read as "no line of `base.py`, `results.py` or
`converters.py` may change".

Applied that way it split a two-line defect fix — a de-duplication suffix generator that stops
terminating past 701 collisions (#41) — into its own branch, review and merge cycle, and made this
feature depend on that merge. A loop that terminates is not a widening of the contract. It changes no
public behaviour and concedes nothing about where the seam was drawn, so the criterion it was
supposedly protecting was never at risk.

The amendment separates the two cases the original sentence conflated. **Widening or reshaping** any
of those modules to suit this format is still recorded as its own issue and kept out of this feature,
because that is the thing that would falsify the claim. **A defect fix that changes none of their
public behaviour** may land here, with its own issue for traceability. #41 is now fixed under T041 in
this feature's pull request, which also honours the standing rule that a session's work lands as one
pull request rather than several.

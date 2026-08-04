# Feature Specification: Import References from BibTeX Files

**Feature Branch**: `004-import-references-bibtex`

**Created**: 2026-08-04

**Status**: Draft · **Refined**: 2026-08-04 (see *Refinements* below)

**Serves**: G5 (import references from common bibliography formats) · Roadmap R5 · Issue #22

**Input**: Researchers keep their reference libraries in BibTeX, the format nearly every reference manager and academic database will export. This package only takes references in as CSL JSON, so anyone adopting it has to convert their library first with whatever tool they can find, and accept whatever that tool loses on the way. This feature reads a `.bib` file directly, so an existing library becomes a populated catalogue in one step.

## Clarifications

### Session 2026-08-04 — intake

- Q: A record that is otherwise sound but carries one value the catalogue rejects, a DOI written as `https://doi.org/10.1234/abc` being the common case, fails entirely under the import contract's atomicity rule. Is that the intended behaviour for a real library? → A: No. Cleaning an entry before it is imported is the format's job, and this format recovers as much as it can before rejecting anything. A value whose intended meaning is recoverable is normalized, and a value that is genuinely unusable goes to preservation rather than costing the record. Rejection is the last resort, not the first response to a formatting difference.
- Q: "BibTeX" names two dialects in practice. Classic BibTeX is what publisher export links emit, and BibLaTeX is what current Zotero and JabRef emit by default, with different field names and entry types. Does this feature read both? → A: Both, unified under one format name. Someone importing does not know which dialect their reference manager wrote, and requiring them to find out is the adoption barrier this feature exists to remove. A BibLaTeX file read as classic BibTeX would produce entries with no journal and no date, reported as created and quietly wrong, which is worse than a refusal.
- Q: Source fields that no bibliographic standard defines are preserved rather than discarded. Does the import result also have to report which fields were preserved? → A: No. "Not dropped in silence" means not discarded, and preservation on the record satisfies it. Per-entry reporting keeps the vocabulary the import contract defines, this feature adds no per-field reporting channel, and someone who wants to know what was preserved reads the record. Adding one would mean reopening a contract that shipped days earlier for a need nobody has stated.
- Q: BibTeX's `crossref` field lets an entry inherit fields from another entry in the same file, so a chapter can take its book's publisher and year. Ignoring it produces records that are incomplete without saying so. Is inheritance in scope? → A: Yes, where the referenced parent is in the same file. Ignoring it silently is the same failure as reading a BibLaTeX file as classic BibTeX: a record that lands looking complete while missing fields the source actually supplied. A `crossref` pointing at an entry the file does not contain is preserved as an ordinary unmapped field, since nothing can be resolved from it.
- Q: Does this feature change anything about how the import contract behaves? → A: No. It supplies the two stages a format owns and takes the rest as given. Atomicity, per-entry reporting, ordering, dry runs, and the configured-format lookup are the contract's behaviour, already delivered and tested under issue #21, and this feature is verification that the seam was drawn in the right place rather than an occasion to move it.

### Session 2026-08-04 — clarification scan

Resolved against the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: Reading a file's entries one at a time and resolving `crossref` contradict each other. Classic BibTeX requires a cross-referenced entry to appear *after* every entry referencing it, so the parent a child needs has not been read yet when the child is converted. Which requirement gives way? → A: Neither. The format establishes the file's `@string` macros and its cross-reference targets before converting anything, and converts entries against that. What an import holds in memory is then bounded by the macros and cross-reference parents a file defines rather than by the number of entries in it, which is the constraint that actually mattered, and the order entries are reported in is untouched. The cost is that the source must be readable more than once, which holds for a path and for an uploaded file alike, and is stated as a requirement rather than left as an assumption about the caller. *(Superseded 2026-08-04 — see Refinements. The parsing library does both within one load, so there is no second pass and no cost to the caller. The reasoning is kept because it is why FR-004 read as it did.)*
- Q: The stories are written around a researcher who "runs an import", but this feature ships no interface, and the roadmap places the front end at R6. Who actually calls it? → A: A developer, or an administrator acting for the researcher, exactly as in the import contract's own stories. The researcher is who the feature is for and whose library and judgement decide whether it succeeded, but the caller is someone working in code until R6 exists. The stories name both rather than conflating them.
- Q: "No entry is refused for a reason that normalization resolves" cannot be measured against an unnamed body of files, and the roadmap asks for tests over representative real-world files. What establishes it? → A: A corpus committed to the repository: fixture files built to reproduce the malformations real exports contain, plus a genuine export per dialect from a mainstream reference manager, carrying only bibliographic metadata and nothing personal. Acceptance is judged against that committed corpus, so it is reproducible and needs no network. Bibliographic metadata is factual and raises no licensing question.
- Q: The requirement to add vocabulary to `CONTEXT.md` does not say which terms, where the import contract's equivalent named its own. Which are they? → A: Entry type, field, and dialect, plus cite key — and cite key matters most, because the glossary already defines *citation key* for `Item.citation_key`. They are the same value arriving under two names, one the source's and one the model's, and leaving that unpinned is how a synonym starts circulating.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import a reference library from a `.bib` file (Priority: P1)

A researcher has exported their library from a reference manager and has a `.bib` file. Until the front end arrives at R6 the person running the import is a developer, or an administrator working on the researcher's behalf, and they call it the same way any format is called: name the BibTeX format, hand over the file. Each entry becomes a catalogue item of the right kind, carrying its contributors in the order and roles the file gave them, its dates, and its identifiers. The entry's cite key is what the researcher can search for afterwards, and it is what identifies the entry in the report.

**Why this priority**: It is the feature. Nothing else in this specification is reachable without it, and it is the whole of what the roadmap asks for in the plain case.

**Independent Test**: Fully testable with a well-formed classic BibTeX file covering several entry types with multiple contributors, dates, and identifiers. Run an import and assert the catalogue holds an item per entry with the expected type, contributor order, date precision, and identifiers.

**Acceptance Scenarios**:

1. **Given** a well-formed `.bib` file, **When** the developer runs an import naming the BibTeX format, **Then** the catalogue holds one item per entry and every entry is reported as created.
2. **Given** an entry whose type has a direct CSL equivalent, **When** it is imported, **Then** the stored item carries that CSL item type.
3. **Given** an entry whose type has no CSL equivalent, **When** it is imported, **Then** the item is stored as a generic document rather than the entry being failed.
4. **Given** an entry with several authors and an editor, **When** it is imported, **Then** each contributor is stored in its stated role, and the authors keep the order the file listed them in.
5. **Given** an entry naming an organization as its author in braces, **When** it is imported, **Then** the contributor is stored as an unparsed institutional name rather than being split into given and family parts.
6. **Given** an entry carrying a year but no month, **When** it is imported, **Then** its issued date is stored to year precision rather than being padded to a day the source did not state.
7. **Given** an entry carrying a DOI, an ISBN, and a URL, **When** it is imported, **Then** each is stored as an identifier of its own type.
8. **Given** any entry, **When** it is imported, **Then** its cite key is the item's citation key and is the handle reported against that entry in the result.
9. **Given** a file using `@string` macros for repeated values, **When** it is imported, **Then** entries carry the values those macros stand for rather than the macro names.
10. **Given** a file containing `@comment` or `@preamble` blocks, **When** it is imported, **Then** they are reported as skipped rather than failed, and no item is created for them.
11. **Given** an entry whose `crossref` names another entry in the same file, **When** it is imported, **Then** the item carries the fields it inherits from that parent alongside its own.
12. **Given** an entry whose `crossref` parent appears later in the file, which is where classic BibTeX requires it, **When** it is imported, **Then** inheritance resolves regardless, and the entry is still reported at its own position in the file rather than deferred to its parent's.

---

### User Story 2 - A messy export still imports (Priority: P2)

The same researcher's file is a real one. Entries have been hand-edited over years, a DOI has been pasted in as a full URL, author names carry accents written as LaTeX escapes, and a date is a string no standard would recognise. None of that costs them a reference. Values whose meaning is recoverable are cleaned up on the way in, and values that are not recoverable are kept rather than thrown away. An entry is refused only when there is genuinely nothing left to build a record from.

**Why this priority**: A messy export is the normal case, not the exception, and it is what the person evaluating this package will feed it first. An importer that refuses a quarter of a real library over formatting details fails the only test that decides adoption. It is second because a file has to import at all before it matters how forgiving that import is.

**Independent Test**: Fully testable with a file built from the malformations real exports contain, run alongside a clean file holding the same references, asserting the two produce equivalent catalogue records.

**Acceptance Scenarios**:

1. **Given** an entry whose DOI is written as a full `https://doi.org/…` URL, **When** it is imported, **Then** the item carries a DOI identifier holding the bare DOI, and the entry is not failed.
2. **Given** an entry whose DOI carries a `doi:` label, **When** it is imported, **Then** the same normalization applies.
3. **Given** an entry whose author names use LaTeX escapes for accented characters, **When** it is imported, **Then** the stored names hold those characters rather than the LaTeX source that produced them.
4. **Given** a title carrying braces that exist only to protect capitalization, **When** it is imported, **Then** the stored title holds the text without them.
5. **Given** an entry carrying a value in a known identifier's field that is not a valid identifier of that type and cannot be normalized into one, **When** it is imported, **Then** the entry is still stored and the value is preserved on the record rather than discarded or stored as a valid identifier.
6. **Given** an entry whose date cannot be resolved to a structured date, **When** it is imported, **Then** the date is kept in the record's own fallback for unparseable dates and the entry is not failed.
7. **Given** an entry the parser cannot read at all, **When** the file is imported, **Then** that entry alone is reported as failed with a reason, and the remaining entries are still stored.
8. **Given** a file of several hundred entries mixing clean and malformed records, **When** it is imported, **Then** every entry is accounted for once and no entry is refused for a reason normalization could have resolved.

---

### User Story 3 - A BibLaTeX export imports the same way (Priority: P3)

A researcher whose reference manager writes BibLaTeX rather than classic BibTeX runs the same import, naming the same format, and does not have to know which dialect they were given. Entry types and field names that exist only in BibLaTeX are understood, and a file mixing conventions imports without anyone intervening.

**Why this priority**: It widens the feature to the reference managers that now export BibLaTeX by default, which is a large part of the audience, but the classic dialect has to be read before the second one can be folded in.

**Independent Test**: Fully testable by exporting an equivalent library in both dialects and asserting the two imports produce equivalent catalogue records.

**Acceptance Scenarios**:

1. **Given** a BibLaTeX entry using `journaltitle`, **When** it is imported, **Then** the stored item carries that value as its container title, exactly as a classic entry using `journal` would.
2. **Given** a BibLaTeX entry carrying a single `date` field, **When** it is imported, **Then** its issued date is stored at the precision the field states, whether that is a year, a year and month, or a full date.
3. **Given** a BibLaTeX entry type with no classic equivalent, an online resource or a thesis among them, **When** it is imported, **Then** it is stored as its corresponding CSL item type rather than falling back to a generic document.
4. **Given** a file whose entries mix classic and BibLaTeX field names, **When** it is imported, **Then** every entry is read correctly without anyone naming a dialect.
5. **Given** an entry carrying both a `date` field and a `year` field that disagree, **When** it is imported, **Then** the resolution is deterministic and documented rather than depending on the order the fields appear in.

---

### User Story 4 - Nothing in the file is thrown away (Priority: P4)

Reference managers write their own bookkeeping into every export, fields recording where a PDF sits on disk, which collection an entry belongs to, or when a record was last touched. No bibliographic standard defines them and the catalogue has no column for them. They are kept on the record all the same, so a researcher who later wants to know what their export actually contained can still find out.

**Why this priority**: It is what makes the import lossless rather than merely successful, and it protects a decision the researcher has not made yet. It is last because it changes nothing about whether a reference imports, only about what survives alongside it.

**Independent Test**: Fully testable by importing a file carrying fields that no standard defines and asserting they are retrievable from the stored record afterwards.

**Acceptance Scenarios**:

1. **Given** an entry carrying fields that map to no CSL variable, **When** it is imported, **Then** those fields and their values are retrievable from the stored item.
2. **Given** such an entry, **When** it is imported, **Then** it is reported as created exactly as an entry with no unmapped fields would be, with no additional outcome and no per-field reporting.
3. **Given** an entry whose `crossref` names an entry the file does not contain, **When** it is imported, **Then** the unresolved reference is preserved as an ordinary unmapped field and the entry is not failed.

---

### Edge Cases

- **A file that is not BibTeX at all.** A file of prose, or one holding a different bibliography format, produces a reported parse failure rather than an unhandled error or a catalogue of nonsense.
- **An empty file, or one holding only comments and macros.** A successful import of nothing, with an empty result and an unchanged catalogue.
- **A truncated file.** The entries recovered before the truncation are reported, and the remainder is reported as ~~a failure~~ *skipped (amended 2026-08-04, D26 — the parser reclassifies the cut-off block as a comment before this feature's code runs, the same mechanism D11 documents; what matters is that it is reported, not which of the two reported outcomes it carries)*.
- **Duplicate cite keys within one file.** The catalogue's existing behaviour applies unchanged: colliding keys are given distinguishing suffixes within the batch, and each entry is still reported as created.
- ~~**An entry with no fields at all beyond its type and cite key.** Stored, since a type and a citation key are all the catalogue requires. Sparse is not invalid.~~ *(Amended 2026-08-04 — reported as skipped rather than stored. See `## Refinements` and D11.)*
- **A file in an unexpected text encoding.** Reported as a parse failure naming the encoding, rather than storing corrupted text. Latin-1 content in a file assumed to be UTF-8 is the case that occurs in practice.
- **LaTeX that decodes to nothing recognisable.** A command the decoder does not know is left as it stands rather than dropped, so the reader can still see what the source held.
- **A `crossref` chain, or a cycle.** Inheritance resolves without looping indefinitely, and a cycle is reported rather than hanging the import.
- **An entry carrying the same field twice.** Resolved deterministically rather than depending on parser internals.
- ~~**A source that cannot be read twice.** Reported as a failure naming that as the cause, rather than silently importing with macros unexpanded and cross-references unresolved.~~ *(Removed 2026-08-04 with FR-005. Nothing reads the source twice.)*

## Requirements *(mandatory)*

### Functional Requirements

**The format**

- **FR-001**: The package MUST ship a BibTeX format that plugs into the import contract delivered under issue #21, supplying the file-to-entries and entry-to-CSL-JSON stages and the per-entry source handle.
- **FR-002**: The format MUST NOT change the contract's behaviour. Entry atomicity, per-entry reporting and its outcome vocabulary, source ordering, dry runs, and the configured-format lookup MUST apply exactly as delivered.
- **FR-003**: The format MUST be among the formats the package ships by default, so a project that configures nothing can import BibTeX (Article X).
- **FR-004**: The format MUST consume a file's entries one at a time, so that the whole file's *converted* content is not materialised before any entry is stored. Entries MUST be converted and stored one at a time, and the order they are reported in MUST follow the order they occur in the source. *(Reworded 2026-08-04. The original tightened the import contract's FR-024 from converted content to all content, which #21 did not settle and which the parsing library makes moot; it also required macros and cross-reference targets to be established before conversion, which the library does within its own single load.)*
- **FR-005**: ~~The format MUST be able to read its source more than once, which is what FR-004 costs, and MUST state that requirement rather than assume it. A source that cannot be re-read MUST fail with a reason saying so rather than produce an import with macros or cross-references left unresolved.~~ **Removed 2026-08-04.** It existed only to pay for the original FR-004. The parsing library expands `@string` macros and resolves `crossref` inside a single load, so there is no second pass and nothing is asked of the caller that the import contract did not already ask. The number is retired rather than reused, so every later requirement keeps its identifier.

**Mapping**

- **FR-006**: Every BibTeX entry type MUST map to a CSL item type. A type with no CSL equivalent MUST map to the generic `document` type rather than failing the entry.
- **FR-007**: Every BibTeX field with a CSL equivalent MUST map to it, and the mapping MUST be documented.
- **FR-008**: Contributor lists MUST become contributor records in the roles the fields name, preserving the order the source lists them in.
- **FR-009**: Contributor names MUST be parsed into their parts where the source states them, and a name the source gives as an unparsed or institutional string MUST be stored as such rather than split.
- **FR-010**: Dates MUST be stored at the precision the source states, without padding an unstated month or day.
- **FR-011**: Identifier fields MUST become typed identifier records.
- **FR-012**: An entry's cite key MUST become the item's citation key, and MUST be the source handle reported against that entry. *(Qualified 2026-08-04, D26: where one file carries two entries under one cite key, the catalogue resolves the collision by suffixing, so the second entry's stored citation key differs from the key its own report names. The report names what the source wrote, which is what a reader searching the file will look for.)*
- **FR-013**: `@string` macros defined in a file MUST be expanded in the entries that reference them.
- **FR-014**: Elements that are not bibliographic records, `@comment` and `@preamble` among them, MUST be reported as skipped rather than failed.
- **FR-015**: An entry whose `crossref` names another entry in the same file MUST inherit that parent's fields where it does not state its own. A `crossref` naming an entry the file does not contain MUST be preserved as an unmapped field. Inheritance MUST terminate on a cyclic or self-referential chain and report it rather than failing to complete.
- **FR-016**: A field appearing more than once in one entry MUST resolve deterministically, and the rule MUST be documented.

**Recovery**

- **FR-017**: A value written in a form the catalogue would reject, but whose intended value is recoverable, MUST be normalized before it is stored. A DOI carrying a resolver URL prefix or a `doi:` label is the case this feature must handle by name.
- **FR-018**: LaTeX-encoded text MUST be decoded to the characters it represents, and braces serving only to protect capitalization MUST be removed. A construct the decoder does not recognise MUST be left as it stands rather than dropped.
- **FR-019**: A value that cannot be normalized into something the catalogue accepts MUST NOT cause its entry to fail. It MUST be preserved instead.
- **FR-020**: A date that cannot be resolved to a structured date MUST be kept in the record's existing fallback for unparseable dates rather than discarded.
- **FR-021**: An entry MUST be reported as failed only where it cannot be parsed, or where the catalogue rejects it after recovery has been attempted.

**Dialects**

- **FR-022**: One format MUST read both classic BibTeX and BibLaTeX, under a single name, without the caller stating which dialect a file holds.
- **FR-023**: Entry types and field names belonging to only one dialect MUST map to their CSL equivalents, and a file mixing both MUST import correctly.
- **FR-024**: Where the dialects supply the same information through different fields, and an entry carries both with conflicting values, precedence MUST be deterministic and documented.

**Preservation**

- **FR-025**: A source field with no CSL equivalent MUST be preserved on the stored item and be retrievable afterwards, rather than discarded.
- **FR-026**: Preservation MUST NOT alter what an import reports. No outcome value is added, and no per-field reporting channel is introduced.

**Package conventions**

- **FR-027**: Every name this feature makes public MUST be importable from the `literature` namespace (Article X).
- **FR-028**: Every human-readable string this feature produces, failure reasons among them, MUST be translatable (Article VIII).
- **FR-029**: File content MUST be treated as untrusted input. No content in a `.bib` file may cause code execution, filesystem access, network access, or an unhandled error, and decoding LaTeX MUST NOT evaluate it (Article V).
- **FR-030**: The vocabulary this feature introduces MUST be added to `CONTEXT.md` in the same change (Article VI): entry type, field, dialect, and cite key. The cite key entry MUST record its relationship to the glossary's existing *citation key*, since they are one value under two names, the source's and the model's.

**Source fidelity** *(added 2026-08-04 at convergence — see Refinements)*

- **FR-031**: XML character escaping carried in a source field's text MUST be resolved to the characters it represents. Text that is not XML character escaping, a bare ampersand among it, MUST be left exactly as written.
- **FR-032**: Where a source value states something the catalogue's field holds in a different form, it MUST be normalized to that form. Where the value cannot be resolved to that form, the field MUST be preserved under FR-025 rather than truncated, guessed at, or allowed to fail its entry.
- **FR-033**: A date a source records as the date its subject was retrieved MUST be mapped to the item's access date.

### Requirement coverage

- **User Story 1** carries FR-006 through FR-016: reading a file and mapping what it holds.
- **User Story 2** carries FR-017 through FR-021.
- **User Story 3** carries FR-022 through FR-024.
- **User Story 4** carries FR-025 and FR-026.
- **FR-001 through FR-005** define the format's relationship to the import contract and constrain every story.
- **FR-027 through FR-030** are package-wide constraints, and each story's acceptance is judged against them.
- **FR-031 through FR-033** were added at convergence, from defects the four stories' own acceptance could not have caught: each is a case where a record is created and reported as created while quietly holding less than its source stated. They belong to no single story and are asserted against the committed corpus.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An exported reference library becomes a populated catalogue in one call, without converting the file first and without anyone naming its dialect.
- **SC-002**: Across the committed corpus described under *Verification corpus*, no entry is refused for a reason that normalization resolves, and every entry that is refused carries a reason naming what could not be recovered.
- **SC-003**: A DOI written as a resolver URL is stored as a valid DOI identifier, so a record is not lost to the most common way exports write that field.
- **SC-004**: Accented and non-Latin text arrives in the catalogue as characters, and no stored title, name, or field value contains LaTeX markup the decoder recognised.
- **SC-005**: The same library exported as classic BibTeX and as BibLaTeX produces equivalent catalogue records, judged on item type, contributors and their order, dates and their precision, and identifiers.
- **SC-006**: Every field present in a source entry is either mapped to its CSL equivalent or retrievable from the stored record afterwards. No field is absent from both.
- **SC-007**: Contributor order and role survive the import, so an item's first author is the file's first author.
- **SC-008**: No content in a `.bib` file, however malformed, produces an unhandled error, and every malformed-input case is reported through the import result.
- **SC-009**: Adding this format required no change to the import workflow, the reported result, or the code that builds an item from CSL JSON, which is what demonstrates the contract was drawn in the right place.

### Verification corpus

The criteria above are judged against files committed to the repository, so the result is reproducible and no test reaches the network. The corpus holds three kinds of file:

- Constructed fixtures, each isolating one malformation this specification names, so a failure points at the rule it broke.
- A genuine export per dialect from a mainstream reference manager, which is what the roadmap means by representative real-world files and is the only thing that catches malformations nobody thought to construct.
- At least one file large enough that a whole-file conversion would be visible, which is what FR-004 is asserted against.

Exported files carry bibliographic metadata only, with anything personal removed. Bibliographic metadata is factual and raises no licensing question.

## Assumptions

- **The import contract is inherited, not revisited.** The workflow, atomicity, reporting, dry runs, and configured-format lookup delivered under issue #21 apply unchanged. This feature supplies the two stages a format owns.
- **The caller names the format.** Detecting a file's format from its name or content remains out of scope, as settled for the contract.
- **CSL JSON is the intermediate representation.** The existing conversion builds the item and its related records, and this feature does not change its behaviour for callers using it directly.
- **The existing catalogue behaviour is inherited.** Batch-scoped citation-key de-duplication, partial-date fallbacks, and unknown-identifier storage apply exactly as they do today.
- **De-duplication against already-stored records is out of scope**, as it was for the contract. Importing the same library twice produces two sets of items, and deciding when two records are the same reference remains a separate problem.
- **RIS is out of scope.** It is issue #23, and it is what will prove the contract holds for a second real format.
- **Export is out of scope.** Writing a `.bib` file from the catalogue is a later feature, though the mapping this feature documents is what an export would run in reverse.
- **No user interface.** Nothing here assumes a view, a form, or an upload. The front end is roadmap item R6.

## Refinements

### 2026-08-04 — planning found FR-004 stricter than the contract it inherits from

Two changes, agreed with the maintainer at the plan gate. Nothing in the feature's purpose, its user
stories, or its acceptance changed. One requirement was reworded and one was removed.

The parsing library chosen at planning (`research.md`) expands `@string` macros and resolves
`crossref` inheritance inside a single load of the file. That exposed two problems with requirements
written before the library was chosen.

**FR-004 was stricter than #21.** The import contract's FR-024 requires that an import not
materialise the whole file's *converted* content before storing any entry. FR-004 had tightened that
to all content, including parsed source text, which the contract never settled and which was not
argued on its merits at the spec gate. Reworded to the contract's scope. Converted content is where
the cost actually lives, an `Item` with its contributors, dates and identifiers per entry, and that
stays streamed.

**FR-005 was removed.** It required the source to be readable more than once, which existed solely to
pay for the original FR-004. With no second pass it asks something of the caller that nothing needs.
Its edge case went with it.

The number FR-005 is retired rather than reused, so FR-006 onward keep the identifiers the story
issues and the task list already cite.

### 2026-08-04 — an entry with no fields cannot be stored, and is reported instead

One edge case amended. No requirement, user story or acceptance criterion changed.

The spec said an entry carrying nothing but a type and a cite key would be stored, on the reasoning
that those two values are all the catalogue asks for. That reasoning still holds for the catalogue.
It does not hold for the file, because such an entry never arrives as an entry: the parsing library
chosen at planning treats a block with no fields as a comment, so there is no type and no cite key
to store by the time any of this feature's code runs. The full mechanism is in D11.

Closing the gap would mean either reaching into the library's private grammar or pre-scanning the
raw text for this one shape, which is the hand-written parsing the plan rejected for the feature as
a whole. Neither is worth it for a shape no reference manager emits — an export always carries at
least a title.

So the behaviour is now stated as it is: such a block is reported as skipped. That keeps the promise
the feature actually rests on, which is that nothing disappears without being reported, and it costs
a stored record that would have held no bibliographic content anyway. A test pins the current
behaviour, so if the parser is ever replaced the gap surfaces as a failing test rather than as
silence.

### 2026-08-04 — convergence added three requirements, from defects no story could see

Three requirements added (FR-031, FR-032, FR-033). No existing requirement, user story or acceptance
criterion changed.

Each came from checking the merged feature against the committed corpus rather than against a
story's own acceptance, and each has the same shape: an entry is created, reported as created, and
stored holding less than the source stated. That shape is invisible to a story, because every story
here was scoped to one behaviour and each one's acceptance passes.

**FR-031, source escaping.** The genuine Crossref export in the corpus writes `Knowledge Discovery
&amp; Data Mining` in a container title, because its text passed through an XML pipeline before it
reached a `.bib` file. It was stored with the entity intact. That is the same defect as an undecoded
`Kr{\"u}ger`, which FR-018 already rules out, so it belongs in the spec on the same reasoning: it is
recoverable from the value alone. The requirement's second sentence matters as much as its first,
and D23 records why.

**FR-032, normalize or preserve.** `langid = {english}` is a language name; the catalogue's language
field holds a tag of at most ten characters. Storing the name would have failed the entry on length
for a long enough name, and truncating it would have stored a wrong value silently. Neither is
acceptable, and the answer already existed in two places in this spec — FR-017's recover-what-you-
can and FR-025's preserve-what-you-cannot — so this states the general rule those two are instances
of.

**FR-033, access date.** BibLaTeX's `urldate`. `@online` entries are what a reader reaches for the
BibLaTeX dialect to describe, and the date of retrieval is most of what distinguishes one from an
undated web reference. The model has held an access date since before this feature.

# Feature Specification: A Standard Contract for Importing Bibliographic Files

**Feature Branch**: `003-import-contract`

**Created**: 2026-08-03

**Status**: Draft

**Serves**: G5 (import references from common bibliography formats) · Roadmap R5 · Issue #21

**Input**: Every bibliography format this package will ever read does the same job: take a file, turn its entries into stored items, and report what happened to each one. This feature settles the shared surface once, before the first format arrives, so that adding a format later is a mapping exercise rather than a new public API.

## Clarifications

### Session 2026-08-03

- Q: Per-entry importing was settled at intake, but is a *single* entry atomic? An entry produces an `Item` plus its related `ItemName`, `ItemDate`, and `ItemIdentifier` records, so a failure part-way through could leave a half-built item. → A: Yes, an entry is all-or-nothing. It lands complete or not at all, and a failure while building its related records stores nothing from that entry. The outcome vocabulary has no value meaning "partially created", and a half-built item would be exactly the kind of unqueryable, corrupted record Article XI exists to prevent. Per-record was agreed at the file level. It does not extend below the entry.
- Q: How does an entry result identify which entry in the file it refers to? "Enough positional information" was left unquantified. → A: By its zero-based index among the entries the format found, always present, plus a source handle the format supplies where the syntax offers one, such as a BibTeX cite key or an RIS record number. The index alone locates an entry mechanically, but "entry 47 failed" is close to useless to someone holding a 400-entry file, and the source's own key is what they will search for.
- Q: Does the existing log-a-warning behaviour survive, given the requirement that failures not be log-only? → A: The result is the reporting channel and every failure appears there. Logging may continue alongside it for operator visibility but is never the only place a failure surfaces. The existing `from_csl_json_list` keeps its current behaviour for callers using it directly, since this feature does not change that function's contract.
- Q: What data volume must an import handle, and is there a throughput target? → A: No throughput target. The roadmap's concern is correct handling of messy files, and any number set here would be invented. The one constraint that matters is that memory grows with the number of entries reported, not with a fully materialised conversion of the whole file held at once.
- Q: The feature introduces vocabulary (format, entry, outcome, import result) that `CONTEXT.md` does not carry, and "provider" and "record" are already circulating as informal synonyms. Is pinning that vocabulary part of this feature? → A: Yes. The glossary gains the new terms and the synonyms to avoid, in the same change, as Article VI requires of any public API addition.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import a file and learn what happened to every entry (Priority: P1)

A developer has a bibliographic file and a format that can read it. They call one documented function, naming the format and handing over the file. Every entry the file contains is attempted. Entries that convert cleanly become catalogue items, while entries that do not are reported individually with a reason the developer can act on. Nothing is dropped silently, and the developer never touches anything specific to the file's syntax.

**Why this priority**: This is the contract. Without it there is nothing for a format to plug into, and the two format features that follow have no shared surface to target.

**Independent Test**: Fully testable with a test-only format that yields a known mix of good, unreadable, and non-bibliographic entries. Run an import over it and assert that the catalogue contains exactly the good entries and the returned result accounts for every entry in the file.

**Acceptance Scenarios**:

1. **Given** a file whose entries all convert cleanly, **When** the developer runs an import naming its format, **Then** a catalogue item exists for each entry and the result reports each one as created.
2. **Given** a file in which one entry cannot be converted, **When** the developer runs an import, **Then** the remaining entries are still stored and the result reports that one entry as failed, with a reason and its index in the file.
3. **Given** a file whose format supplies a handle of its own for each entry, **When** an entry fails, **Then** that handle appears alongside the index in the entry's result.
4. **Given** an entry whose item is acceptable but one of whose contributors, dates, or identifiers is not, **When** the developer runs an import, **Then** nothing at all from that entry is stored and it is reported as a single failure.
5. **Given** a file containing an element the format recognises but that is not a bibliographic record, **When** the developer runs an import, **Then** the result reports that element as skipped rather than failed, and no item is created for it.
6. **Given** any file, **When** an import completes, **Then** the number of entry results equals the number of entries the format found, each appearing once and in the order they occur in the file.
7. **Given** a file that the format cannot parse at all, **When** the developer runs an import, **Then** the failure is reported through the result rather than raised as an unhandled error.
8. **Given** a format that yields its entries one at a time, **When** an import runs, **Then** entries are consumed and stored progressively rather than the whole file being converted before anything is stored.

---

### User Story 2 - Rehearse an import without changing anything (Priority: P2)

Before committing a library of several hundred references, a developer wants to know what the import will do. They run the same import as a rehearsal. Every stage executes and every entry is reported exactly as it would be in earnest, but the catalogue is untouched when the run finishes.

**Why this priority**: A messy real-world export is the normal case, and per-entry importing means a bad file leaves a partially populated catalogue to reconcile by hand. A rehearsal turns that from a cleanup problem into a decision made before anything is written. It is second because the contract has to exist before it can be rehearsed.

**Independent Test**: Run an import over the same file twice, once as a rehearsal and once in earnest, and assert the two results report identical outcomes while the catalogue is unchanged after the rehearsal.

**Acceptance Scenarios**:

1. **Given** a file containing entries that would be created, **When** the developer runs a dry run, **Then** the result reports them as created and the catalogue contains no new items afterwards.
2. **Given** a file containing an entry that would fail, **When** the developer runs a dry run, **Then** the failure and its reason appear in the result exactly as they would in a real run.
3. **Given** any completed import result, **When** the developer inspects it, **Then** it states whether it came from a dry run.
4. **Given** a dry run over a file, **When** the same file is then imported in earnest, **Then** the outcomes reported by the two runs match.

---

### User Story 3 - Discover which formats are available (Priority: P3)

A developer, or code acting on their behalf, needs to know which file formats this installation can read without knowing anything about them individually. They ask for the registered set and get back the names, each of which can be used to run an import.

**Why this priority**: It is what lets a caller stay ignorant of the individual formats, which is the point of having a contract at all. It is last because an import can be run by handing over a format directly, so the registry is a convenience over a working core rather than a precondition for one.

**Independent Test**: Register a test-only format, assert it appears in the enumerated set, run an import by naming it, and assert an unregistered name is rejected with a message that names what is registered.

**Acceptance Scenarios**:

1. **Given** a registered format, **When** the developer enumerates the available formats, **Then** the registered format appears in the result.
2. **Given** a registered format name, **When** the developer runs an import naming it, **Then** the import uses that format.
3. **Given** a name that is not registered, **When** the developer runs an import naming it, **Then** the call fails with an error that names the formats that are registered.
4. **Given** a name already registered, **When** a second format is registered under that name, **Then** the registration fails rather than replacing the first silently.

---

### Edge Cases

- **A file with no entries at all.** An empty file, or one holding only comments, is a successful import of nothing rather than an error: the result is empty and the catalogue is unchanged.
- **A file that is not what it claims to be.** A file named for one format but holding something else entirely produces a reported parse failure, never an unhandled error or a crash.
- **A truncated file.** A file cut off mid-entry reports the entries recovered before the truncation and a failure covering the remainder.
- **An entry that parses but will not convert.** An entry the format reads successfully but whose content the catalogue rejects, whether an unrecognised item type or no usable citation key, is a per-entry failure carrying the rejection reason, not a whole-file failure.
- **An entry that fails part-way through being built.** An entry whose item is acceptable but one of whose contributors, dates, or identifiers is rejected leaves nothing stored from that entry, and is reported as one failure rather than a partial success.
- **Repeated citation keys inside one file.** The catalogue's existing behaviour applies unchanged: colliding keys within a single import are given distinguishing suffixes, and each entry is still reported as created.
- **An entry that fails during a dry run.** Reported identically to a real run, with the rest of the file still evaluated.
- **A file in an unexpected text encoding.** Reported as a parse failure with the encoding named in the reason, rather than storing corrupted text.

## Requirements *(mandatory)*

### Functional Requirements

**The workflow**

- **FR-001**: The package MUST provide one documented way to import a bibliographic file, identical for every format.
- **FR-002**: An import MUST run a fixed sequence of stages: read the file, parse it into entries, convert each entry to CSL JSON, and build an `Item` with its related records from that CSL JSON.
- **FR-003**: A format MUST supply only the file-to-entries and entry-to-CSL JSON stages. It MUST NOT be able to change how an `Item` is built from CSL JSON.
- **FR-004**: Building an `Item` MUST reuse the package's existing CSL JSON conversion, whose behaviour for callers using it directly MUST be unchanged by this feature.
- **FR-005**: A caller MUST be able to run an import without referring to anything specific to the file's format.
- **FR-006**: An entry MUST be stored in full or not at all. Where any part of an entry cannot be stored, whether its `Item` or any related `ItemName`, `ItemDate`, or `ItemIdentifier`, nothing from that entry MUST remain stored.

**Reporting**

- **FR-007**: An import MUST return one result per entry the format found, each appearing exactly once, in the order the entries occur in the source file.
- **FR-008**: Each entry result MUST carry an outcome drawn from a fixed vocabulary: created, skipped, or failed.
- **FR-009**: Each entry result MUST identify its entry by a zero-based index among the entries the format found, and MUST additionally carry a source-supplied handle for that entry, such as a cite key or a record number, where the format's syntax offers one.
- **FR-010**: A failed entry result MUST carry a reason stating why the entry could not be imported.
- **FR-011**: A skipped entry result MUST be distinguishable from a failed one, so that a format can report an element it recognises but that is not a bibliographic record without presenting it as an error.
- **FR-012**: An entry that fails MUST NOT stop the remaining entries in the file from being imported.
- **FR-013**: Every failure MUST be present in the returned result. Log output MAY carry the same failures for operator visibility, but MUST NOT be the only place a failure appears.
- **FR-014**: A failure that prevents the file being parsed at all MUST be reported through the same result rather than raised to the caller as an unhandled error.

**Rehearsal**

- **FR-015**: An import MUST be runnable as a dry run that executes every stage and produces the same result, while leaving the stored catalogue exactly as it was before the run.
- **FR-016**: An import result MUST state whether it came from a dry run.

**Registration**

- **FR-017**: A format MUST be registerable under a name, and the registered set MUST be enumerable by a caller that knows nothing about the individual formats.
- **FR-018**: An import MUST be runnable by naming a registered format.
- **FR-019**: Naming a format that is not registered MUST fail with an error that names the formats which are registered.
- **FR-020**: Registering a second format under an already-registered name MUST fail rather than silently replacing the first.

**Package conventions**

- **FR-021**: Every name the contract makes public MUST be importable from the `literature` namespace (Article X).
- **FR-022**: Every human-readable string the contract produces, including failure reasons, MUST be translatable (Article VIII).
- **FR-023**: File content MUST be treated as untrusted input: no input in a source file may cause code execution, filesystem access outside the file being read, or an unhandled error (Article V).
- **FR-024**: An import MUST consume a format's entries one at a time rather than requiring the whole file's converted content to be materialised before any entry is stored.
- **FR-025**: The vocabulary this feature introduces (format, entry, outcome, import result) MUST be added to `CONTEXT.md`, together with the synonyms it retires, in the same change that introduces it (Article VI).

### Requirement coverage

- **User Story 1** carries FR-001 through FR-014: the workflow itself and everything it reports.
- **User Story 2** carries FR-015 and FR-016.
- **User Story 3** carries FR-017 through FR-020.
- **FR-021 through FR-024** are constraints on every story rather than work belonging to any one of
  them, and each story's acceptance is judged against them.
- **FR-025** is a documentation requirement covering the feature as a whole, verified by
  inspection of `CONTEXT.md` rather than by a scenario.

### Key Entities

- **Format**: A plug-in for one bibliographic file syntax, such as BibTeX or RIS. It knows how to turn a file into entries and how to express one entry as CSL JSON, and nothing else. It is registered under a name.
- **Entry**: One bibliographic record as it appears in a source file, before it becomes an `Item`. The unit that an outcome is reported against.
- **Import result**: The report from one import run. Holds one entry result per entry found, in source order, and records whether the run was a dry run.
- **Entry result**: The fate of a single entry — its outcome, its zero-based index in the source file, the source's own handle for it where the format offers one, the `Item` it produced where there is one, and a reason where it failed.
- **Outcome**: The fixed vocabulary an entry result draws from: created, skipped, or failed.
- **Format registry**: The set of formats this installation can read, keyed by name, enumerable without knowing what is in it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can import a bibliographic file with one documented call and, without reading anything specific to that file's format, determine for every entry whether it was created, skipped, or failed, and for every failure, why.
- **SC-002**: Every entry in a source file is accounted for in the result exactly once. Over files containing valid, invalid, and non-bibliographic entries, the number of entry results equals the number of entries the format found.
- **SC-003**: A file containing failing entries still imports every entry that converts cleanly, so no single bad record can block a library.
- **SC-004**: A dry run leaves the stored catalogue identical to its state beforehand while reporting the same per-entry outcomes as the equivalent real run.
- **SC-005**: No import failure is discoverable only by reading log output or by comparing a count of inputs against a count of results.
- **SC-006**: Adding support for a further format requires supplying only the parse and convert stages and registering the result, with no change to the import workflow, the reported result, or the code that builds an `Item`. Demonstrated by the test-only format standing in for a real one.
- **SC-007**: No file content, however malformed, causes an unhandled error, and every malformed-input case is reported through the result.
- **SC-008**: No entry ever leaves a partial record behind. After any import, every entry in the file is either fully present in the catalogue or wholly absent from it, with no entry contributing an item missing its contributors, dates, or identifiers.
- **SC-009**: A failure report locates its entry well enough to act on: every failed entry result carries an index, and carries the source's own handle for that entry whenever the format can supply one.

## Assumptions

- **CSL JSON is the intermediate representation.** Every format converts to CSL JSON and the existing conversion takes it from there. This is what makes the contract adaptable to any format, and it means the shared half of the workflow is already-exercised code rather than new abstraction.
- **The caller names the format.** Working out which format a file holds from its name or its content is not part of this feature. The place to decide that is wherever files are accepted from users, which does not exist yet.
- **De-duplication against already-stored records is out of scope** (settled at intake). Deciding when two records are the same reference is a separate problem with nothing to do with file formats. The outcome vocabulary leaves room for it: a later feature that can make that judgement reports its decisions as skipped without changing the contract.
- **Export is out of scope**, though the same workflow is expected to run in reverse later, so the contract should not make an export counterpart harder to add.
- **No concrete format ships here.** BibTeX (#22) and RIS (#23) follow. This feature is verified against a test-only format that exists solely to exercise the contract, which is also what keeps the workflow honest: a contract that only one real format can satisfy is not a contract.
- **No user interface.** Nothing here assumes a view, a form, or an upload.
- **The existing catalogue behaviour is inherited, not revisited.** Batch-scoped citation-key de-duplication, partial-date fallbacks, and unknown-identifier storage all apply exactly as they do today.

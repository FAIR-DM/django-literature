# Feature Specification: Import a Bibliography File Through the Front End

**Feature Branch**: `011-import-bibliography-file`

**Created**: 2026-08-24

**Status**: Draft

**Serves**: G4 (a full front end as an opt-in app built on django-mvp) · G5 (import references from common bibliography formats) · Roadmap R6 · Issue #50

**Input**: The package already reads BibTeX and RIS files, but only from code. Someone using the interface should be able to hand it a file exported from their reference manager and have the references land in the catalogue without writing anything. Afterwards they need to see what became of every entry in the file, including which ones failed and why, rather than guessing from a count.

## Clarifications

### Session 2026-08-24 — intake

- Q: Does the outcome report need to survive the page, or is it enough to render it once on the response? → A: Once is enough. Nothing about the run is stored, there is no record to return to, and re-importing the file is how the same report is seen again. A persisted import record would mean a model, a list page and a retention decision, and none of that is what the issue asks for.
- Q: The issue's closing sentence allows two landings — a report page, or a redirect to the catalogue carrying a summary message. Which? → A: Always the report page. A summary message on the catalogue is exactly the count the issue rules out, so the redirect is not a variant of the requirement, it is the failure the requirement names.
- Q: Where is the entry point? The original description put a button on every page of the front end. → A: An action in the catalogue table's toolbar, not a global control. The catalogue is where someone is when they decide to add references to it.
- Q: Does the import run while the reader waits, or in the background? → A: In the request. Background imports are a later feature with their own specification, and building the waiting version first is what makes the background version worth having.

### Session 2026-08-24 — clarification scan

Resolved from the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: Which formats does the reader choose from? → A: Whichever formats the installation has configured, read at the time the page is rendered. Today that is BibTeX and RIS. A project that configures a third format sees it in the list without any change to the front end, because the front end asks the configuration rather than carrying its own list.
- Q: What happens when the chosen format does not match the attached file — RIS chosen, a `.bib` file attached? → A: The import runs and the format reports the whole file as one failed entry with its own reason, which already names the mismatch in words a reader can act on. The front end does not sniff the file, and it does not second-guess the reader's choice.
- Q: The result identifies each entry by a zero-based index. Is that what the reader sees? → A: No. The report counts entries from one, which is how a person counts them in a file, and shows the citation key beside the position wherever the format carries one. The zero-based index stays what it has always been, an identifier in the result the code hands back. This is a deliberate divergence and is written down so nobody later "corrects" one to match the other.
- Q: The issue rules out guessing from a count. Does the report show counts at all? → A: Yes, alongside the per-entry list, never instead of it. How many were created, skipped and failed is the first thing a reader wants; which ones failed and why is the thing they cannot get anywhere else.
- Q: Is the report grouped by outcome, or in the order the entries appear in the file? → A: Source order, so a reader can follow it against the file they submitted. Failed entries are distinguishable within that order rather than lifted out of it.
- Q: A four-hundred-entry file produces a four-hundred-row report. Is the report paginated? → A: No. The report exists once, so a second page of it would be a page the reader cannot return to. It is one page however long the file was.
- Q: The catalogue has two presentations — the table it serves by default and the card list a project can route to instead. Does the import action appear on both? → A: Both. FS-010 settled this exact fork for search and filtering: a project that chooses the card presentation must not silently lose a capability. The action is defined once and each presentation renders it in its own idiom.
- Q: Nothing already stored is compared against an incoming entry, so importing the same file twice produces two sets of references. Does the front end warn? → A: It states it plainly on the import page, before the reader submits. It does not detect it, because detecting it is a decision the package has taken twice and refused twice (ADR 0009, ADR 0023) and this feature is not the occasion to reopen it.
- Q: A run that fails partway leaves the entries before the failure stored. Does the reader learn that? → A: The report shows it, because every entry appears with its own outcome — the created ones are created whatever happened after them. The documentation states it as well, since it is the one thing about the import a reader could reasonably assume the other way.
- Q: Does the feature change the import contract, any model, or ship a migration? → A: None of the three. It is a front-end path onto a contract that already returns everything the report needs. If something the report requires turns out to be missing from the result, that is a finding raised as its own issue rather than a contract change smuggled in here.
- Q: `CONTEXT.md` defines *import result* and *entry result* but has no term for the page that renders them. → A: The page is the **import report**, and the glossary gains it as the front end's rendering of an import result. It is a new thing rather than a new word for an existing one, so it does not collide with the synonyms the glossary already retires.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import a file and see what became of every entry (Priority: P1)

Someone looking at the catalogue has a file their reference manager just exported. They pick the import action from the catalogue's toolbar, choose the format the file is in, attach it and submit. The import runs, and they land on a report of it: how many references were created, skipped and failed, followed by every entry in the file in the order it appeared, each one saying what became of it, carrying its citation key where the file gave one, and carrying a reason wherever it failed. Created references link to their pages in the catalogue, and the report offers a way back to the catalogue.

**Why this priority**: It is the entire feature. Delivered alone, someone with a reference manager can populate a catalogue without writing any code, which is the gap the issue names.

**Independent Test**: Install the front end over an empty catalogue, take a real `.bib` export containing a mix of good entries and at least one that cannot be converted, import it through the interface, and confirm the references appear in the catalogue and that the report accounts for every entry in the file including the failure and its reason.

**Acceptance Scenarios**:

1. **Given** the catalogue page, **When** its toolbar is read, **Then** an action leading to the import page is present.
2. **Given** the import page, **When** it is opened, **Then** it offers a choice of the configured formats and a control for attaching a file.
3. **Given** the import page, **When** its format choices are read, **Then** they are the formats the installation has configured and nothing else.
4. **Given** a valid file and a matching format, **When** the form is submitted, **Then** the references in the file are created in the catalogue.
5. **Given** a completed import, **When** the response is shown, **Then** it is a report of that import and not the catalogue page.
6. **Given** a completed import, **When** the report is read, **Then** it states how many entries were created, how many skipped and how many failed.
7. **Given** a file of several entries, **When** the report is read, **Then** every entry in the file appears exactly once, in the order it appeared in the file.
8. **Given** an entry the file gave a citation key for, **When** its row is read, **Then** that key is shown beside its position.
9. **Given** an entry the format minted a key for, **When** its row is read, **Then** the key as stored is shown.
10. **Given** an entry carrying no key at all, **When** its row is read, **Then** it is identified by its position alone and nothing is invented for it.
11. **Given** a failed entry, **When** its row is read, **Then** it states the reason it failed in a sentence a reader can act on.
12. **Given** a created entry, **When** its row is read, **Then** it links to that reference's page in the catalogue.
13. **Given** entries are numbered in the report, **When** the first one is read, **Then** it is numbered one.
14. **Given** a report, **When** it is read, **Then** it offers a way back to the catalogue.
15. **Given** a file where an entry fails after several have been created, **When** the report is read, **Then** the created entries are reported created and are present in the catalogue.
16. **Given** a file of four hundred entries, **When** the report is shown, **Then** every entry appears on the one page and the report is not paginated.
17. **Given** the catalogue routed at the card list instead of the table, **When** its toolbar is read, **Then** the same import action is present and leads to the same page.
18. **Given** the import page, **When** it is read before submitting, **Then** it says that importing the same file twice creates the references twice.
19. **Given** an import that created references, **When** the catalogue is opened afterwards, **Then** they are in it.

---

### User Story 2 - Be told when the file cannot be used (Priority: P2)

Someone attaches the wrong thing, or nothing, or a file the chosen format cannot read. They are told which, in words that say what to do about it, and they are never shown a server error or an empty report they have to interpret.

**Why this priority**: It is what makes the first story survive contact with a real reader, and the failures it covers are the ordinary ones — a file picked from the wrong folder, a format chosen from habit. It sits second because the successful path is what the feature is for.

**Independent Test**: Submit the import form with no file, then with an empty file, then with a RIS file while BibTeX is chosen, and confirm each is reported in the interface with a reason and none produces a server error.

**Acceptance Scenarios**:

1. **Given** the import form, **When** it is submitted with no file attached, **Then** the form is redisplayed saying a file is required and nothing is imported.
2. **Given** the import form, **When** it is submitted with no format chosen, **Then** the form is redisplayed saying a format is required and nothing is imported.
3. **Given** an empty file, **When** it is submitted, **Then** the outcome is reported in the interface with a reason and no server error is raised.
4. **Given** a file the chosen format cannot read at all, **When** it is submitted, **Then** a report is shown carrying the format's own reason for refusing it.
5. **Given** a file whose bytes cannot be decoded, **When** it is submitted, **Then** the outcome is reported in the interface and no server error is raised.
6. **Given** any file at all, **When** it is submitted, **Then** the request completes with a page rather than an unhandled error.
7. **Given** a file the chosen format could not read, **When** the catalogue is opened afterwards, **Then** nothing was added to it.

---

### User Story 3 - The demo serves it, and a broken one is caught (Priority: P3)

The demo project offers the import path over its own front end, and the guard that walks the demo in CI imports a file, reads the report and fails the build when the action disappears, the import stops creating references, or the report stops accounting for the entries.

**Why this priority**: It is how the feature stays working after the release that introduces it, and it is the standing pattern for front-end work in this package.

**Independent Test**: Run the demo's guard against the branch and confirm it reaches the import page from the catalogue, submits a file and reads the report; then break each of those in turn and confirm the guard fails.

**Acceptance Scenarios**:

1. **Given** the demo running, **When** the guard opens the catalogue, **Then** it finds the import action in the toolbar and follows it.
2. **Given** the demo running, **When** the guard submits a bibliography file, **Then** it confirms the references were created.
3. **Given** the demo running, **When** the guard reads the report, **Then** it confirms every entry in the submitted file is accounted for, including a failure and its reason.
4. **Given** the import action is removed, the import stops creating references, or the report stops listing entries, **When** the guard runs, **Then** it fails.

---

### Edge Cases

- A file containing exactly one entry produces a report of one row, with the same counts and the same structure as a long one.
- A file that parses but yields no entries at all — every one of them skipped — produces a report saying so, not an empty page.
- A file whose entries all fail produces a report of failures and leaves the catalogue as it was.
- A failure reason carrying characters that mean something in markup is shown as text, not interpreted.
- A very large file blocks the request for as long as the import takes, because the import runs in the request; the host's own upload and timeout limits are what bound it.
- A reader who reloads the report page does not re-run the import.
- A citation key long enough to be awkward in a table is still shown in full rather than silently truncated to something that no longer matches the file.

## Requirements *(mandatory)*

### Functional Requirements

**Reaching the import**

- **FR-001**: The catalogue MUST offer an action in its toolbar leading to the import page.
- **FR-002**: The toolbar action MUST be defined once and MUST appear on both catalogue presentations, the table and the card list.
- **FR-003**: The import page MUST be reachable at a named route within the front end's namespace.

**Submitting a file**

- **FR-004**: The import page MUST offer a choice of format and a control for attaching a file.
- **FR-005**: The format choices MUST be the formats the installation has configured, read when the page is rendered, and MUST NOT be a list held by the front end.
- **FR-006**: The form MUST require both a format and a file, and MUST redisplay itself with a reason when either is missing.
- **FR-007**: The front end MUST NOT inspect the file to determine its format, and MUST import it as the format the reader chose.
- **FR-008**: The import page MUST state, before submission, that importing the same file twice creates the references twice.
- **FR-009**: The import MUST run within the request that submitted it.
- **FR-010**: A submitted file MUST be imported through the package's existing import contract, with no separate reading path in the front end.

**The report**

- **FR-011**: A completed import MUST render an import report, and MUST NOT redirect to the catalogue.
- **FR-012**: The report MUST state how many entries were created, how many skipped and how many failed.
- **FR-013**: The report MUST list every entry in the file exactly once, in the order the entries appeared in it.
- **FR-014**: The report MUST NOT be paginated.
- **FR-015**: Each entry MUST show its outcome as one of created, skipped or failed, using the vocabulary the package already fixes for it.
- **FR-016**: Each entry MUST be numbered by its position in the file counting from one.
- **FR-017**: Each entry MUST show its citation key where the format carries or mints one, and MUST show nothing in its place where there is none.
- **FR-018**: Every failed entry MUST show its reason.
- **FR-019**: Failed entries MUST be distinguishable from the rest without being lifted out of source order.
- **FR-020**: Each created entry MUST link to that reference's page in the catalogue.
- **FR-021**: The report MUST offer a way back to the catalogue.
- **FR-022**: A failure reason MUST be rendered as text, so that characters meaningful in markup cannot be interpreted.
- **FR-023**: Reloading the report MUST NOT re-run the import.

**Failing safely**

- **FR-024**: A file the chosen format cannot read MUST produce a report carrying the format's own reason, not a server error.
- **FR-025**: A file whose bytes cannot be decoded MUST be reported in the interface, not raised.
- **FR-026**: No submitted file MUST be able to end the request in an unhandled error.
- **FR-027**: Entries created before a later entry failed MUST remain created, and MUST be reported as created.

**Boundaries**

- **FR-028**: The feature MUST NOT change the import contract, any model, or any converter, and MUST ship no migration.
- **FR-029**: The feature MUST NOT add duplicate detection, and MUST NOT compare an incoming entry against anything already stored.
- **FR-030**: The feature MUST NOT offer a preview or dry run.
- **FR-031**: The feature MUST NOT store anything about the run.
- **FR-032**: A core-only install MUST resolve nothing this feature adds.
- **FR-033**: Every user-facing string this feature introduces MUST be translatable.

**The demo and the documentation**

- **FR-034**: The demo MUST serve the import path, and MUST carry a bibliography file containing both entries that convert and at least one that does not.
- **FR-035**: The demo's guard MUST reach the import page from the catalogue, submit that file, read the report, and MUST fail when the action, the import or the report stops working.
- **FR-036**: The documentation MUST describe importing a file through the interface, state that the format is the reader's choice rather than detected, state that a repeated import creates the references again, state that entries created before a failure stay created, and state that the import runs while the reader waits.
- **FR-037**: `CONTEXT.md` MUST define *import report* as the front end's rendering of an import result.

### Key Entities

No new entity, no changed field and no migration. The report renders what the import contract already returns: the import result, its entry results, and each one's outcome, position, citation key, reason and created `Item`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Someone with a BibTeX or RIS export populates a catalogue through the interface without writing any code.
- **SC-002**: After any import, every entry in the submitted file is accounted for on one page, in source order, each with its outcome.
- **SC-003**: Every failed entry carries a reason naming what was wrong with it.
- **SC-004**: A reader reaches a created reference's page from the report in one action.
- **SC-005**: No submitted file — empty, undecodable, of the wrong format, or absent — produces a server error.
- **SC-006**: The import path is reachable from both catalogue presentations.
- **SC-007**: The feature ships no migration and changes no model.
- **SC-008**: Installing the core alone resolves nothing this feature added.
- **SC-009**: The demo's guard fails when the import action, the import itself, or the report stops working.

## Assumptions

- The import contract returns everything the report needs — an outcome, a position, a citation key where one exists, a reason on every failure and the created reference — so this feature reads it rather than extending it. If something proves missing, it is raised as its own issue against the contract rather than changed here.
- Nothing in the front end checks permissions, so the import page is reachable by whoever can reach the catalogue, matching what FS-008 settled for creating, editing and deleting references. Import is the most consequential write the front end offers, so this is stated rather than assumed silently.
- The package imposes no size limit of its own on the submitted file. The import runs in the request, so what bounds a large file is the host project's upload and request limits, and the documentation says so rather than the package inventing a number.
- Background imports are a separate feature with their own specification. Nothing here is designed around a future move off the request, because the report is what a background import would have to reproduce and it is worth building once against the simple case first.
- Duplicate detection stays refused. ADR 0009 and ADR 0023 both settled it, and a front end that quietly acquired it would contradict the documented behaviour of the same import run started from code.
- Both catalogue presentations carry the action, following the boundary FS-010 drew when it gave search and filtering to the card list as well as the table.
- The formats offered are read from the installation's configuration, so this feature needs no change when a format is added or removed.

# Feature Specification: Import a Bibliography File Through the Front End

**Feature Branch**: `011-import-bibliography-file`

**Created**: 2026-08-24

**Status**: Draft

**Refined**: 2026-08-24 — a preview step, the presentation of the report, and a reason on skipped entries. Sam, in session, after using the shipped pages. See `decisions.md` D16-D18.

**Refined again**: 2026-08-24 — the preview and the success page each become pages in their own right, with their own addresses, and the preview loses the form. Sam, in session, after using the preview. See FR-045 to FR-055 and `decisions.md` D30. `plan.md` and `tasks.md` carry the cascade.

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

---

### User Story 4 - Preview an import before it happens (Priority: P1)

*Added by the 2026-08-24 refinement.*

Someone attaches a file and submits it. Instead of the references appearing, they get the same report they would have got — every entry, its outcome, its citation key, its reason — under a heading saying nothing has been imported yet, and a button to go ahead. They read it, see that four entries would fail, and either accept that and confirm, or fix the file and start again. Nothing was written to the catalogue while they decided. Someone who does not want the extra step ticks a box on the form and the import happens directly.

**Why this priority**: A file from a reference manager is the least trustworthy input this package takes, and the report is only useful before the fact if reading it can still change the outcome. It shares P1 with the story it modifies, because previewing is now the default path through the feature rather than an addition to it.

**Independent Test**: Submit a mixed file, confirm the catalogue is unchanged and the page says so, confirm the preview, and confirm the same entries the preview described are now the ones in the catalogue. Then repeat with the skip box ticked and confirm the references arrive in one step.

**Acceptance Scenarios**:

1. **Given** the import form, **When** a file is submitted with the default settings, **Then** the catalogue is unchanged and the page states that nothing has been imported.
2. **Given** a preview, **When** it is read, **Then** it reports every entry exactly as a real import of the same file would.
3. **Given** a preview, **When** it is read, **Then** it offers a control that carries out the import it described.
4. **Given** a preview, **When** its import is carried out, **Then** the entries it reported as created are the ones now in the catalogue.
5. **Given** a preview, **When** its import is carried out, **Then** the reader is not asked to attach the file again.
6. **Given** the import form, **When** the skip control is ticked and the form submitted, **Then** the references are imported in one step and the report describes what was imported rather than what would be.
7. **Given** the import form, **When** it is first opened, **Then** the skip control is not ticked.
8. **Given** a file staged by one session, **When** another session attempts to confirm it, **Then** nothing is imported and the attempt is reported as having nothing to confirm.
9. **Given** a preview that was never confirmed, **When** the staged file is looked for later, **Then** it has been swept.
10. **Given** a confirmation for a file that is no longer staged, **When** it is submitted, **Then** the page says so plainly and imports nothing.
11. **Given** a confirmed import, **When** it completes, **Then** the file it was staged from is no longer held.
12. **Given** a preview of a file the chosen format cannot read, **When** it is read, **Then** it reports the format's own reason and offers no confirmation.

---

### User Story 5 - Read why an entry was skipped (Priority: P2)

*Added by the 2026-08-24 refinement.*

A reader looks at a report and sees an entry that was neither created nor failed. Today the row says "skipped" and stops, with no key and no explanation, which tells them nothing they can act on. The format always knows why — it was a comment block, or header material before the first record, or a fragment carrying no type — and it should say so.

**Why this priority**: A row a reader cannot interpret is a defect in the thing this feature exists to provide. It sits below the preview because a skipped entry is not a loss, only an unexplained one.

**Independent Test**: Import a file containing a comment block and a truncated trailing entry, and confirm each skipped row carries a reason naming what it was.

**Acceptance Scenarios**:

1. **Given** an entry a format skips, **When** its result is read, **Then** it carries a reason saying why.
2. **Given** a BibTeX file containing a comment or preamble block, **When** it is imported, **Then** that block is reported skipped with a reason naming what it was.
3. **Given** an RIS file with header material before its first record, **When** it is imported, **Then** that material is reported skipped with a reason naming what it was.
4. **Given** a skipped entry, **When** its row in the report is read, **Then** the reason appears in the same place a failure's reason appears.
5. **Given** a created entry, **When** its result is read, **Then** it carries no reason, exactly as before.
6. **Given** an existing caller reading a result, **When** it inspects a skipped entry, **Then** nothing that worked before has changed except that a reason is now present.

---

---

### User Story 6 - The preview is a page, not a response (Priority: P1)

*Added by the second 2026-08-24 refinement.*

Someone submits a file and lands on a page of its own, titled for what it is, that tells them what they are looking at. If anything in the file was skipped or would fail, a warning above the table says so before they read a single row. They narrow the table to just the failures with one click, read them, and then choose from a single row of three: go back to the catalogue, start over with a different file, or go ahead. Going ahead lands them on a page saying what was created, offering the catalogue or another import.

**Why this priority**: The preview is the step that makes the whole feature safe to use, and a page a reader cannot parse at a glance does not do that. It shares P1 with the stories it reshapes.

**Independent Test**: Submit a mixed file, confirm the browser is at the preview's own address, that the page carries a warning naming the trouble, that the outcome control narrows the table without a request, and that the three controls do what they say. Confirm, and check the browser is at the success address with the counts on it.

**Acceptance Scenarios**:

1. **Given** the import form, **When** a file is submitted, **Then** the browser ends at the preview's own address rather than the form's.
2. **Given** the preview page, **When** it is read, **Then** it carries no import form.
3. **Given** the preview page, **When** it is read, **Then** it is titled for what it is and carries a description beneath the title.
4. **Given** a file in which at least one entry was skipped or failed, **When** the preview is read, **Then** a warning above the table says so.
5. **Given** a file in which every entry would be created, **When** the preview is read, **Then** no such warning appears.
6. **Given** the preview page, **When** an outcome is chosen in the narrowing control, **Then** only rows of that outcome remain and no request is made.
7. **Given** a narrowed table, **When** the control is cleared, **Then** every row returns.
8. **Given** the preview page, **When** its foot is read, **Then** one row carries exactly three controls: back to the catalogue, restart, and confirm.
9. **Given** the preview page, **When** restart is chosen, **Then** the staged file is discarded and the reader is returned to an empty import form.
10. **Given** the preview page, **When** confirm is chosen, **Then** the browser ends at the success address rather than rendering the result in place.
11. **Given** the success page, **When** it is read, **Then** it states what was created and offers exactly two controls: back to the catalogue and import another file.
12. **Given** the preview address, **When** it is reached with nothing staged, **Then** the page says so plainly and does not raise.
13. **Given** the success address, **When** it is reached with nothing to report, **Then** the page says so plainly and does not raise.
14. **Given** the preview page, **When** it is reloaded, **Then** it shows the same preview and imports nothing.
15. **Given** any page this feature adds, **When** its breadcrumb is read, **Then** the step back to the catalogue is a link and carries the catalogue's own title.

---

### Edge Cases

- A file containing exactly one entry produces a report of one row, with the same counts and the same structure as a long one.
- A file that parses but yields no entries at all — every one of them skipped — produces a report saying so, not an empty page.
- A file whose entries all fail produces a report of failures and leaves the catalogue as it was.
- A failure reason carrying characters that mean something in markup is shown as text, not interpreted.
- A very large file blocks the request for as long as the import takes, because the import runs in the request; the host's own upload and timeout limits are what bound it.
- A reader who reloads the report page meets their browser's own offer to resubmit the form, which is what every server-rendered upload in Django does. The page itself carries nothing that re-runs the import.
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
- ~~**FR-011a**: The report page MUST carry the import form above the results, separated from them by a divider, so a second file can be submitted without navigating away.~~ **Reversed 2026-08-24 — the form on the results page was confusing to use. See FR-046 and `decisions.md` D30.**
- **FR-012**: The report MUST state how many entries were created, how many skipped and how many failed.
- **FR-013**: The report MUST list every entry in the file exactly once, in the order the entries appeared in it.
- **FR-014**: The report MUST NOT be paginated.
- **FR-015**: Each entry MUST show its outcome as one of created, skipped or failed, using the vocabulary the package already fixes for it, rendered as a badge whose colour encodes which of the three it is.
- **FR-016**: Each entry MUST be numbered by its position in the file counting from one.
- **FR-017**: Each entry MUST show its citation key where the format carries or mints one, and MUST show nothing in its place where there is none.
- **FR-018**: Every failed entry MUST show its reason, and every skipped entry MUST show why it was skipped.
- **FR-019**: Failed entries MUST be distinguishable from the rest without being lifted out of source order.
- **FR-020**: Each created entry MUST link to that reference's page in the catalogue.
- **FR-021**: The report MUST offer a way back to the catalogue as a button carrying a backward arrow, and a second button that returns to an empty import form.
- **FR-022**: A failure reason MUST be rendered as text, so that characters meaningful in markup cannot be interpreted.
- **FR-023**: One submission MUST import the file exactly once. *(Narrowed during planning from "reloading the report must not re-run the import" — see `decisions.md` D11. The second half of this requirement, that the report carry no control running the import again, was removed by the 2026-08-24 refinement: the report now carries the form deliberately, and the preview step is what makes a second run safe.)*
- ~~**FR-023a**: Where the submitted file could not be read at all, the form's submit control MUST read *Retry* and MUST stay disabled until the attached file changes.~~ **Reversed 2026-08-24 with FR-011a, which it depended on. *Restart import* on the preview page is now the way back to an empty form. See `decisions.md` D30.**

**Failing safely**

- **FR-024**: A file the chosen format cannot read MUST produce a report carrying the format's own reason, not a server error.
- **FR-025**: A file whose bytes cannot be decoded MUST be reported in the interface, not raised.
- **FR-026**: No submitted file MUST be able to end the request in an unhandled error.
- **FR-027**: Entries created before a later entry failed MUST remain created, and MUST be reported as created.

**Boundaries**

- **FR-028**: The feature MUST NOT change any model, MUST NOT change any converter, and MUST ship no migration. *(Amended 2026-08-24: the import contract does change, in one respect — a skipped entry may now carry a reason. See FR-018 and `decisions.md` D18.)*
- **FR-029**: The feature MUST NOT add duplicate detection, and MUST NOT compare an incoming entry against anything already stored.
- ~~**FR-030**: The feature MUST NOT offer a preview or dry run.~~ **Reversed 2026-08-24 — see FR-038 to FR-044 and `decisions.md` D16.**
- **FR-031**: The feature MUST NOT store any record of a completed import — no model, no table, no history. *(Amended 2026-08-24: a submitted file is now held between the preview and the confirmation, which is staging rather than a record. See FR-041 to FR-044.)*
- **FR-032**: A core-only install MUST resolve nothing this feature adds.
- **FR-033**: Every user-facing string this feature introduces MUST be translatable.

**Previewing before importing**

- **FR-038**: Submitting the import form MUST, by default, run the file as a preview that reports every entry exactly as a real import would and leaves the catalogue untouched.
- **FR-039**: A preview MUST be labelled as one, MUST state that nothing has been imported, and MUST offer a control that carries out the import it previewed.
- **FR-040**: The import form MUST offer a way to skip the preview and import directly, and that choice MUST default to previewing.
- **FR-041**: Carrying out a previewed import MUST NOT require the reader to attach the file a second time.
- **FR-042**: The identity of a staged file, and the format it was staged as, MUST be held in the reader's session and MUST NOT be carried in the page, so that a request can only confirm a file that same session staged.
- **FR-043**: A staged file MUST be removed once the import it was staged for is carried out, and staged files left behind by a preview that was never confirmed MUST be swept.
- **FR-044**: A confirmation naming a file that is no longer staged, or that this session never staged, MUST report that plainly and MUST import nothing.

**The preview page and the success page**

- **FR-045**: The preview MUST have its own address, distinct from the import form's, and submitting the form MUST redirect to it rather than rendering it in the response.
- **FR-046**: The preview page MUST NOT carry the import form.
- **FR-047**: The preview page MUST be titled for what it is, and MUST carry a description of what the reader is looking at beneath that title.
- **FR-048**: Where any entry was skipped or failed, the preview MUST carry a warning saying so above the table. Where none was, it MUST NOT.
- **FR-049**: The preview MUST offer a control that narrows the table to one outcome, and back to all of them, without leaving the page or issuing a request.
- **FR-050**: The preview MUST end with a single row of three controls: back to the catalogue, restart the import, and carry the import out.
- **FR-051**: Restarting MUST discard the staged file and return the reader to an empty import form.
- **FR-052**: A carried-out import MUST redirect to a success address rather than rendering its result in the response.
- **FR-053**: The success page MUST state what was created, and MUST offer two controls: back to the catalogue, and import another file.
- **FR-054**: Reaching the preview or the success address with nothing to show MUST say so plainly rather than raising or rendering an empty page.
- **FR-055**: On every page this feature adds, the breadcrumb back to the catalogue MUST be a link, and MUST use the catalogue's own title rather than the model's plural name.

**The demo and the documentation**

- **FR-034**: The demo MUST serve the import path, and MUST carry a bibliography file containing both entries that convert and at least one that does not.
- **FR-035**: The demo's guard MUST reach the import page from the catalogue, submit that file, read the preview, carry out the import it previewed, read the report, and MUST fail when the action, the preview, the confirmation or the report stops working.
- **FR-036**: The documentation MUST describe importing a file through the interface, state that the format is the reader's choice rather than detected, state that a repeated import creates the references again, state that entries created before a failure stay created, state that the import runs while the reader waits, and describe the preview step including how to skip it.
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
- **SC-009**: The demo's guard fails when the import action, the preview, the confirmation or the report stops working.
- **SC-010**: A reader sees what a file would do to the catalogue before any of it happens, and can decline.
- **SC-011**: A reader who wants the one-step import can have it, and has to ask for it.
- **SC-012**: No session can carry out an import staged by another session.
- **SC-013**: A preview that is never confirmed leaves nothing behind.
- **SC-014**: Every row of a report says what happened to that entry and, where it was not created, why.

## Assumptions

- The import contract returns everything the report needs — an outcome, a position, a citation key where one exists, a reason on every failure and the created reference — so this feature reads it rather than extending it. If something proves missing, it is raised as its own issue against the contract rather than changed here.
- Nothing in the front end checks permissions, so the import page is reachable by whoever can reach the catalogue, matching what FS-008 settled for creating, editing and deleting references. Import is the most consequential write the front end offers, so this is stated rather than assumed silently.
- The package imposes no size limit of its own on the submitted file. The import runs in the request, so what bounds a large file is the host project's upload and request limits, and the documentation says so rather than the package inventing a number.
- Background imports are a separate feature with their own specification. Nothing here is designed around a future move off the request, because the report is what a background import would have to reproduce and it is worth building once against the simple case first.
- Duplicate detection stays refused. ADR 0009 and ADR 0023 both settled it, and a front end that quietly acquired it would contradict the documented behaviour of the same import run started from code.
- Both catalogue presentations carry the action, following the boundary FS-010 drew when it gave search and filtering to the card list as well as the table.
- The formats offered are read from the installation's configuration, so this feature needs no change when a format is added or removed.

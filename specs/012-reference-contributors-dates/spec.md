# Feature Specification: Manage a Reference's Contributors, Dates and Identifiers

**Feature Branch**: `012-reference-contributors-dates`

**Created**: 2026-08-25

**Status**: Draft

**Serves**: G4 (a full front end as an opt-in app built on django-mvp) · G7 (validate known identifier types at the model layer) · Roadmap R6 · Issue #48

**Input**: The parts of a reference that are not plain fields need editing too, and each carries its own awkwardness. A contributor has a role and a position within that role. A date may be a year on its own, or a range. An identifier is typed and format-checked. Someone editing a reference should be able to add, reorder and remove all of these without meeting a raw form that assumes they already know the underlying structure, and an identifier that gets rejected should say what is wrong with it.

## Clarifications

### Session 2026-08-25 — intake

- Q: When someone adds a contributor, do they pick from the contributors the catalogue already holds, or does a fresh record get created every time? → A: The field completes from the stored names, and a new record is created every time regardless. Accepting a completion asserts how the name is spelled, never who the person is. A field that bound the reference to a stored record would put an identity judgement in front of someone who is reading a name off a PDF, at the one moment they are least equipped to make it, and they would take the first plausible match without knowing they had decided anything. Nothing in the record can tell two same-named people apart — CSL JSON carries no author identifier — so the interface must not act as though something can. This extends ADR-0009 and ADR-0017 from reading to entry rather than carving an exception out of them. Joining records that do name the same person is a feature in its own right, filed as #112.
- Q: Are these three edited as part of the reference form, or as their own actions on the reference's page? → A: As part of the form, so one save covers the whole reference and backing out discards the whole edit. Someone entering a book from the copy in front of them has the authors, the year and the ISBN to hand, and a form that takes the title but sends them back for the authors has split one act into two for no reason they can see. Established reference managers often divide a form like this across tabs, which may suit this one later; a single form is the straightforward starting point.
- Q: Does the person meet all six CSL date slots, or just the reference's date? → A: Just the reference's date. `issued` is presented plainly, and the other five slots are reachable rather than laid out — the shape FS-008 settled for the scalar fields. Which slots lead is decided by extending the package's existing item-type-to-field mapping to cover them, so a webpage offers `accessed` up front and a book does not. Six labelled boxes would be the model leaking onto the page, which is what this issue objects to.
- Q: How far does "an identifier that gets rejected should say what is wrong with it" go? → A: As far as there is something to say. ISBN and ISSN carry a check digit, so a value of the right shape with one character mistyped can be told apart from a value of the wrong shape, and that is the commonest real error — a transcription slip, and the case where being shown a well-formed example helps least. DOI, URL, PMID and PMCID carry no check digit and have nothing further to diagnose, so their messages stay as they are. Nothing about what is accepted or rejected changes.

### Session 2026-08-25 — clarification scan

Resolved from the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: A contributor record holds nine fields — family, given, two particles, suffix, literal, and three flags a citation processor reads. Which does a person meet? → A: Family and given plainly, with the particles, the suffix and the organizational form reachable rather than laid out, exactly as the scalar fields and the date slots are treated. The three flags — `comma_suffix`, `static_ordering`, `parse_names` — are signals to a downstream citation processor, and a person entering a reference has no basis on which to set them. They stay off the form and are preserved unchanged, the same treatment FS-008 gave `categories` and `custom`.
- Q: A stored date may hold a season, a circa flag, a literal date, or the unparsed material an import kept when it could not normalize one. What happens to those? → A: They are never silently dropped. A date the form saves preserves every part of it the form did not offer. Following FS-008's rule that a field already holding a value is always shown, a date already carrying a literal or unparsed content shows it, so an imported date that could not be read can be repaired rather than being invisible and unreachable.
- Q: Does reordering contributors require a change to the stored data model? → A: No. A contributor's position is numbered within its role, assigned when the link is first stored, and the interface sets it explicitly when the order changes. Nothing is added, widened or constrained, and no migration is introduced.
- Q: What happens when someone adds a second identifier of a type the reference already carries — a second ISBN? → A: It is refused, with a message saying the reference already holds an identifier of that type. One identifier per type per reference is a current design limit rather than an oversight, and widening it is a separate feature. The refusal names the limit rather than reporting a database error.
- Q: What happens when the same contributor name is entered twice in the same role on one reference? → A: It is stored. Each entry creates its own record, so nothing collides, and the interface does not decide that two identically-spelled contributors are one person — on entry any more than on a page. It is very likely a slip, but the same reasoning that governs the completion field governs this: the software does not conclude identity, and a duplicate is the recoverable direction.
- Q: If a save fails validation after contributors have been entered, is anything left behind in the catalogue? → A: No. Nothing is written until the whole edit succeeds. A rejected save leaves the store exactly as it was — no orphaned contributor records from an attempt that never completed — and returns the form with what was entered still in it.
- Q: Does removing a contributor from a reference delete the contributor? → A: No, for the same reason removing a reference does not. A contributor record is shared and role-neutral, so removing it from a reference removes that reference's claim on it and never the record. A contributor left credited on nothing keeps their own page, which then lists nothing.
- Q: Can contributors be reordered across roles — an editor moved above an author? → A: No. Positions are numbered independently within each role, so reordering acts inside one role and never disturbs another. There is no single combined list to reorder, and presenting one would imply an ordering the store does not hold.
- Q: Does this feature change what the identifier validators accept? → A: No. It changes only what a rejection says. A value accepted today is accepted afterwards and a value rejected today is rejected afterwards, with the ISBN and ISSN messages distinguishing two failures that currently share one message.

**Refined 2026-08-25 — the check-digit distinction covers ISBN alone.**

The intake session settled that ISBN and ISSN would both distinguish a mistyped character from a
wrong shape, on the understanding that both carry a check digit. They do, in the standards. The
package does not act on the ISSN one: `validate_issn` matches `^\d{4}-\d{3}[\dX]$` and stops, so
the check character is recognised as a character and never verified. An ISSN of the right shape
with a wrong check digit is accepted today.

Distinguishing that case therefore means computing the check digit, which turns values the
catalogue currently accepts into rejections — the one thing FR-029 and SC-005 forbid. The test
suite makes it concrete: `0000-000X` sits in the accepted list and is not a valid ISSN by the
standard's own arithmetic. Reordering the RIS importer's `SN` routing is a second consequence,
since it uses this validator as a shape discriminator.

So ISBN keeps the distinction and ISSN does not, and the gap it exposes is filed separately as
**#118** — verifying the ISSN check digit is a change to what the catalogue accepts and deserves
its own decision rather than arriving inside a feature about form messages.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Credit the people behind a reference (Priority: P1)

Someone entering a chapter by hand types its authors and its editors, in the order they appear on the title page. Someone repairing an imported reference finds its author list mangled — two authors merged into one, or the wrong person credited — and fixes it: correcting a name, adding the one that was missed, dropping the one that does not belong, and putting them back in the right order. As they type a name, the field offers names the catalogue already holds so they can accept the spelling rather than key it out again, and what gets stored is this reference's own record of that contributor either way.

**Why this priority**: A reference with no contributors is the most obviously incomplete thing the catalogue can hold, and today it is the only thing a person can create by hand. Author lists are also what imports most often get wrong, so this is the repair people reach for first. Delivered alone it turns a catalogue of titles into a catalogue of work by people.

**Independent Test**: On a reference in a project with the interface installed, add two authors and an editor, reorder the authors, remove one, save, and confirm the catalogue holds those contributors in that order with those roles, and that names credited on other references are untouched.

**Acceptance Scenarios**:

1. **Given** someone creating or correcting a reference, **When** the form is shown, **Then** the reference's contributors are on it, each with the role it holds, in the order it holds within that role.
2. **Given** a contributor being added, **When** a name is typed, **Then** names the catalogue already holds are offered as completions, and accepting one fills the text without linking the reference to that stored record.
3. **Given** an accepted completion, **When** the form is saved, **Then** a new contributor record is created carrying that text, and the record the completion came from is unchanged and still credited on everything it was credited on.
4. **Given** contributors in a role, **When** their order is changed and the form is saved, **Then** the reference holds them in the new order, and contributors in every other role are in the order they were.
5. **Given** a contributor on a reference, **When** it is removed and the form is saved, **Then** the reference no longer credits it, and the contributor record itself still exists.
6. **Given** a contributor whose name is an organization rather than a person, **When** it is entered, **Then** it can be recorded as a single unparsed name rather than being forced into family and given parts.
7. **Given** a contributor record carrying content the form does not offer, **When** the reference is saved, **Then** that content is unchanged.
8. **Given** a form submitted with contributors and a validation failure elsewhere on it, **When** the save is rejected, **Then** no contributor record has been created and the form is returned with what was entered still in it.

---

### User Story 2 - Give a reference its dates (Priority: P2)

Someone records when a reference came out. Often that is a year and nothing more, because a year is all a book gives them. Sometimes it is a year and a month, sometimes a full date, and sometimes a span — a conference that ran across three days, or a report covering a period. They put in what they have without being asked to say in advance how precise it is going to be, and without being asked which of CSL's six date slots a publication year belongs in. When a reference needs one of the other slots — the day a web page was read, the year an edition was first published — that is reachable.

**Why this priority**: A reference with no date is hard to cite and hard to find again, and a year is the single most common thing a person knows about a source. It is second because contributors are the more visible absence and the more common import failure, and because a date on a reference nobody is credited on is of limited use.

**Independent Test**: Put a year-only date on a reference through the interface, confirm it is stored as a year, then change it to a range and confirm both ends are stored. Reach a second date slot on the same reference and confirm both are held independently.

**Acceptance Scenarios**:

1. **Given** someone creating or correcting a reference, **When** the form is shown, **Then** the reference's own publication date is presented plainly, and the other date slots are reachable without leaving the form.
2. **Given** a date being entered, **When** only a year is given, **Then** it is stored as a year and the reference does not gain a month or a day it was never told.
3. **Given** a date being entered, **When** a year and month, or a full date, is given, **Then** it is stored at that precision.
4. **Given** a date that spans a period, **When** both ends are given, **Then** the reference holds the span, and each end keeps its own precision.
5. **Given** a date with an end but no beginning, **When** the form is saved, **Then** it is not stored and the form is returned saying a span needs a start.
6. **Given** a reference whose item type makes another slot the obvious one, **When** the form is shown, **Then** that slot is presented alongside the publication date rather than only being reachable.
7. **Given** a stored date holding content the form does not offer, **When** the reference is saved, **Then** that content is unchanged.
8. **Given** a stored date an import could not read, and which therefore holds only unparsed content, **When** the form is shown, **Then** that content is visible and can be replaced with a date the catalogue can read.
9. **Given** a date on a reference, **When** it is cleared and the form is saved, **Then** the reference no longer holds a date in that slot.

---

### User Story 3 - Give a reference its identifiers, and be told plainly when one is wrong (Priority: P3)

Someone adds the DOI from the article's first page, or the ISBN from the back of the book, choosing what kind of identifier it is and typing the value. When they mistype a character of an ISBN, they are told that the number does not check out and a character is likely wrong, rather than being shown a correct-looking example of the thing they thought they had just typed. When the identifier is a kind the package does not know, they can name it themselves and it is stored as given.

**Why this priority**: Identifiers are what make a reference resolvable, and a mistyped one is worse than an absent one because it looks right. It is third because a reference is usable without one, whereas a reference with no contributors or no date is barely a reference. The diagnosis work is what makes it worth its own slice rather than a field on someone else's form.

**Independent Test**: Add a DOI and an ISBN to a reference through the interface and confirm both are stored. Submit an ISBN with one digit altered and confirm the message says the check digit does not match rather than only showing an example. Submit an identifier of a type the package does not know and confirm it is stored unchecked.

**Acceptance Scenarios**:

1. **Given** someone creating or correcting a reference, **When** the form is shown, **Then** the reference's identifiers are on it, each with the kind of identifier it is.
2. **Given** an identifier being added, **When** the kind is chosen, **Then** the kinds the package knows are offered and another can be named.
3. **Given** an identifier of a known kind, **When** its value does not have that kind's shape, **Then** it is not stored and the form says what the shape should be.
4. **Given** an ISBN of the right shape whose check digit does not match, **When** the form is saved, **Then** it is not stored and the form says the check digit does not match, distinguishing this from a value of the wrong shape.
5. **Given** an identifier whose kind was named by the person rather than chosen, **When** the form is saved, **Then** it is stored exactly as given and no format check is applied to it.
6. **Given** a kind named by the person that matches a known kind in different casing, **When** the form is saved, **Then** it is treated as that known kind and checked accordingly.
7. **Given** a reference that already holds an identifier of some kind, **When** a second of the same kind is submitted, **Then** it is not stored and the form says the reference already holds one of that kind.
8. **Given** an identifier on a reference, **When** it is removed and the form is saved, **Then** the reference no longer holds it.
9. **Given** a value that is accepted by the catalogue today, **When** it is submitted after this feature, **Then** it is still accepted, and a value rejected today is still rejected.

---

### User Story 4 - The demo shows the flows, and a broken one is caught (Priority: P4)

Someone evaluating the package starts the demo with the documented command and can credit contributors, set dates and add identifiers on the references it serves, not merely see the ones the seed data gave them. The check that runs on every change walks those flows in the demo project, so one that has quietly stopped working is caught on the change that broke it rather than by the next person who tries it.

**Why this priority**: The demo is the package's executable documentation and its regression guard, and FS-007 settled that each feature extends both as part of its own delivery. It is last because it guards work the other three stories deliver.

**Independent Test**: Start the demo from a clean clone with the documented command, add a contributor, a date and an identifier to a reference through it, then run the guard and confirm it exercises those flows and fails when one is broken.

**Acceptance Scenarios**:

1. **Given** a demo started with the documented command, **When** an evaluator credits a contributor, sets a date and adds an identifier, **Then** each completes and the catalogue reflects it.
2. **Given** the check that runs on every change, **When** it runs against the demo, **Then** it walks each of those flows and asserts the catalogue changed as the flow claims.
3. **Given** one of those flows broken, **When** the check runs, **Then** it fails and names the flow.
4. **Given** the demo's documented path, **When** an evaluator follows it, **Then** no sign-in is asked for at any point.

---

### Edge Cases

- A completion is offered from a contributor record that is subsequently removed from every reference: the completion still offers the text, because the record survives its last credit.
- A contributor is entered with neither a family name nor an unparsed name: the form is returned saying the contributor needs a name, and nothing is stored.
- The same name is entered twice in the same role on one reference: stored as two records, per the clarification scan.
- A contributor is entered on a reference that is itself being created: the reference and its contributors are stored together, or neither is.
- A date is entered whose end falls before its beginning: the form is returned saying so, and nothing is stored.
- A date slot the item type does not lead with already holds a value: it is presented rather than merely reachable, per FS-008's rule that a populated field is always shown.
- An identifier value exceeds the stored length: the form is returned stating the limit rather than truncating.
- A reference is saved with no changes to its contributors, dates or identifiers: they are byte-identical afterwards, including the parts the form does not offer.
- Two people edit the same reference at once: out of scope, as it is for FS-008. The package assumes one person managing their own library.

## Requirements *(mandatory)*

### Functional Requirements

**Contributors**

- **FR-001**: The reference form MUST carry the reference's contributors, each showing its role and its position within that role.
- **FR-002**: A contributor MUST be addable to a reference in a chosen role.
- **FR-003**: A contributor MUST be removable from a reference, and removing it MUST NOT delete the contributor record, whether or not it is credited elsewhere.
- **FR-004**: Contributors MUST be reorderable within a role. Reordering one role MUST NOT change the order of any other role, and the interface MUST NOT offer an ordering across roles.
- **FR-005**: The contributor name field MUST offer completions drawn from the names the catalogue already holds.
- **FR-006**: Accepting a completion MUST NOT link the reference to the record the completion came from. Saving MUST create a new contributor record carrying the entered text, whether or not an identical one is already stored.
- **FR-007**: The interface MUST NOT warn about, refuse, or merge a contributor whose name matches one already stored, on entry or afterwards.
- **FR-008**: A contributor MUST be recordable as a single unparsed name, for organizations and names that do not divide.
- **FR-009**: A contributor form MUST present the family and given name parts directly, and MUST make the particles, the suffix and the unparsed form reachable without leaving the form.
- **FR-010**: A contributor form MUST NOT offer the citation-processor flags (`comma_suffix`, `static_ordering`, `parse_names`), and saving MUST preserve their stored values exactly.
- **FR-011**: A contributor MUST require a family name or an unparsed name. Submitting neither MUST NOT store anything, and MUST return the form saying so.

**Dates**

- **FR-012**: The reference form MUST present the reference's publication date directly, and MUST make the remaining date slots reachable without leaving the form.
- **FR-013**: Which date slots are presented directly MUST be decided by the package's item-type-to-field mapping, extended to cover date slots. As with the scalar fields, the mapping MUST NOT restrict what can be stored.
- **FR-014**: A date MUST be enterable as a year alone, a year and month, or a full date, without the person declaring the precision beforehand, and MUST be stored at the precision given.
- **FR-015**: A date MUST be enterable as a span by giving a second end, and each end MUST keep its own precision.
- **FR-016**: Submitting an end with no beginning, or an end that falls before its beginning, MUST NOT store anything and MUST return the form saying so.
- **FR-017**: Saving MUST preserve exactly the parts of a stored date the form does not offer.
- **FR-018**: A stored date holding content the form does not otherwise present MUST be shown, so an unreadable imported date can be repaired.
- **FR-019**: Clearing a date MUST remove the reference's date in that slot.
- **FR-020**: One date per slot per reference MUST be inherited unchanged. This feature MUST NOT widen it.

**Identifiers**

- **FR-021**: The reference form MUST carry the reference's identifiers, each showing its kind.
- **FR-022**: An identifier MUST be addable and removable on a reference.
- **FR-023**: The kinds the package knows MUST be offered, and a kind outside that set MUST be nameable by the person.
- **FR-024**: An identifier of a person-named kind MUST be stored exactly as given and MUST NOT be format-checked, per ADR-0002.
- **FR-025**: A person-named kind matching a known kind other than by casing MUST be treated as that known kind and checked accordingly.
- **FR-026**: A rejected identifier MUST be reported with a message describing what is wrong with the value submitted.
- **FR-027**: For ISBN, a value of the correct shape whose check digit does not match MUST be reported differently from a value of the wrong shape, and the message MUST say the check digit does not match.
- **FR-028**: For ISSN, DOI, URL, PMID and PMCID the existing messages MUST be unchanged. ISSN is excluded because the package does not verify its check digit at all, and adding that verification would reject values it accepts today — see the refinement note below. The other four carry no check digit and have nothing further to diagnose.
- **FR-029**: This feature MUST NOT change which identifier values are accepted or rejected. Only the wording of a rejection changes.
- **FR-030**: One identifier per kind per reference MUST be inherited unchanged. A second of the same kind MUST be refused with a message naming the limit, and the limit MUST NOT be widened here.

**The form as a whole**

- **FR-031**: Contributors, dates and identifiers MUST be edited as part of the reference form, saved with it in one act, and discarded with it when the edit is abandoned.
- **FR-032**: They MUST be editable both when a reference is being created and when one is being corrected.
- **FR-033**: A rejected save MUST leave the catalogue exactly as it was, creating no contributor, date or identifier record, and MUST return the form carrying what was entered.
- **FR-034**: A save that changes none of the three MUST leave all three exactly as they were, in value, role and order, including the parts the form does not offer.

**Scope and posture**

- **FR-035**: Every page this feature touches MUST remain reachable without authentication, and the feature MUST NOT impose a permission check of its own, per ADR-0022.
- **FR-036**: The core MUST NOT acquire any front-end dependency. Everything except the identifier message change lives in the opt-in front-end app.
- **FR-037**: The identifier message change MUST stay at the model layer where the existing validators live, so a caller that never installs the front end gets the same diagnosis.
- **FR-038**: This feature MUST NOT introduce custom UI components or custom CSS. Its forms compose django-mvp's existing set, and a gap in that set is raised upstream rather than filled locally, per FS-006.
- **FR-039**: This feature MUST NOT change the stored data model. No field is added, removed, widened or constrained, and no migration is introduced.
- **FR-040**: Joining contributor records that name the same person MUST NOT be delivered here. It belongs to #112.
- **FR-041**: Every user-facing string this feature introduces, in Python and in templates, MUST be translatable per Article VIII.

**Demo and guard**

- **FR-042**: The demo project MUST expose these flows over its seeded catalogue, reachable by following links from the pages it already serves.
- **FR-043**: The check that runs on every change MUST walk the contributor, date and identifier flows against the demo project and assert the catalogue changed as each claims.
- **FR-044**: The demo MUST continue to require no sign-in at any point on its documented path.

### Key Entities *(include if feature involves data)*

- **Name**: a contributor, shared across references and role-neutral. This feature creates one for every contributor entered, and never changes or removes one.
- **ItemName**: the link binding a contributor to a reference in a role, at a position within that role. This feature creates, reorders and removes these links.
- **ItemDate**: a structured date occupying one of the reference's six CSL date slots, at most one per slot, partial by nature. This feature creates, changes and removes them.
- **ItemIdentifier**: a typed value on a reference, at most one per kind. This feature creates, changes and removes them.
- **Item type**: which of CSL JSON's forty-five kinds a reference is. Extended here to decide which date slots are presented directly.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person with the interface installed can enter a complete reference — its record, its contributors, their roles and order, its date and its identifiers — in one form and one save, without running a shell, writing Python, or using a Django admin.
- **SC-002**: Entering a contributor whose name matches one already stored never changes what that stored record is credited on, demonstrated by crediting the same name across two references and confirming each holds its own record.
- **SC-003**: A year-only date entered through the interface exports to CSL JSON as a year alone, with no month or day the person did not supply.
- **SC-004**: An ISBN with one digit altered produces a message naming the check digit, distinguishable from the message a malformed ISBN produces.
- **SC-005**: The set of identifier values the catalogue accepts is unchanged by this feature, demonstrated by the existing validator tests passing untouched.
- **SC-006**: No stored value is lost by a round trip through the form: a reference saved with no changes is byte-identical afterwards, including its contributors' processor flags and the parts of its dates the form does not offer.
- **SC-007**: A reference completed through the interface exports to CSL JSON that round-trips back to the same reference, so a reference entered by hand is of the same quality as an imported one.
- **SC-008**: The check that runs on every change fails when any one of the three flows is broken, demonstrated by breaking each in turn.

## Assumptions

- **Duplicate contributor records accumulate, and that is the accepted cost.** Entry never reuses a stored record, so a person crediting the same collaborator across twenty references holds twenty records. This is already true of any imported library, so it is not a new condition, but it does mean the interface never offers a way down. Joining them is #112, where the evidence for a merge can be weighed and a person decides it — which is what ADR-0017 said should happen.
- **Completion is a spelling aid and nothing more.** It saves keystrokes. It buys nothing for integrity, because nothing in the model requires reuse, and it must never be mistaken for — or evolve into — a way of saying two references credit the same person.
- **The single form is the starting point, not a settled interaction.** Established reference managers commonly divide a form of this size across tabs. That may suit this one once it is in use; nothing here forecloses it.
- **The store's existing limits are inherited and not widened.** One identifier per kind, one date per slot, and the partial-date fallbacks apply as they do today. Widening either is a feature, not a fix.
- **Type scoping stays a presentation decision.** Extending the mapping to date slots decides which are offered first, never which can be stored — the same bound ADR-0021 already places on it for the scalar fields.
- **The identifier message change is diagnosis only, and covers ISBN.** Nothing about which values pass becomes looser or stricter. The existing validator tests are the guard on that, and they are expected to pass unchanged — which is exactly why ISSN is excluded, since verifying its check digit would move values out of the accepted set. That gap is #118.
- **The demo is extended, not replaced.** FS-007's seeded catalogue, documented command and guard stay as they are and gain these flows, and the guard remains an addition to the test suite rather than a substitute for part of it.

# Feature Specification: Add, Edit and Remove References Through the Front End

**Feature Branch**: `008-add-edit-remove-references`

**Created**: 2026-08-13

**Status**: Draft

**Serves**: G4 (a full front end as an opt-in app built on django-mvp) · Roadmap R6 · Issue #47

**Input**: Browsing is only half of what a reference catalogue is for. Someone using the interface should be able to enter a new reference, correct one that is wrong, and remove one that does not belong, without dropping into a shell or writing code against the models. This covers the reference itself. Its contributors, dates and identifiers are a separate piece of work.

## Clarifications

### Session 2026-08-13 — intake

- Q: The browse pages are open — no sign-in, no permission check, and the demo's guard actively asserts that no page redirects to a login. Writing is a different proposition, since the same posture means anyone who can reach the URL can delete a reference. Does this feature introduce access control? → A: No. The package is being developed on the assumption of a single person managing their own library, so the write pages are open exactly as the read pages are. Permissions arrive as the package matures, as their own piece of work.
- Q: An item carries around seventy scalar fields, and which of them mean anything depends on which of the forty-five item types was chosen — `page` and `volume` matter for a journal article and are noise on a dataset. Does someone adding a reference meet all seventy? → A: No. The item type is chosen first and the form is then scoped to the fields that apply to that type, with the remainder reachable rather than absent. A field already holding a value is always shown whatever the type, so an import can never hide data behind the type mapping.
- Q: The citation key is required, and nothing outside the RIS importer produces one. Does the person type it, and what happens when it collides with a key already stored? → A: The person types it, and a collision is not the software's problem. A citation key is a handle for writing bibliographies, and keeping keys distinct is the same kind of concern in every other reference manager: something the person creates deliberately and resolves themselves. Nothing here warns, refuses, or rewrites. The store's own de-duplication on the import path contradicts this and is tracked separately as issue #69; this feature does not depend on that being fixed first.

### Session 2026-08-13 — clarification scan

Resolved from the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: An item carries two JSON fields, `categories` and `custom`, which exist to round-trip data the conversion boundary owns. Do they appear on the form? → A: No, and editing a reference must leave them exactly as they were. They hold content whose shape the person editing has no way to reason about, and a text box containing raw JSON is a way to lose data rather than a way to edit it. Preserving them untouched is a requirement, not a side effect of leaving them off the form.
- Q: What happens when someone edits a reference and changes its item type, and fields already holding values no longer apply to the new type? → A: The values stay and remain visible. Type scoping decides what is offered on a blank form, never what is kept. A change of type that silently discarded stored bibliographic content would be exactly the failure Article XI exists to prevent, and the person is better placed than the software to decide whether a now-off-type value is wrong.
- Q: Is a reference valid with nothing but an item type and a citation key? → A: Yes. Contributors, dates and identifiers belong to #48, so a reference created here necessarily has none until that lands, and the catalogue and reference pages already render an item whose related collections are empty. Requiring more would make the feature undeliverable on its own.
- Q: Where does each flow start, and where does it end? → A: Adding starts from the catalogue page and ends on the new reference's own page. Correcting and removing start from the reference's page; correcting ends there too, and removing ends back at the catalogue.
- Q: Can several references be removed at once? → A: No. Removal acts on one reference, behind a confirmation that names it. Selecting many rows and acting on them together is a different interaction with a different failure mode, and no issue in R6 asks for it.
- Q: Removing a reference cascades to its contributor links, dates and identifiers. What happens to the contributor records themselves? → A: They survive. A `Name` is shared across items and role-neutral, so deleting the reference removes that item's claim on the contributor and never the contributor. A contributor left credited on nothing keeps their own page, which then lists nothing.
- Q: Where does the mapping from item type to applicable fields come from? → A: The package authors and owns it, because nothing publishes one. CSL 1.0.2 treats item type and variable set as orthogonal: `csl-data.json` declares all 103 properties flat with no conditional on `type`, so any variable validates on any type; the specification lists variables by data category rather than by type, and uses type only to drive conditionals inside citation styles; neither reference processor carries a table. The nearest published mapping is Zotero's schema, which is machine-readable and maintained but covers 32 of the 45 types, omits 29 CSL variables, reverses ambiguously in eleven places, and — decisively — carries no licence at all, so vendoring it would mean redistributing unlicensed material. What makes authoring our own defensible rather than reckless is that the mapping is presentation only: it decides which fields are offered first, never which can be stored, so a debatable entry is a form that asks in a slightly odd order rather than a reference that cannot be recorded. The specification's Appendix III carries advisory prose about types and variables that gives the editorial work a starting point.
- Q: Does this feature build any form widget or styling of its own? → A: No. FS-006 settled the standing rule that this app writes no custom components and no custom CSS and composes django-mvp's set only. A gap in that set is raised upstream rather than solved locally, and a local bridge, if one is unavoidable, is temporary and comes out when a django-mvp release carries the component.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enter a reference by hand (Priority: P1)

Someone has a reference that no file gave them — a report they were sent, a dataset they are citing, a chapter they read — and wants it in the catalogue. From the catalogue page they start a new reference, choose what kind of thing it is, and get a form carrying the fields that kind of thing actually has rather than every field the model can store. They fill in what they know, save, and land on the new reference's page with what they entered shown back to them. Nothing else in the catalogue changed.

**Why this priority**: It is the first thing the catalogue cannot do at all today. Every reference in a store now arrives through an import file or a shell session, so a person with a single reference in front of them has no way in. Delivered alone it makes the interface a place where a library can start rather than only be looked at.

**Independent Test**: Open the catalogue in a project with the interface installed, start a new reference, choose an item type, fill in a handful of fields, save, and confirm the reference exists in the store with those values and appears in the catalogue.

**Acceptance Scenarios**:

1. **Given** a reader on the catalogue page, **When** they start a new reference, **Then** they are asked what kind of reference it is before being asked for anything else.
2. **Given** a chosen item type, **When** the form is shown, **Then** the fields that apply to that type are presented directly and the remaining scalar fields are reachable without leaving the form.
3. **Given** a completed form with an item type and a citation key, **When** it is saved, **Then** a reference is stored with exactly the values entered and the reader arrives on its page.
4. **Given** a form submitted without an item type or without a citation key, **When** it is saved, **Then** the reference is not stored and the form is returned stating which field needs a value.
5. **Given** a citation key that another stored reference already uses, **When** the form is saved, **Then** the reference is stored with that key unchanged and nothing warns, refuses, or alters it.
6. **Given** a newly created reference, **When** its page is opened, **Then** it shows no contributors, dates or identifiers, and the page renders without error.

---

### User Story 2 - Correct a reference that is wrong (Priority: P2)

A reference in the catalogue has a typo in its title, a missing page range, or the wrong publisher — often because it came out of an imported file that way. From that reference's page the person opens it for correction, sees the current values in a form scoped the same way as when adding, changes what is wrong, and saves. They land back on the reference's page showing the corrected record. Anything they did not touch is exactly as it was, including the parts of the record this feature does not put on the form.

**Why this priority**: Imported references are wrong often enough that a catalogue with no correction path pushes people back to the shell for a one-character fix. It builds on the same form as US1 but is a separate slice: a catalogue populated entirely by import needs correction before it needs manual entry.

**Independent Test**: Take a stored reference, open its correction form, confirm it shows the stored values, change one field, save, and confirm the store holds the change and nothing else about the reference moved.

**Acceptance Scenarios**:

1. **Given** a reader on a reference's page, **When** they open it for correction, **Then** the form is shown carrying that reference's current values.
2. **Given** a reference whose stored values include fields that do not apply to its item type, **When** the form is shown, **Then** those fields are visible and carry their values.
3. **Given** a changed field, **When** the form is saved, **Then** the reference holds the new value, every other field is unchanged, and the reader arrives back on its page.
4. **Given** a reference carrying content in the fields this feature does not put on the form, **When** it is saved through the form, **Then** that content is unchanged.
5. **Given** a reference with contributors, dates and identifiers, **When** it is corrected and saved, **Then** those related records are unchanged in value, role and order.
6. **Given** a correction that changes the item type, **When** it is saved, **Then** values already held by fields that do not apply to the new type are retained.

---

### User Story 3 - Remove a reference that does not belong (Priority: P3)

A reference is in the catalogue that should not be — a duplicate from importing the same file twice, or something imported by mistake. From that reference's page the person removes it, is asked to confirm against a page that names the reference so there is no doubt which one is going, and confirms. The reference and the parts of the record that belong only to it go with it. The people credited on it stay in the catalogue, because they are shared with everything else they worked on. The person lands back on the catalogue, which no longer lists it.

**Why this priority**: Importing the same file twice creates duplicates by design, so a catalogue that can be added to and corrected but never pruned only accumulates. It is last of the three because a wrong reference that stays is a smaller problem than one that cannot be entered or fixed.

**Independent Test**: Remove a stored reference through the interface and confirm it and its own related records are gone, the contributors it credited still exist, and the catalogue no longer lists it.

**Acceptance Scenarios**:

1. **Given** a reader on a reference's page, **When** they choose to remove it, **Then** they are asked to confirm on a page that names the reference, and nothing has yet been removed.
2. **Given** the confirmation page, **When** the reader declines, **Then** the reference is untouched and they are returned to it.
3. **Given** the confirmation page, **When** the reader confirms, **Then** the reference and its contributor links, dates and identifiers are removed and the reader arrives at the catalogue.
4. **Given** a removed reference whose contributors are credited on other references, **When** the removal completes, **Then** those contributors still exist and their own pages list the references that remain.
5. **Given** a removed reference whose contributor is credited on nothing else, **When** the removal completes, **Then** that contributor still exists and their page renders while listing nothing.
6. **Given** a removal of the only reference in the catalogue, **When** it completes, **Then** the catalogue renders and states that there is nothing stored.

---

### User Story 4 - The demo shows the flows, and a broken one is caught (Priority: P4)

Someone evaluating the package starts the demo with the documented command and can add, correct and remove a reference in the catalogue it serves, not merely browse it. The check that runs on every change walks these flows in the demo project as well as the pages that already exist, so a flow that has quietly stopped working is caught on the change that broke it rather than by the next person who tries it.

**Why this priority**: The demo is the package's executable documentation and its regression guard, and FS-007 settled that each feature extends both as part of its own delivery. It is last because it guards work the other three stories deliver.

**Independent Test**: Start the demo from a clean clone with the documented command, add a reference through it, correct it, remove it, then run the guard and confirm it exercises those flows and fails when one is broken.

**Acceptance Scenarios**:

1. **Given** a demo started with the documented command, **When** an evaluator adds, corrects and removes a reference through its pages, **Then** each flow completes and the catalogue reflects it.
2. **Given** the check that runs on every change, **When** it runs against the demo, **Then** it walks the add, correct and remove flows and asserts the catalogue changed as each one claims.
3. **Given** one of those flows broken, **When** the check runs, **Then** it fails and names the flow.
4. **Given** the demo's documented path, **When** an evaluator follows it, **Then** no sign-in is asked for at any point.

---

### Edge Cases

- A reference is requested for correction or removal by an identifier that matches nothing stored: the interface answers not found rather than erring.
- A citation key is submitted that duplicates one already stored: stored as given, silently, per the intake session.
- An item type is changed on correction such that populated fields no longer apply: those values are retained and stay visible, per the clarification scan.
- A form is submitted with every optional field blank: stored, since an item type and a citation key are the only values a reference requires.
- The catalogue is emptied by removing its last reference: the catalogue page renders its empty state.
- A contributor is left credited on nothing after a removal: the contributor record and its page survive.
- A value is entered that exceeds a field's stored length: the form is returned stating the limit rather than truncating.
- Two people correct the same reference at once: out of scope. The package assumes one person managing their own library, and nothing here detects a concurrent edit.

## Requirements *(mandatory)*

### Functional Requirements

**Creating**

- **FR-001**: The interface MUST offer a way to create a reference, reachable from the catalogue page.
- **FR-002**: Creating a reference MUST ask for the item type before asking for the rest of the record.
- **FR-003**: Once an item type is chosen, the form MUST present the scalar fields that apply to that type, and MUST make the remaining scalar fields reachable without leaving the form.
- **FR-004**: The mapping from item type to its applicable fields MUST be carried in the package as a single readable artefact, MUST cover all forty-five item types, and MUST state what each type's set was decided from. It MUST NOT be derived from a source the package cannot lawfully redistribute.
- **FR-004a**: The mapping MUST NOT restrict what can be stored. Every scalar field stays reachable and storable on every item type, whatever the mapping says.
- **FR-005**: A reference MUST be creatable with nothing beyond an item type and a citation key.
- **FR-006**: Submitting without an item type or without a citation key MUST NOT create a reference, and MUST return the form stating which field needs a value.
- **FR-007**: A citation key matching one already stored MUST be accepted and stored unchanged. The interface MUST NOT warn about, refuse, or alter it.
- **FR-008**: On successful creation the reader MUST arrive at the new reference's own page.

**Correcting**

- **FR-009**: The interface MUST offer a way to correct a stored reference, reachable from that reference's page.
- **FR-010**: The correction form MUST be scoped by item type exactly as the creation form is, and MUST additionally show every field the reference already holds a value in, whatever its item type.
- **FR-011**: Saving a correction MUST change only the fields submitted, and MUST leave every other stored value on the reference unchanged.
- **FR-012**: Saving a correction MUST leave the reference's contributors, dates and identifiers unchanged in value, role and order.
- **FR-013**: Saving a correction MUST preserve the reference's `categories` and `custom` content exactly, and neither MUST appear on the form.
- **FR-014**: Changing a reference's item type MUST retain values already held by fields that do not apply to the new type.
- **FR-015**: On successful correction the reader MUST arrive back at the reference's own page.

**Removing**

- **FR-016**: The interface MUST offer a way to remove a stored reference, reachable from that reference's page.
- **FR-017**: Removal MUST be confirmed on a page that names the reference being removed, and MUST remove nothing before that confirmation.
- **FR-018**: Declining the confirmation MUST leave the reference untouched and return the reader to it.
- **FR-019**: Confirming MUST remove the reference together with its contributor links, its dates and its identifiers.
- **FR-020**: Removal MUST NOT delete any contributor record, whether or not that contributor is credited on anything else.
- **FR-021**: On successful removal the reader MUST arrive at the catalogue.
- **FR-022**: Removal MUST act on exactly one reference per confirmation. The interface MUST NOT offer removal of several references at once.

**Scope and posture**

- **FR-023**: This feature MUST cover only the reference's own scalar record. Creating, changing, ordering or removing contributors, dates and identifiers belongs to #48 and MUST NOT be delivered here.
- **FR-024**: Every page this feature adds MUST be reachable without authentication, and the feature MUST NOT impose a permission check of its own. Restricting access stays the host's to do, as it is for the existing pages.
- **FR-025**: The core MUST NOT acquire any front-end dependency. Everything here lives in the opt-in front-end app.
- **FR-026**: This feature MUST NOT introduce custom UI components or custom CSS. Its forms and pages compose django-mvp's existing set, and a gap in that set is raised upstream rather than filled locally.
- **FR-027**: This feature MUST NOT change the stored data model. No field is added, removed, widened or constrained, and no migration is introduced.
- **FR-028**: Text search, filtering, choice of ordering, and importing a file through the interface MUST NOT be delivered here. They belong to #49 and #50.
- **FR-029**: No admin-based management ships with the package, and this feature MUST NOT add any.
- **FR-030**: Every user-facing string this feature introduces, in Python and in templates, MUST be translatable per Article VIII.

**Demo and guard**

- **FR-031**: The demo project MUST expose the create, correct and remove flows over its seeded catalogue, reachable by following links from the pages it already serves.
- **FR-032**: The check that runs on every change MUST walk each of the three flows against the demo project and assert the catalogue changed as the flow claims.
- **FR-033**: The demo MUST continue to require no sign-in at any point on its documented path.

### Key Entities *(include if feature involves data)*

- **Item**: the reference itself. This feature creates, changes and removes it, and touches only its own scalar fields.
- **ItemName**, **ItemDate**, **ItemIdentifier**: the reference's related records. This feature never creates or changes them; removing a reference removes them with it.
- **Name**: a contributor, shared across references and role-neutral. This feature never creates, changes or removes one.
- **Item type**: which of CSL JSON's forty-five kinds a reference is. It selects the fields the form offers and can be changed on correction.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person with the interface installed can put a reference into the catalogue, correct it, and remove it again without running a shell, writing Python, or using a Django admin.
- **SC-002**: Adding a journal article presents materially fewer fields than the item model stores, so the form asks about what a journal article has rather than everything a reference could be.
- **SC-003**: No stored value is lost by a round trip through the correction form: a reference saved with no changes is byte-identical afterwards, including the fields the form does not show.
- **SC-004**: Removing a reference leaves every contributor it credited still present in the catalogue.
- **SC-005**: The check that runs on every change fails when any one of the three flows is broken, demonstrated by breaking each in turn.
- **SC-006**: A reference created through the interface exports to CSL JSON that round-trips back to the same reference, so manual entry and import produce records of the same quality.

## Assumptions

- **The write pages are open, and that is a decision rather than an oversight.** The package is developed for a single person managing their own library. Anyone who can reach a URL can add, correct and remove references, and the demo ships that way. Access control for the front end has no issue and no roadmap item, and wants one before the package is used by more than one person against the same store.
- **Contributors, dates and identifiers are absent from a reference created here.** They are #48's, so between this feature and that one the interface can create a reference nobody is credited on. The existing pages already render such a reference.
- **Citation-key uniqueness is nobody's problem.** Nothing here checks, warns or rewrites. The import path currently does de-duplicate against the whole store, which contradicts this posture; that is issue #69 and is not a dependency of this work.
- **The store's existing limits are inherited and not widened.** One identifier per type per item, one date per slot, and partial-date fallbacks apply as they do today.
- **Type scoping is a presentation decision, never a storage one.** No stored value is ever discarded because the item type says it does not apply.
- **The type-to-field mapping becomes something the package maintains.** Nothing publishes one that can be used, so this feature authors it and it joins the package's public surface: people will disagree with individual entries and file issues about them. That is the accepted cost of asking a person about the fields their reference actually has, and it is bounded by the mapping having no say over what can be stored.
- **The demo is extended, not replaced.** FS-007's seeded catalogue, documented command and guard stay as they are and gain these flows, and the guard remains an addition to the test suite rather than a substitute for part of it.
- **No new runtime dependency is expected.** The form stack the interface already relies on ships with django-mvp, which the front end already requires.

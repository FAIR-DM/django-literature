# Feature Specification: A Reference Picker for a Project's Own Forms

**Feature Branch**: `013-reference-picker`

**Created**: 2026-10-26

**Status**: Draft

**Serves**: G4 (a full front end as an opt-in app built on django-mvp) · G3 (run as a headless core with no UI required) · Issue #160

**Input**: Projects that link their own models to `Item` need a way to choose a reference in a form: a dataset's data publication, the paper a review is about. A plain choice field renders every reference in one list, which does not work for a catalogue of any size, so each project builds its own search endpoint and widget. A developer should be able to add a searchable reference picker to their own form with one field declaration.

## Clarifications

### Session 2026-10-26 — intake

- Q: Who is this for, and what do they do? → A: A developer whose own model points at `Item` declares one field on their form. The people using that form type part of a title, a contributor's name, a citation key or a DOI, and choose from the references that match, instead of scrolling a list of the whole catalogue. A form editing an existing record opens with its current choice already in the picker.
- Q: Can the picker choose several references? → A: Yes. There is a single-choice field and a multiple-choice field, so a many-to-many link to `Item` is served as well as a foreign key.
- Q: Can the picker create a reference that is not in the catalogue yet? → A: No. It chooses from what exists. Creating a reference from inside another model's form puts a reference's whole entry form inside someone else's, which is a different feature.
- Q: What does a search match? → A: The title, the citation key, a contributor's family name or organisational (literal) name, and the DOI.
- Q: How does each option identify its reference? → A: By its title, its year and its first contributor, enough to tell two similar titles apart.
- Q: Who may search? → A: Whoever may read the catalogue list, which today is anyone. ADR 0036 left reading open and put only writing behind permissions, and a search returns nothing the list does not already show.
- Q: What does a developer have to wire up? → A: Nothing beyond what mounting the catalogue already does. The search is part of the catalogue's routes, so a project that has mounted the catalogue has the search.
- Q: Can a developer restrict which references a picker offers? → A: Yes, with the filter and exclude conditions django-tomselect fields already take, for example "only references whose type is book". The same conditions decide what a submitted form accepts.

### Session 2026-10-26 — clarification scan

Resolved from the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: The search route answers anyone. Can a restricted picker be used to read references outside its restriction, by calling the search directly? → A: Every reference is already readable on the open catalogue list, so a direct call can reveal nothing new. What must hold is the narrower guarantee: a picker never offers, and its form never accepts, a reference outside its restriction, whatever is submitted.
- Q: How many matches does one search return? → A: A bounded number, with the most relevant first: a reference whose title or citation key starts with what was typed comes before one that merely contains it. Someone who does not see what they want types more. A search that returned the whole catalogue for one letter would recreate the problem this feature removes.
- Q: When does searching begin? → A: As soon as the picker is opened: an empty box offers the first page of the catalogue by title, and typing narrows it from the first character.
- Q: Someone pastes a DOI with its resolver in front of it (`https://doi.org/10.…`). Does it match? → A: Yes. A DOI is matched in the form the package stores it, so the same reference is found whether the resolver, the `doi:` prefix or neither is pasted, and whatever the letter case.
- Q: A reference chosen in the picker is deleted before the form is submitted. What happens? → A: The form reports that the chosen reference no longer exists, as any choice field does for a value that has gone, and nothing is saved.
- Q: Is the picker required? → A: It follows the form field's own `required`, as any field does. On a model form it follows the model field, so an optional link gives an optional picker that can be cleared.
- Q: The same picker appears on every row of an inline formset. Does each row work on its own? → A: Yes. Each row searches and chooses independently, including rows added on the page after it loaded.
- Q: The project mounts the catalogue under a prefix of its own choosing. Does the picker still find its search? → A: Yes. The picker locates the search by its route name, never by a fixed path.
- Q: Does a models-only install gain anything it must now configure or install? → A: No. The picker lives in the opt-in front end, and a project using only the models is untouched.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A developer adds a picker for one reference to their own form (Priority: P1)

A developer whose model has a foreign key to `Item`, such as a review naming the paper it assesses, declares the reference picker as that field on their form. The people filling the form in type a few letters of the title, an author's surname or a DOI, see the matching references identified well enough to tell similar ones apart, and choose one. Opening the form to edit an existing review shows the paper already chosen.

**Why this priority**: A single link to a reference is the commonest case and the one every project currently builds by hand. Delivered alone, it removes that work.

**Independent Test**: In a project with the catalogue mounted, declare the picker on a form for a model with a foreign key to `Item`, then search by title, by contributor, by citation key and by DOI, choose a reference, save, and reopen the form to edit.

**Acceptance Scenarios**:

1. **Given** a form with the reference picker and a catalogue of references, **When** the person types part of a reference's title, **Then** that reference is offered and can be chosen.
2. **Given** the same form, **When** the person types a contributor's family name, a citation key, or a DOI with or without its resolver, **Then** the references matching it are offered.
3. **Given** two references with the same title in different years, **When** both are offered, **Then** each option identifies its reference by title, year and first contributor.
4. **Given** a reference chosen and the form saved, **When** the record is opened for editing, **Then** the picker shows that reference already chosen.
5. **Given** a search that matches more references than one search returns, **When** the results are offered, **Then** they are bounded in number and those whose title or citation key starts with what was typed come first.
6. **Given** a chosen reference deleted before the form is submitted, **When** the form is submitted, **Then** it reports the choice as no longer available and nothing is saved.
7. **Given** the catalogue mounted under a prefix of the project's choosing, **When** the person searches, **Then** the search works.
8. **Given** the picker on every row of an inline formset, including a row added after the page loaded, **When** the person searches and chooses on each row, **Then** each row holds its own choice.
9. **Given** a visitor who is not signed in, **When** a form with the picker searches, **Then** the search answers, as the catalogue list does.

---

### User Story 2 - A developer adds a picker for several references (Priority: P2)

A developer whose model has a many-to-many link to `Item`, such as a dataset's related publications, declares the multiple-choice reference picker on that field. The person filling the form in searches and adds references one after another, sees the ones already chosen, and removes one they added by mistake.

**Why this priority**: Many-to-many links to references are common, but less so than a single link, and they build on everything the first story delivers.

**Independent Test**: Declare the multiple-choice picker on a form for a model with a many-to-many link to `Item`, choose three references, save, reopen, remove one, and save again.

**Acceptance Scenarios**:

1. **Given** a form with the multiple-choice picker, **When** the person searches and chooses three references, **Then** all three are saved on the link.
2. **Given** a saved record with references chosen, **When** it is opened for editing, **Then** every chosen reference is shown.
3. **Given** a reference already chosen, **When** the person searches again, **Then** choosing it again does not add it twice.
4. **Given** chosen references, **When** the person removes one and saves, **Then** only the remaining ones are linked.

---

### User Story 3 - A developer restricts which references a picker offers (Priority: P3)

A developer wants a picker that offers only some of the catalogue, such as only journal articles. They give the picker a filter or exclude condition, the way any django-tomselect field is restricted. People using the form are never offered anything outside that set, and a submitted form never accepts anything outside it.

**Why this priority**: Most pickers offer the whole catalogue. Restricting one is a refinement that matters to some projects and builds on the first two stories.

**Independent Test**: Declare a picker restricted to one item type, search for a title that exists both inside and outside the restriction, and confirm only the inside one is offered. Then submit the form with a reference outside the restriction and confirm it is refused.

**Acceptance Scenarios**:

1. **Given** a picker restricted to journal articles, **When** the person searches for a title shared by an article and a book, **Then** only the article is offered.
2. **Given** a picker restricted to a set of references, **When** a form is submitted naming a reference outside the set, **Then** the form refuses the choice as invalid and nothing is saved.
3. **Given** two pickers with different restrictions on the same page, **When** each is searched, **Then** each offers only its own set.

---

### Edge Cases

- A search for text that matches nothing returns an empty result, never an error.
- A search containing characters with meaning to a database query (`%`, `_`, quotes) matches them literally.
- A reference with no year, or no contributors, is still offered and still identifiable by its title. A reference with no title is identified by its citation key.
- A reference whose first contributor is an organisation is identified by the organisation's name.
- A record whose link points at a reference outside the picker's restriction opens for editing showing that reference, and saving it unchanged is refused, as any choice field refuses a value outside its choices.
- A form submitted without the browser running its scripts still carries the chosen reference and is validated in the same way.
- A project that uses only the models and never installs the front end is unaffected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The front end MUST provide a form field for choosing one reference, usable on any Django form, including a model form for a foreign key or one-to-one field to `Item`. *(US1)*
- **FR-002**: The front end MUST provide a form field for choosing any number of references, usable for a many-to-many field to `Item`. *(US2)*
- **FR-003**: Each field MUST offer references by searching as the person types, rather than listing the catalogue in full. *(US1, US2)*
- **FR-004**: A search MUST match references by title, citation key, a contributor's family name or literal name, and DOI. *(US1)*
- **FR-005**: A DOI search MUST match the stored DOI whether or not the text typed carries a resolver or `doi:` prefix, and regardless of letter case. *(US1)*
- **FR-006**: Each offered reference MUST be identified by its title, its year and its first contributor, falling back to the citation key when it has no title and omitting what it lacks. *(US1)*
- **FR-007**: A search MUST return a bounded number of references, placing those whose title or citation key starts with the text typed before those that only contain it. *(US1)*
- **FR-008**: A form opened on an existing record MUST show the reference or references already chosen. *(US1, US2)*
- **FR-009**: The search MUST be part of the catalogue's routes, available wherever the catalogue is mounted and under whatever prefix, and the fields MUST locate it by route name. *(US1)*
- **FR-010**: The search MUST be readable by anyone who may read the catalogue list, under the same rule. *(US1)*
- **FR-011**: The fields MUST work on every row of an inline formset, including rows added after the page loaded. *(US1)*
- **FR-012**: A developer MUST be able to restrict the references a field offers with django-tomselect's filter and exclude conditions. *(US3)*
- **FR-013**: A restricted field MUST offer only references inside its restriction, and its form MUST refuse a submitted reference outside it. *(US3)*
- **FR-014**: The multiple-choice field MUST NOT link the same reference twice, and MUST let a chosen reference be removed. *(US2)*
- **FR-015**: The field's `required` MUST behave as for any Django form field. On a model form it follows the model field, and an optional field can be cleared. *(US1)*
- **FR-016**: Both fields and the search MUST live in the opt-in front end, adding nothing a models-only install must configure or install. *(US1)*
- **FR-017**: The package documentation MUST describe how to declare each field, how to restrict it, and what the search matches. *(US1, US2, US3)*

### Key Entities

- **Item**: the reference being chosen. Unchanged.
- **Reference picker**: the pair of form fields, one choice and many, together with the search they draw on. It stores nothing of its own.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer adds a working, searchable reference picker to a form for their own model by declaring one field, writing no view, URL or JavaScript of their own.
- **SC-002**: A person finds a stored reference by any one of its title, citation key, a contributor's family name, or its DOI pasted with its resolver.
- **SC-003**: Each search returns at most the bounded number of references however large the catalogue is, demonstrated with a catalogue larger than the bound.
- **SC-004**: A form never saves a reference outside its picker's restriction, demonstrated by submitting one directly.
- **SC-005**: A project using only the models runs unchanged after upgrading, demonstrated by the existing models-only tests passing untouched.

## Assumptions

- **The picker chooses and never creates.** Creating a reference from another model's form is out of scope.
- **Reading stays open.** The search answers anyone, because ADR 0036 left reading open and the catalogue list already shows every reference to anyone. If reading is later put behind a permission, the search follows it under FR-010 without a change of its own.
- **Showing a chosen reference on a page is #161,** a separate component. This feature ends at the form.
- **References only.** Choosing a contributor record is not offered, and should not follow from this: FS-012 decided against selecting stored contributors because selection asserts who a person is (FS-012 `decisions.md`, D1). A reference has no such problem, since choosing one asserts nothing beyond which reference is meant.
- **The catalogue's own search page (FS-010) is unchanged.** The picker's search is its own route with its own bounded result, not a reuse of the list page.
- **Not in this feature, by decision on 2026-10-26:** offering the catalogue's add page when a search finds nothing, and a demo form using the picker. Both were specified and taken out at review. See `decisions.md`, D4.

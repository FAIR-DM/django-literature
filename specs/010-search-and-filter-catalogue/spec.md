# Feature Specification: Find a Reference in a Large Catalogue

**Feature Branch**: `010-search-and-filter-catalogue`

**Created**: 2026-08-20

**Status**: Draft

**Serves**: G4 (a full front end as an opt-in app built on django-mvp) · Roadmap R6 · Issue #49

**Input**: A researcher's library runs to thousands of references, and a plain list stops being usable well before that. Someone should be able to narrow the catalogue down by searching its text and filtering on the things references actually get grouped by, then move through the results in a predictable order.

## Clarifications

### Session 2026-08-20 — intake

- Q: FS-009 already gave the table bidirectional sorting from its column headings, so the issue's third clause — moving through results in a predictable order — looks served. Does this feature add an ordering surface, or does ordering enter only as the requirement that a sort survives a search and a filter? → A: The latter. No new ordering controls and no relevance ranking. Sorting stays the column headings, and this feature must compose with it.
- Q: An item carries around sixty scalar fields, so "searching its text" needs a defined set. Does the search reach the abstract and the keywords, or stay on the fields that identify a reference? → A: Stay on identity. Citation key, the three title fields the row already falls back through, container title, and contributor names. Abstract and keyword text are excluded: a search over long text is a different capability with different infrastructure behind it, and including it would trade a fast, predictable lookup for a slow scan.
- Q: The issue names item type, contributor and year. Contributor is awkward — thousands of references carry thousands of contributors, and there is already a contributor page answering "everything this person is credited on". Is that the filter set? → A: Add language. Contributor stays, because the contributor page answers only its one question and cannot be combined with "articles from 2019". The set is not meant to be exhaustive and is expected to grow as needs appear.
- Q: There are two public list views — the table the package now serves by default, and the card list a project can route to instead. Which one gets search and filtering? → A: Both, from one shared definition of what is searchable and filterable, each rendering the controls in its own idiom. A project that prefers cards must not silently lose the ability to find things.
- Q: Issue #88 records that a chosen sort is discarded on a page change, because pagination links replace the whole query string. The upstream fix has now shipped. Does this feature absorb #88, or does it stay a separate issue? → A: Absorb it. This feature has to raise the same dependency floor regardless, because filtering discarded on page two is the defect the feature exists to remove.
- Q: Are the fields the search reaches indexed? → A: Not today, and the feature is expected to index them.

### Session 2026-08-20 — clarification scan

Resolved from the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: Sam's requirement is that the searched fields be indexed. A single-column index does not serve a substring match — a query looking for a fragment anywhere inside a value cannot use an ordinary index on most databases, so adding one would cost write time and a migration and change no query. What does "indexed" have to mean here? → A: It means an index the search demonstrably uses, proven by measurement rather than asserted by its presence. The feature adds indexing that its own queries can use, and adds none that they cannot. Where the search cannot be served by an index on a given database, the specification says so rather than shipping a decorative one. This is the one place the feature may need a database-specific decision, and it is called out at the specification gate rather than settled quietly.
- Q: Does the search match whole words or fragments, and does case matter? → A: Case-insensitive fragments. Someone hunting a half-remembered reference types part of a title or a surname, not its exact form, and a whole-word match would fail on the hyphenated and possessive forms bibliographic titles are full of.
- Q: Contributor names are stored across several parts — family, given, particles, suffix, and a literal for organizations. Which does a search or a contributor filter match? → A: Family name, given name, and the literal that holds organizational and unparsed names. Particles and suffixes are matched only as part of those where they are stored inline. Omitting the literal would make every organization in the catalogue unfindable by name.
- Q: An item can carry six date slots, and its dates are partial. What does the year filter mean? → A: The year of the `issued` slot, which is the date the table already shows and the one a reference is commonly cited by. A year-only date qualifies, as does the year a range begins in. A reference carrying no issued date is not returned when a year is chosen.
- Q: `language` is a free-text field with no fixed vocabulary, so its values are whatever the imported data carries. What does the filter offer? → A: The distinct values present in the catalogue, shown as stored. Inventing a display vocabulary would mean mapping arbitrary strings onto a list this package does not own, and a value that appears in no reference is not worth offering.
- Q: How do several filters, and several values within one filter, combine? → A: Choosing more than one value within a filter widens the result to any of them; filters combine with each other and with the search to narrow it. That is what a reader means by "articles or chapters, from 2019".
- Q: What does the reader see when a search or a filter returns nothing? → A: A message saying nothing matched, distinct from the message shown when the catalogue itself is empty, with the search and filter controls still present so the reader can change them. Emptying the page of its own controls strands the reader on a dead end.
- Q: What happens to a filter value in the address bar that no longer exists in the catalogue, or was never valid? → A: It narrows to nothing and says so. It never raises an error, and it never falls back to the unfiltered catalogue, which would show a reader a full page they did not ask for and let them believe it was the result.
- Q: The contributor page is the third place in the front end that lists items. Does it get search and filtering? → A: No. It stays as it is, which is the same boundary FS-009 drew when it left that page on cards.
- Q: Does the feature change any model, add a field, or ship a migration? → A: No model change and no new field. It may ship a migration that adds indexing and nothing else.
- Q: The demo's guard pins a pagination link's exact address, and the upstream fix changes that address. What happens to it? → A: The guard's expectation moves with the fix, and the guard grows to walk a search and a filter, so that a page move that loses them fails the build.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find a reference by what you remember of it (Priority: P1)

Someone with a few thousand references types part of a surname, a word from a title, or a citation key into a search box above the catalogue, and the page narrows to the references that match. They do not have to know which field their fragment lives in, or spell it exactly as it was stored. The page tells them how many references matched, and clearing the box returns the whole catalogue.

**Why this priority**: It is the fastest route from a large catalogue to one reference, and it is the half of this feature a reader reaches for first. Delivered alone it already makes a library of thousands usable.

**Independent Test**: Install the front end over a catalogue holding several hundred references, type a fragment of a known title into the search box, and confirm the page narrows to the references carrying it, that the same fragment finds a reference by its contributor's surname and by its citation key, and that clearing the box restores the full catalogue.

**Acceptance Scenarios**:

1. **Given** a catalogue of references, **When** the catalogue page is opened, **Then** a search box is present above the results.
2. **Given** a reference whose title contains a fragment, **When** that fragment is searched, **Then** the reference is among the results.
3. **Given** a reference carrying no main title but a short title or an original title containing a fragment, **When** that fragment is searched, **Then** the reference is among the results.
4. **Given** a reference whose container title contains a fragment, **When** that fragment is searched, **Then** the reference is among the results.
5. **Given** a reference whose citation key contains a fragment, **When** that fragment is searched, **Then** the reference is among the results.
6. **Given** a reference credited to a contributor whose family name contains a fragment, **When** that fragment is searched, **Then** the reference is among the results.
7. **Given** a reference credited to an organization stored as a literal name containing a fragment, **When** that fragment is searched, **Then** the reference is among the results.
8. **Given** a fragment typed in a different case from the stored value, **When** it is searched, **Then** the reference is still among the results.
9. **Given** a reference whose abstract or keywords contain a fragment found nowhere else on it, **When** that fragment is searched, **Then** the reference is **not** among the results.
10. **Given** a search matching several references, **When** the results are shown, **Then** the page states how many references matched.
11. **Given** a search matching nothing, **When** the results are shown, **Then** the page says nothing matched, keeps the search box and the filters on the page, and does not show the empty-catalogue message.
12. **Given** a search in force, **When** the search box is cleared, **Then** the whole catalogue returns.
13. **Given** a catalogue of several thousand references, **When** a search is run, **Then** the number of database queries does not grow with the number of results on the page.

---

### User Story 2 - Narrow the catalogue to a part of it (Priority: P2)

Someone wants the chapters, or everything from 2019, or everything by one contributor, or everything in German. Filters beside the catalogue offer item type, contributor, issued year and language, they combine with each other and with the search, and what is in force is visible on the page rather than only in the address bar.

**Why this priority**: It answers the questions a search cannot — a reader who wants a group rather than a reference has nothing to type. It sits below search because a reader who knows what they are looking for is served by the box alone.

**Independent Test**: Over a catalogue spanning several item types, years and languages, apply each filter on its own and confirm the results, then combine two of them and a search term and confirm the result is narrowed by all three.

**Acceptance Scenarios**:

1. **Given** a catalogue page, **When** it is opened, **Then** filters for item type, contributor, issued year and language are present.
2. **Given** an item type is chosen, **When** the results are shown, **Then** every result carries that type and no other type appears.
3. **Given** two item types are chosen, **When** the results are shown, **Then** results carrying either type appear and no other type does.
4. **Given** a contributor is named, **When** the results are shown, **Then** every result credits that contributor in some role.
5. **Given** an issued year is chosen, **When** the results are shown, **Then** every result's issued date falls in that year, including references whose issued date is a year alone.
6. **Given** an issued year is chosen, **When** the results are shown, **Then** references carrying no issued date at all do not appear.
7. **Given** a language is chosen, **When** the results are shown, **Then** every result carries that language value as stored.
8. **Given** the language filter is offered, **When** its choices are read, **Then** they are the language values the catalogue actually holds and nothing else.
9. **Given** an item type and an issued year are both chosen, **When** the results are shown, **Then** every result satisfies both.
10. **Given** a filter and a search term are both in force, **When** the results are shown, **Then** every result satisfies both, and the page states how many matched.
11. **Given** filters are in force, **When** the page is read, **Then** what is in force is visible on the page and can be cleared from it.
12. **Given** a filter value that matches no reference, or a value that is not valid at all, **When** it is applied, **Then** the page reports that nothing matched and does not show the unfiltered catalogue or raise an error.

---

### User Story 3 - Keep the search, the filters and the sort on the next page (Priority: P3)

A reader searches, filters, sorts, gets four pages of results and clicks page two. They land on page two of what they asked for, with the same search, the same filters and the same sort still in force — not on page two of the whole catalogue.

**Why this priority**: It is what makes the first two stories true beyond their first page, and it is small: the defect is upstream, the fix has shipped, and this story raises the dependency floor to the release carrying it and moves the guard that pinned the old behaviour. It closes issue #88.

**Independent Test**: Over a catalogue large enough for a filtered result to span several pages, apply a search, a filter and a sort, move to the second page, and confirm all three survive.

**Acceptance Scenarios**:

1. **Given** a search whose results span several pages, **When** the reader moves to another page, **Then** the search is still in force and the results are the next page of it.
2. **Given** filters whose results span several pages, **When** the reader moves to another page, **Then** the filters are still in force.
3. **Given** a sorted catalogue spanning several pages, **When** the reader moves to another page, **Then** the sort is still in force.
4. **Given** a search, a filter and a sort all in force, **When** the reader moves to another page, **Then** all three survive together.
5. **Given** a search or a filter in force, **When** the reader sorts by a column, **Then** the search and the filter survive and the sort applies to what they narrowed.
6. **Given** the front-end extra, **When** its dependency floor is read, **Then** it names the released version that preserves the address on a page move.

---

### User Story 4 - The card list can be searched and filtered too (Priority: P4)

A project that routes its catalogue at the card list rather than the table gets the same search box and the same filters, over the same fields, narrowing the same way.

**Why this priority**: Without it, choosing the card presentation silently costs a project the ability to find anything, which turns a documented routing choice into a trap. It sits last of the functional stories because the table is what the package serves by default.

**Independent Test**: Route the catalogue at the card list, apply the same search and the same filters used against the table, and confirm the results agree.

**Acceptance Scenarios**:

1. **Given** the catalogue routed at the card list, **When** the page is opened, **Then** a search box and the same four filters are present.
2. **Given** the same search term applied to both presentations, **When** the results are compared, **Then** they contain the same references.
3. **Given** the same filters applied to both presentations, **When** the results are compared, **Then** they contain the same references.
4. **Given** a search or filter on the card list spanning several pages, **When** the reader moves to another page, **Then** it survives.
5. **Given** the definition of what is searchable and filterable, **When** it is read in the source, **Then** one definition serves both presentations rather than each carrying its own.
6. **Given** the contributor page, **When** it is opened, **Then** it is unchanged and offers neither search nor filters.

---

### User Story 5 - The demo shows it, and a broken one is caught (Priority: P5)

The demo project serves a catalogue big enough and varied enough to search and filter, and the guard that walks it in CI fails when a search stops narrowing, a filter stops applying, or a page move loses either.

**Why this priority**: It is how the feature stays working after the release that introduces it, and it is the standing pattern for front-end work in this package.

**Independent Test**: Run the demo's guard against the branch and confirm it exercises a search, a filter and a page move; then break each in turn and confirm the guard fails.

**Acceptance Scenarios**:

1. **Given** the demo's seed references, **When** they are read, **Then** they span enough item types, years, languages and contributors for every filter to have more than one value.
2. **Given** the demo running, **When** the guard searches the catalogue, **Then** it confirms the results narrowed to the expected references.
3. **Given** the demo running, **When** the guard applies a filter, **Then** it confirms the results narrowed to the expected references.
4. **Given** the demo running, **When** the guard moves to a second page of a filtered result, **Then** it confirms the filter survived.
5. **Given** the guard's existing expectation of a pagination link's exact address, **When** the dependency floor rises, **Then** that expectation is updated to the address the fixed component now emits.

---

### Edge Cases

- A search fragment of one character, or one consisting only of spaces, must behave predictably rather than returning the catalogue as though nothing had been typed.
- A search fragment containing the pattern-matching characters a database treats specially must be matched as literal text.
- A reference credited to the same contributor in two roles must appear once in a contributor-filtered result, not twice.
- A reference whose issued date is a range spanning a year boundary is returned for the year its range begins in.
- A language value differing only by case or by region subtag from another is a distinct value in the filter, because the field stores what the source carried.
- Search and filter terms are held in the address, so a reader can bookmark or share a narrowed catalogue and get the same result back.

## Requirements *(mandatory)*

### Functional Requirements

**Search**

- **FR-001**: The catalogue MUST offer a search box that narrows the results to the references matching what is typed.
- **FR-002**: The search MUST match against the reference's citation key, title, short title, original title and container title, and against the family name, given name and literal name of every contributor credited on it.
- **FR-003**: The search MUST match a fragment appearing anywhere in a value, without regard to case.
- **FR-004**: The search MUST NOT match against the abstract, the keywords, or any other field not named in FR-002.
- **FR-005**: A reference matching in any one of the searched fields MUST be returned, and MUST be returned once however many of them it matches in.
- **FR-006**: The search MUST treat characters that the underlying database gives special meaning in pattern matching as literal text.
- **FR-007**: The page MUST state how many references the current search and filters matched.
- **FR-008**: Clearing the search MUST restore the unnarrowed catalogue.

**Filters**

- **FR-009**: The catalogue MUST offer filters for item type, contributor, issued year and language.
- **FR-010**: The item type filter MUST offer the human-readable, translatable label of each type and MUST narrow on the stored type value.
- **FR-011**: The contributor filter MUST narrow to references crediting a matching contributor in any role, and MUST return such a reference once even when it credits that contributor in more than one role.
- **FR-012**: The issued year filter MUST narrow to references whose `issued` date falls in the chosen year, including dates stored as a year alone and ranges beginning in that year, and MUST exclude references carrying no issued date.
- **FR-013**: The language filter MUST offer the distinct language values the catalogue holds, as stored, and MUST NOT offer a value no reference carries.
- **FR-014**: Choosing more than one value within a filter MUST widen the result to references matching any of them.
- **FR-015**: Filters MUST combine with each other and with the search so that a result satisfies all of them.
- **FR-016**: What is currently in force MUST be visible on the page and clearable from it.
- **FR-017**: A filter value matching nothing, or one that is not valid, MUST produce a stated no-results page rather than an error or the unfiltered catalogue.

**Composing with what is already there**

- **FR-018**: A search, a filter and a sort in force MUST all survive a move to another page of the results.
- **FR-019**: A search and filters in force MUST survive a change of sort, and the sort MUST apply to the narrowed results.
- **FR-020**: The front-end extra's floor on django-mvp MUST rise to the released version whose pagination links preserve the rest of the address, closing issue #88.
- **FR-021**: This feature MUST NOT add an ordering control, a relevance ranking, or any change to how sorting is chosen.
- **FR-022**: The current search and filters MUST be held in the page's address, so that a narrowed catalogue can be bookmarked and shared.

**Both presentations**

- **FR-023**: What is searchable and what is filterable MUST be defined once and used by both the table and the card list.
- **FR-024**: The card list MUST offer the same search and the same filters as the table, narrowing to the same references.
- **FR-025**: The contributor page MUST be unchanged, offering neither search nor filters.

**Staying fast as the catalogue grows**

- **FR-026**: The feature MUST add the indexing its own search and filter queries use, and MUST NOT add an index those queries cannot use.
- **FR-027**: Any index the feature adds MUST be justified by a measurement showing the query planner uses it, recorded with the feature rather than asserted.
- **FR-028**: Where a search cannot be served by an index on a database this package supports, the documentation MUST state that plainly rather than implying a performance the package does not deliver.
- **FR-029**: Rendering a page of results MUST cost a number of database queries that does not grow with the number of results on it.

**Presentation and boundaries**

- **FR-030**: A search or filter returning nothing MUST show a message distinct from the empty-catalogue message, and MUST keep the search and filter controls on the page.
- **FR-031**: The feature MUST NOT change any model or add any field. A migration that adds indexing and nothing else is permitted.
- **FR-032**: Every user-facing string this feature introduces MUST be translatable.

**Packaging, the demo and the documentation**

- **FR-033**: A core-only install MUST resolve nothing this feature adds to the front end.
- **FR-034**: The demo's seed references MUST span enough item types, years, languages and contributors for every filter to offer more than one value.
- **FR-035**: The demo's guard MUST exercise a search, a filter and a page move over a narrowed result, and MUST fail when any of them stops working.
- **FR-036**: The documentation MUST state what the search matches, what it deliberately does not, what each filter narrows on, and how the search and filters compose with sorting and pagination.

### Key Entities

No new entity and no changed field. The search and the filters read what the store already holds: `Item`'s citation key, its title and container-title fields, its `ItemType`, its `language`; the `ItemName` links that credit a `Name` in a role; and the `ItemDate` occupying the `issued` slot.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader who remembers a fragment of a title, a contributor's surname, or a citation key reaches that reference from a catalogue of thousands in one action.
- **SC-002**: A reader can narrow the catalogue to a single item type, a single contributor, a single issued year, or a single language, and to any combination of them together with a search.
- **SC-003**: A search, a filter and a sort applied together all remain in force after moving to another page of the results.
- **SC-004**: A catalogue narrowed by search and filters can be bookmarked and reopened to the same result.
- **SC-005**: The card list returns the same references for the same search and the same filters as the table does.
- **SC-006**: Every index the feature ships is shown by measurement to be used by the query it was added for, and no index is shipped that is not.
- **SC-007**: A search over a catalogue of several thousand references returns its first page without the page's query count growing with the size of the result.
- **SC-008**: The demo's guard fails when a search stops narrowing, a filter stops applying, or a page move discards either.
- **SC-009**: Installing the core alone resolves nothing the front end added for this feature.

## Assumptions

- A released version of django-mvp whose pagination links preserve the rest of the address is available to depend on. It has shipped, so the front-end extra's floor rises to it rather than this feature working around the defect.
- Where the front end meets a defect in the interface layer's own logic or templates, the defect is raised upstream and the floor rises to the release that fixes it. This feature does not fork someone else's markup around a bug (Sam's direction, 2026-08-20).
- The searched and filtered fields are those a reference is identified by. Discovery over abstracts and keywords is a different capability, with different infrastructure behind it, and is not in this feature.
- The filter set — item type, contributor, issued year, language — is what references are commonly grouped by today, not a closed list. It is expected to grow, so the definition of what is filterable is written to be added to.
- Nothing in the front end checks permissions, so a search and its filters are visible to whoever can reach the catalogue page, matching what FS-008 and FS-009 settled for the pages around it.
- Sorting is the column headings FS-009 shipped. This feature composes with them and introduces no ordering surface of its own.
- The contributor page keeps its current behaviour, which is the boundary FS-009 drew for the same page.

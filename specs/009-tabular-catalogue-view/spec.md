# Feature Specification: A Tabular Catalogue View

**Feature Branch**: `009-tabular-catalogue-view`

**Created**: 2026-08-19

**Status**: Draft

**Serves**: G4 (a full front end as an opt-in app built on django-mvp) · Roadmap R6 · Issue #81

**Input**: The catalogue lists references as cards. That reads well for browsing and poorly for managing a library, which is what reference-management software does with a table. The front end gains a tabular catalogue, that becomes what the package serves by default, and the card list stays available to a project that prefers it.

## Clarifications

### Session 2026-08-19 — intake

- Q: The edit control is described as appearing "for users with necessary permissions", but nothing in the front end checks a permission today — the create, edit and delete pages accept any request that reaches them, and every button pointing at them is drawn for everyone. Does this feature introduce access control? → A: No. It uses whatever gating is already in place. If the edit path is open it stays open, if a project has gated it the control follows that gating, and establishing a permission system is a separate piece of work. This restates what FS-008 already settled for the write pages.
- Q: Column ordering is deferred as aspirational, but click-to-sort is a different thing and is the default behaviour of a table. Does the reader get sortable column headers, or a fixed order with sorting left to #49? → A: Sortable headers ship with this feature. What is deferred is the reader choosing which columns appear and in what order they sit.
- Q: An item carries ten title fields. Does the title column amalgamate them by falling back down a chain until it finds a value, or by composing a cell out of more than one of them — the item's own title above the thing it appeared in, as most reference managers show it? → A: A fallback chain in one column. The container is its own column rather than part of the title cell.
- Q: The four named columns are citation key, title, issued date and authors, with others open for discussion. → A: Two more: item type, because a catalogue mixes 45 kinds of thing and a book and a dataset are otherwise indistinguishable in a row, and container title, because with the title column reduced to a fallback chain the journal or book a reference appeared in would appear nowhere on the page.
- Q: A `Name` carries no role — the role lives on `ItemName`, across 26 of them — so an "authors" column has to say which roles it means. → A: The item's author-role contributors, falling back to its editor-role contributors when it has no authors, so an edited volume does not show an empty cell.
- Q: The contributor page is built as a subclass of the catalogue list and is the second place in the front end that lists items. Does it become a table too? → A: No. It stays as it is, on cards.

### Session 2026-08-19 — clarification scan

Resolved from the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: Which title fields make up the fallback chain, and what does a cell show when an item carries none of them? → A: The item's own title, then its short title, then its original title, then its volume title, and finally the citation key. The card already falls back from title to citation key, so the chain extends established behaviour rather than inventing one. Ending at the citation key duplicates a column in the rare case where an item has no title at all, and that is the better trade: the title cell is what links to the reference, and a link whose text is an empty-value marker cannot be read or clicked with confidence.
- Q: The card links every contributor name to that contributor's page, and FS-006 made a contributor's own page a deliverable reachable from the catalogue. Do names in a table cell stay linked? → A: Yes. Dropping the link would quietly withdraw a reachability guarantee an earlier feature established, in the same release that makes the table the default page.
- Q: A row is one line by default, and an item may credit forty contributors. What does the authors cell do with a long list? → A: It shows the first three credited names and states, in a translatable string, that more are credited. An unbounded list either destroys the row's height or is clipped by the browser at whatever character the column happens to end on, and neither is a column anyone can scan.
- Q: Which columns can the reader sort by? → A: Citation key, item type, title, container title and issued date. The authors column and the edit column declare themselves unsortable — one is assembled from a through-model across two roles and has no single value to order on, and the other holds a control rather than data. A column that appears sortable and then orders on something other than what it displays is worse than one that does not offer it.
- Q: Sorting by item type — does it order by what the reader sees or by what is stored? → A: By the stored CSL type. The displayed label is translated, so ordering by it would put the catalogue in a different order in each language and could not be done in the database. This is stated in the spec rather than left as a surprise.
- Q: What is the catalogue's order before the reader sorts it? → A: Newest first, which is what it is today. The change of presentation is not an occasion to change what the page shows first.
- Q: The table view arrives with a search box and a filter control among its default actions. Do they ship? → A: No. Neither is in this feature, and #49 owns making a large catalogue findable. The controls are switched off deliberately rather than left to whichever default the underlying view happens to carry, so a later change to that default cannot introduce a control this feature excluded.
- Q: What does "becomes the package default" mean for a project already running the front end? → A: The route the package already documents for the catalogue serves the table after upgrading. The card list is not removed, deprecated or hidden: it stays a public view class a project routes to instead, and the contributor page goes on using it. A project that wants what it had makes a one-line routing change.
- Q: Does the feature change any model, add a field or ship a migration? → A: No. Every column reads something the store already holds, and the feature is presentation only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read the catalogue as a table (Priority: P1)

Someone opens the catalogue and sees their references as rows rather than cards: one line per reference, with its citation key, what kind of thing it is, its title, the journal or book it appeared in, who is credited on it, and when it was issued. They can run their eye down a single column across the whole page — every title, or every year — which is what a list of cards cannot be read for. Following a title opens that reference's page, and following a name opens that contributor's page, exactly as before.

**Why this priority**: It is the feature. Everything else here either builds on the table or protects what the table replaces, and delivered on its own it already turns a browsing page into something a library can be managed from.

**Independent Test**: Install the front end over a catalogue holding a spread of item types, open the catalogue page, and confirm the references appear as rows carrying the six data columns, that a title leads to its reference and a name to its contributor, and that paging through the catalogue still works.

**Acceptance Scenarios**:

1. **Given** a catalogue holding references, **When** the catalogue page is opened, **Then** each reference occupies one row and the columns are citation key, item type, title, container title, authors and issued date, in that order.
2. **Given** a reference carrying a title, **When** its row is read, **Then** the title cell shows that title and links to the reference's own page.
3. **Given** a reference carrying no title but a short title, **When** its row is read, **Then** the title cell shows the short title.
4. **Given** a reference carrying no title of any kind, **When** its row is read, **Then** the title cell shows its citation key and still links to the reference.
5. **Given** a reference credited to four or more authors, **When** its row is read, **Then** the first three names are shown with an indication that more are credited.
6. **Given** a reference with no author-role contributors but with editors, **When** its row is read, **Then** the editors' names fill the authors cell.
7. **Given** a reference with no contributors at all, **When** its row is read, **Then** the authors cell shows an empty-value marker rather than nothing.
8. **Given** a reference whose issued date is a year alone, **When** its row is read, **Then** the issued cell shows that year and does not invent a month or a day.
9. **Given** a catalogue with more references than fit on one page, **When** the reader moves to the next page, **Then** the table renders the next set of rows under the same headings.
10. **Given** an empty catalogue, **When** the page is opened, **Then** the existing empty-state message is shown rather than a table of no rows.
11. **Given** a page of references, **When** the page is rendered, **Then** the number of database queries does not grow with the number of rows on it.

---

### User Story 2 - Edit a reference without opening it (Priority: P2)

Someone spots a wrong page range or a misspelled title while scanning the catalogue. Rather than opening the reference, reading it, and then opening its form, they act on the row directly and land on that reference's edit form. What happens after they save is unchanged.

**Why this priority**: It is the second thing issue #81 asks for and the reason a table beats a list for management work — a correction pass over an imported library is a sequence of small edits, and the detail page in between doubles the number of pages loaded to make each one.

**Independent Test**: Open the catalogue, use a row's edit control, confirm it opens that row's reference in the edit form, change a field, save, and confirm the change is stored.

**Acceptance Scenarios**:

1. **Given** a row in the catalogue, **When** the reader looks at it, **Then** it carries an edit control.
2. **Given** a row's edit control, **When** it is followed, **Then** the edit form for that reference opens.
3. **Given** the edit form reached from a row, **When** it is saved, **Then** the reference is updated and the reader lands where saving that form already takes them.
4. **Given** a project that has gated the edit page, **When** the catalogue is rendered for someone the gate excludes, **Then** the edit control follows that gating, and this feature adds no check of its own.

---

### User Story 3 - Order the catalogue by a column (Priority: P3)

Someone wants the catalogue oldest first, or grouped by kind, or alphabetical by journal. They act on the column heading and the whole catalogue reorders — not only the page in front of them — and the order holds as they page through it.

**Why this priority**: Sorting is what makes a table worth having over a list, but the table is legible and useful without it, so it is a genuine slice rather than a precondition.

**Independent Test**: Open a catalogue spanning several item types, journals and years, sort by each sortable column in both directions, confirm the whole catalogue reorders rather than the current page, and confirm the order survives moving to the next page.

**Acceptance Scenarios**:

1. **Given** the catalogue, **When** it is first opened, **Then** the newest references are shown first.
2. **Given** the citation key, item type, title, container title or issued date heading, **When** the reader acts on it, **Then** the catalogue reorders by that column.
3. **Given** a column already sorted, **When** the reader acts on the same heading again, **Then** the direction reverses.
4. **Given** a catalogue sorted by a column, **When** the reader moves to the next page, **Then** the sort still applies.
5. **Given** the authors column or the edit column, **When** the reader looks at the heading, **Then** it offers no sort.
6. **Given** references some of which carry no issued date, **When** the catalogue is sorted by issued date, **Then** every reference still appears, with the undated ones grouped consistently at one end.
7. **Given** a catalogue sorted by item type, **When** the order is read, **Then** it follows the stored type rather than the translated label, and the documentation says so.

---

### User Story 4 - Keep the card list (Priority: P4)

A Django developer embedding the package prefers the card presentation for their own users — a public-facing reading list rather than a management tool. They route the catalogue at the card view instead, and get exactly the page the package served before, without forking anything or copying a template out of the package.

**Why this priority**: It is a promise about not breaking people rather than a new capability, and it holds the moment the default changes. It is last of the reader-facing slices because nothing depends on it, and first in importance if it is ever dropped.

**Independent Test**: In a project using the front end, point the catalogue route at the card view, and confirm the page renders as it did before the table existed, with pagination, the empty state and the create action intact.

**Acceptance Scenarios**:

1. **Given** the front end installed with no configuration, **When** the catalogue route is opened, **Then** the table is served.
2. **Given** a project that routes the catalogue at the card view instead, **When** the catalogue is opened, **Then** references appear as cards exactly as they did before this feature.
3. **Given** the contributor page, **When** it is opened, **Then** it presents cards, unchanged.
4. **Given** the package's documentation, **When** a developer looks for how to choose between the two, **Then** it names both views and shows the routing change.
5. **Given** a project that installs the core alone, **When** its dependencies are resolved, **Then** neither the front-end layer nor the table package is pulled in.

---

### User Story 5 - The demo shows the table, and a broken one is caught (Priority: P5)

Someone evaluating the package starts the demo and the catalogue they land on is the table, over the seed references. If a change breaks the table — a row that no longer links to its reference, an edit control that leads nowhere — the guard that walks the demo in CI fails before anyone is asked to look at it.

**Why this priority**: Article XII requires the demo to stay current with the package in the same change, and the guard is the only thing that exercises these pages over real data against a running server. It comes last because it guards the other four rather than delivering anything on its own.

**Independent Test**: Start the demo, confirm the catalogue serves the table over the seed references, then run the guard against it and confirm it passes; break a row's link and confirm it fails.

**Acceptance Scenarios**:

1. **Given** the demo started as documented, **When** the catalogue is opened, **Then** it serves the table over the seed references.
2. **Given** the running demo, **When** the guard walks it, **Then** it reaches a reference by following a row rather than by constructing an address.
3. **Given** the running demo, **When** the guard walks it, **Then** it reaches an edit form from a row's edit control.
4. **Given** a table whose rows no longer link to their references, **When** the guard runs, **Then** it fails and names what it could not reach.

---

### Edge Cases

- A reference carrying none of the title fields — the title cell falls back to the citation key, which is also its own column.
- A reference credited to forty contributors — three names and a translatable indication that more exist.
- A reference credited only to editors, translators or neither.
- A reference whose only date is `accessed` — the issued column shows an empty-value marker.
- An issued date stored as a range, or as a year alone, or as an un-normalizable literal.
- A container title long enough to push every other column off the screen.
- A catalogue sorted by issued date where some references have no issued date at all.
- The last page of a sorted catalogue, and a page number beyond the end.
- A catalogue holding one reference, and a catalogue holding none.
- Two references sharing a citation key, which the store permits.

## Requirements *(mandatory)*

### Functional Requirements

**The table**

- **FR-001**: The catalogue MUST present each stored reference as one row of a table.
- **FR-002**: The columns MUST be, in order: citation key, item type, title, container title, authors, issued date, and an edit control.
- **FR-003**: The title cell MUST show the first value the reference carries from its title, short title, original title, volume title, and citation key, in that order.
- **FR-004**: The title cell MUST link to the reference's own page.
- **FR-005**: The item type cell MUST show the type's human-readable, translatable label rather than its stored CSL value.
- **FR-006**: The authors cell MUST list the reference's author-role contributors in their stored order, and when it has none, its editor-role contributors instead.
- **FR-007**: The authors cell MUST show at most three names, followed by a translatable indication that further contributors are credited when there are more.
- **FR-008**: Each name in the authors cell MUST link to that contributor's page.
- **FR-009**: The issued cell MUST render the reference's `issued` date slot at the precision it is stored — year, year and month, full date, or a range — and MUST NOT imply a precision the store does not hold.
- **FR-010**: A cell for which the reference holds no value MUST render an explicit empty-value marker rather than an empty cell.
- **FR-011**: Pagination, page size, the empty state and the create action MUST behave as they do on the catalogue today.
- **FR-012**: Rendering a page MUST cost a number of database queries that does not grow with the number of rows on it.

**Ordering**

- **FR-013**: The catalogue MUST be ordered newest first before the reader sorts it.
- **FR-014**: The reader MUST be able to reorder the whole catalogue by the citation key, item type, title, container title and issued date columns, in both directions, from the column heading.
- **FR-015**: The authors column and the edit column MUST declare themselves unsortable.
- **FR-016**: A sort MUST persist as the reader moves between pages.
- **FR-017**: Sorting by item type MUST order by the stored type value, and the documentation MUST state that this is not the alphabetical order of the displayed labels.
- **FR-018**: Sorting by issued date MUST retain references that carry no issued date, ordering them consistently rather than dropping them.

**Editing from a row**

- **FR-019**: Each row MUST carry a control that opens the edit form for that reference.
- **FR-020**: The edit control's visibility MUST follow the same mechanism the reference page's own edit action uses. This feature MUST NOT introduce a permission check, a login requirement, or any other access control.

**What the package serves, and what it keeps**

- **FR-021**: The catalogue route the package documents MUST serve the table with no configuration.
- **FR-022**: The card list MUST remain a public view class that a project can route the catalogue at instead, with no template copied out of the package and nothing deprecated.
- **FR-023**: The contributor page MUST continue to present cards.
- **FR-024**: The documentation MUST name both presentations, state which is served by default, and show the routing change that selects the other.

**Boundaries**

- **FR-025**: The table MUST NOT present a search box, a filter control, or any means of choosing which columns appear or in what order they sit.
- **FR-026**: The feature MUST NOT change any model, add any field, or ship any migration.

**Packaging and the demo**

- **FR-027**: The `ui` extra MUST install what the table rendering needs, and a core-only install MUST resolve neither the front-end layer nor the table package.
- **FR-028**: The demo MUST serve the table at its catalogue route, and its guard MUST reach a reference by following a row and an edit form by following a row's edit control.
- **FR-029**: Every user-facing string this feature introduces MUST be translatable, and the README and CHANGELOG MUST describe the change of default in the same change.

### Key Entities

No new entity, and no change to an existing one. Every column reads what the store already holds: `Item`'s own title and container-title fields, its `ItemType`, the `ItemName` links carrying role and position, and the `ItemDate` occupying the `issued` slot.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project that installs the front end and changes no setting gets a catalogue of rows carrying all six data columns and an edit control.
- **SC-002**: A reader can tell a reference's key, kind, title, venue, credited names and year of issue from the catalogue page alone, without opening a single reference.
- **SC-003**: A reader reaches a reference's edit form from the catalogue in one action, where it previously took two.
- **SC-004**: A reader can reorder the catalogue by each of the five sortable columns in both directions, and the order holds across every page of the result.
- **SC-005**: A project that prefers cards restores the previous page by changing one line of routing, with nothing copied out of the package.
- **SC-006**: The demo serves the table over its seed references, and the guard that walks it fails when a row no longer reaches its reference or its edit form.
- **SC-007**: Installing the core alone resolves neither the front-end layer nor the table package.

## Assumptions

- A released version of django-mvp carrying the table view and its full-screen layout is available to depend on; the front-end extra's floor rises to it rather than the feature vendoring anything.
- The table package the front end needs is added to the `ui` extra. The project's stack constraints currently name django-mvp as the one adopted UI layer and require an amendment before another is adopted, and that amendment is a separate change made outside this feature.
- Nothing in the front end checks permissions today, so "the same gating the edit action already has" means, in the package as it stands, none. FS-008 settled that the write pages are open on the assumption of one person managing their own library.
- Finding a reference in a large catalogue — search, filtering and the ordering that goes with them — is issue #49 and is not in this feature, so the table ships with those controls switched off rather than absent by oversight.
- User-configurable columns and column order remain aspirational, as issue #81 states.

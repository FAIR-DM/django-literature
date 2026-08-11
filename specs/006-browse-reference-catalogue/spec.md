# Feature Specification: Browse the Reference Catalogue in an Opt-In Front End

**Feature Branch**: `006-browse-reference-catalogue`

**Created**: 2026-08-11

**Status**: Draft

**Serves**: G4 (a full front end as an opt-in app built on django-mvp) · Roadmap R6 · Issue #45

**Input**: A project that wants a ready-made interface should be able to install one alongside the core and look at what is stored straight away: a list of the references in the catalogue, and a page for a single reference with its contributors, dates and identifiers. It stays opt-in, so a project that only wants the store installs the core on its own and pulls in nothing extra. The interface brings its own look rather than borrowing the host project's, built on django-mvp, so it arrives complete and consistent without any styling work from whoever adopts it.

## Clarifications

### Session 2026-08-11 — intake

- Q: django-accounts-center runs under a standing rule: it writes no custom components and no custom CSS, composes django-mvp components only, and a gap in django-mvp's component set goes upstream rather than being solved locally. Does this app inherit that rule? → A: Yes. The built-in components are the default. A need for something custom is raised before it is built and may become an upstream request; a local implementation is a temporary bridge only, and it comes out when a django-mvp release carries the component.
- Q: The search feature (#49) ends with "move through the results in a predictable order", which reads as though paging belongs there. But a list that renders every reference on one page is unusable from the first realistic catalogue. Does paging ship here or wait? → A: Here. The list is paginated in one fixed default order. Text search, filtering, and any reader-chosen ordering are #49's.
- Q: The request names contributors, dates and identifiers on the reference page, but an item also stores every scalar CSL field of its own — publisher, volume, page, container title, abstract, and the rest. Is the page the whole record or a minimal one? → A: The whole record. The scalar fields are shown as a labelled set alongside the three related collections, and a field the item does not carry is omitted rather than rendered blank.
- Q: Do the browse pages require anyone to be signed in? → A: No. They are open by default, and a host wanting the catalogue behind authentication wires the URL include behind its own protection, exactly as it would for any embedded app. Gating and its configuration are a later specification's problem.

### Session 2026-08-11 — clarification scan

Resolved from the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: Intake fixed "one default order" and floated newest issued date first. An issued date lives in a related record, is partial by nature, and may be a range or absent entirely. Which order does the list use? → A: The catalogue's existing default, most recently added first, which is what the store already declares. An issued-date order would have to rule on how a year-only date sorts against a full date, where a range sits, and where an item with no issued date goes. Those are reader-visible rulings this feature has no reason to make, #49 has to make anyway when it offers a choice of order, and making them twice is how a package ends up with two orders that disagree. This narrows the intake answer, which named the order only as an example.
- Q: What does a list entry have to carry? → A: Enough to recognise the reference without opening it — its title, its item type, its contributors in the order and roles stored, its issued date at the precision stored, and its citation key. The citation key is included because it is the handle a reader already uses to refer to an item, and it is the one thing a list of similar titles can be told apart by.
- Q: What addresses a single reference's page? → A: The item's primary key. A citation key is explicitly not globally unique — the store resolves collisions per import batch by suffixing — so it cannot address a page without inventing a uniqueness the model does not have. The citation key is displayed on both pages and never used to address one.
- Q: A contributor is stored as a shared record across items, so a page listing everything one contributor worked on is a short step from here. Is it in scope? → A: No. The request names one list and one reference page, and no sibling issue in R6 owns a contributor-centred view. Adding one here would widen the feature past what was agreed. It is recorded as a possible later feature rather than assumed.
- Q: How does django-mvp reach a host without the core acquiring a front-end dependency? → A: As an optional extra the package declares. Installing the core alone resolves no front-end package; a host that wants the interface installs the extra and adds the app. This is what makes "opt-in" a property of the dependency graph rather than a convention.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See what is in the catalogue (Priority: P1)

Someone has a project with references already in it — imported from a BibTeX or RIS file, or created in code — and wants to look at them without writing a view. They install the interface alongside the core, include its URLs, and open the catalogue. They get a list of the references, each one showing enough to recognise it, in a stated order, split across pages so a large library stays usable. An empty catalogue says it is empty rather than showing a blank page.

**Why this priority**: It is the smallest thing that makes the package's contents visible, and every other page in R6 is reached from it. Delivered alone it already replaces the shell session that is the only way to look at a catalogue today.

**Independent Test**: Install the core and the interface into a project holding a set of references, wire the include, open the catalogue URL, and confirm the references are listed, paginated, and ordered as specified.

**Acceptance Scenarios**:

1. **Given** a project with the core and the interface installed and the URLs included, **When** a reader opens the catalogue page, **Then** the references are listed, most recently added first, showing title, item type, contributors, issued date and citation key.
2. **Given** a catalogue holding more references than fit on one page, **When** the reader opens the catalogue, **Then** one page of results is rendered with a statement of where in the catalogue they are and a way to move through the rest.
3. **Given** a catalogue holding no references, **When** the reader opens the catalogue, **Then** the page renders and states that there is nothing stored.
4. **Given** a listed reference, **When** the reader follows it, **Then** they arrive at that reference's own page.

---

### User Story 2 - Read one reference in full (Priority: P2)

A reader has found a reference in the list and wants everything the catalogue holds about it. The reference's page shows its whole record: every scalar field the item actually carries under a readable label, its contributors grouped by role and in the order stored, its dates by slot at the precision they were stored with, and its typed identifiers. Fields the item does not carry are absent rather than shown empty, so a journal article does not display a shelf of blank map and legal-case fields.

**Why this priority**: It is the half of the request that browsing exists for — the list identifies a reference, this page answers what is known about it. It builds on US1 but is testable and valuable on its own.

**Independent Test**: Open the page for a stored reference directly and confirm the record it shows matches what the catalogue holds, with absent fields omitted.

**Acceptance Scenarios**:

1. **Given** a stored reference, **When** a reader opens its page, **Then** every scalar field the item carries is shown under a readable label, and no field it does not carry appears.
2. **Given** a reference with contributors in several roles, **When** the reader opens its page, **Then** the contributors appear grouped by role and in the position order stored within each role.
3. **Given** a reference carrying a year-only date and one carrying a date range, **When** the reader opens each page, **Then** each date is shown at the precision stored, and a range is shown as a range.
4. **Given** a reference carrying identifiers, **When** the reader opens its page, **Then** each identifier is shown with its type, and one addressing a resolvable location is followable.
5. **Given** a reference that does not exist, **When** a reader requests its page, **Then** the response is a not-found, not an error.
6. **Given** a reference with no contributors, no dates and no identifiers, **When** the reader opens its page, **Then** the page renders without those sections rather than failing.

---

### User Story 3 - Install the store on its own and get nothing extra (Priority: P3)

A project that only wants somewhere to keep references installs the core, and that is all it gets. No front-end package is resolved into its environment, no interface app appears in its project, and nothing it already runs changes. The interface is something it can add later by installing an extra and adding one app.

**Why this priority**: It is a guarantee rather than a journey, and it delivers no browsing value on its own — which is exactly why it is stated separately and verified separately. It is the property the roadmap protects, and the one most easily lost by accident once the interface exists.

**Independent Test**: Resolve the package without the extra in a clean environment and confirm no front-end dependency is present and the core's behaviour is unchanged with the interface app absent.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** the package is installed without the interface extra, **Then** no front-end package is resolved into it.
2. **Given** a project with only the core in `INSTALLED_APPS`, **When** it runs, **Then** the core behaves exactly as it did before this feature and imports nothing from the interface app.
3. **Given** a project that later installs the extra and adds the interface app, **When** it includes the URLs, **Then** the interface works with no further configuration.

---

### Edge Cases

- **A reference with no title.** The list entry stays recognisable by falling back to the handle the store itself falls back to, rather than rendering an empty row.
- **A very long title, abstract, or contributor list.** The list stays readable at any single entry's size; the reference page shows the whole value rather than truncating what the catalogue holds.
- **An item type the interface has never been shown.** Every one of the catalogue's item types renders on both pages, because the page is built from the fields the item carries rather than from a per-type layout.
- **A page number beyond the end of the catalogue.** A stated not-found rather than an unhandled error or a silent empty page.
- **A contributor stored as an unparsed or institutional name.** Shown as the store holds it, not split into parts it does not have.
- **An identifier of an unknown type.** Shown with the type as stored; the interface does not reject or hide identifier types the store accepts.
- **A catalogue of several thousand references.** The first page renders without the work growing with the catalogue's size.

## Requirements *(mandatory)*

### Functional Requirements

**The app**

- **FR-001**: The package MUST ship a front-end app, `literature.ui`, which a host enables by adding it to `INSTALLED_APPS` alongside the core (Article X).
- **FR-002**: Installing the core MUST resolve no front-end dependency. django-mvp MUST arrive only through an optional extra the package declares, so opt-in is a property of the dependency graph and not a convention.
- **FR-003**: The app's URLs MUST be an optional, namespaced include that the host wires up. Nothing is mounted automatically (Article X).
- **FR-004**: The app MUST work with no configuration. Any configuration it introduces MUST live under the namespaced `LITERATURE` settings key (Article X).
- **FR-005**: Every name the app makes public MUST be importable from the `literature` namespace and MUST NOT collide with common Django project structures (Article X).
- **FR-006**: No core module may import from the app, and the core MUST behave exactly as it does today when the app is absent from `INSTALLED_APPS`.
- **FR-007**: Every user-facing string the app produces MUST be translatable (Article VIII).

**The design system**

- **FR-008**: Every visual element on both pages MUST be composed from django-mvp's own components and design system. The app MUST NOT ship a stylesheet of its own and MUST NOT define components of its own.
- **FR-009**: Where django-mvp carries no component for something these pages need, the need MUST be raised before anything is built, and a genuine gap MUST be filed as a request against django-mvp. A local implementation MAY stand in until a django-mvp release carries the component, and MUST be recorded in the specification's *Component gaps* section so that it is removed when the release lands.
- **FR-010**: The interface MUST NOT adopt or blend into the host project's styling.
- **FR-011**: The package MUST depend on django-mvp at its current release, and the development toolchain bundle MUST be moved to its current release in the same change.

**The catalogue list**

- **FR-012**: The app MUST offer a page listing the references in the catalogue.
- **FR-013**: Each entry MUST carry the reference's title, its item type, its contributors in the roles and order stored, its issued date at the precision stored, and its citation key. Where an item has no title, the entry MUST fall back to the store's own fallback handle rather than rendering empty.
- **FR-014**: The list MUST be paginated, and MUST NOT render the whole catalogue on one page at any catalogue size.
- **FR-015**: The list MUST use one fixed order — most recently added first, the catalogue's declared default. Offering a choice of order is out of scope.
- **FR-016**: Each entry MUST link to that reference's own page.
- **FR-017**: Pagination MUST state where in the catalogue the reader is and MUST be navigable forward and back. A requested page beyond the end MUST produce a not-found.
- **FR-018**: A catalogue holding no references MUST render the page with a stated empty result, not an error and not a blank page.

**The reference page**

- **FR-019**: The app MUST offer a page for one reference, addressed by the item's primary key. A citation key MUST NOT address the page, because citation keys are not globally unique.
- **FR-020**: The page MUST show every scalar field the item carries, each under a human-readable label.
- **FR-021**: A field the item does not carry MUST be absent from the page entirely, label included.
- **FR-022**: The page MUST show the item's contributors grouped by role and in the position order stored within each role, showing an unparsed or institutional name as the store holds it.
- **FR-023**: The page MUST show the item's dates by slot at the precision stored, showing a range as a range and a fallback value where the store holds one.
- **FR-024**: The page MUST show the item's identifiers with their type, including types the store does not recognise, and an identifier addressing a resolvable location MUST be followable.
- **FR-025**: A request for a reference that does not exist MUST produce a not-found response.
- **FR-026**: The page MUST render for every one of the catalogue's item types, and for an item carrying no contributors, no dates and no identifiers.

**The boundary**

- **FR-027**: Both pages MUST be read-only. Nothing in this feature may create, change, or delete a reference or any of its related records.
- **FR-028**: The pages MUST be reachable without authentication and the app MUST NOT impose a permission check of its own. Restricting access is the host's to do.
- **FR-029**: Text search, filtering, a choice of ordering, importing a file through the interface, editing anything, and a runnable demo project MUST NOT be delivered here. They belong to issues #47, #48, #49, #50 and #46.
- **FR-030**: No admin-based management ships with the package (README), and this feature MUST NOT add any.
- **FR-031**: The vocabulary this feature introduces MUST be added to `CONTEXT.md` in the same change (Article VI): the *UI app* as the name for `literature.ui`, and the *catalogue* as the name for the set of stored items when spoken about from the interface.

### Requirement coverage

- **User Story 1** carries FR-012 through FR-018, and rests on FR-001, FR-003 and FR-008.
- **User Story 2** carries FR-019 through FR-026, and rests on the same three.
- **User Story 3** carries FR-002 and FR-006, and is what FR-001's separation exists for.
- **FR-004, FR-005, FR-007, FR-010 and FR-011** constrain the feature as a whole and every story's acceptance is judged against them.
- **FR-009** is a process requirement covering the run, verified by the presence or absence of entries under *Component gaps*.
- **FR-027 through FR-031** are boundary and documentation requirements, verified by inspection.

### Key Entities

This feature persists nothing and adds no model. The entities it introduces are surfaces:

- **UI app** (`literature.ui`): the opt-in Django app carrying the interface. Installed alongside the core, never required by it.
- **Catalogue list**: the page listing stored items, paginated, in the store's declared default order.
- **Reference page**: the page showing one item's whole record — its scalar fields, and its contributors, dates and identifiers.

### Component gaps

Empty at specification time. FR-009 requires that any component built locally because django-mvp has none is recorded here, with the upstream request it was filed under, so it can be removed when a django-mvp release carries the component.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project installing the package without the interface extra resolves no front-end dependency, and its use of the core is unchanged.
- **SC-002**: A project installing the extra, adding one app and including the URLs reaches a working catalogue list and reference page without writing a view, a template, a URL pattern, or a line of styling.
- **SC-003**: A catalogue of several thousand references renders its first page, and the rendered page does not grow with the catalogue's size.
- **SC-004**: A reader can tell two references apart from their list entries and reach either one's page in a single step.
- **SC-005**: For any stored item, every scalar field it carries appears on its page and no field it does not carry appears at all.
- **SC-006**: Contributors appear in the roles and order the catalogue stores, dates at the precision they were stored with, and identifiers with their type — so the pages report the store rather than reinterpreting it.
- **SC-007**: The app ships no stylesheet and defines no component of its own, or every exception is listed under *Component gaps* with the upstream request that will retire it.
- **SC-008**: Every one of the catalogue's item types renders on both pages, including an item carrying no contributors, no dates and no identifiers, and no reference produces an unhandled error.
- **SC-009**: The core's existing behaviour is unchanged: its test suite passes with the interface app absent.

## Assumptions

- **The catalogue is populated by existing means.** Items arrive through the import paths delivered in R5 or through code. Nothing here creates data, and nothing here depends on how it got there.
- **The demo project is a separate feature.** Issue #46 builds it and depends on this one. Verification here does not wait for it and does not assume it.
- **django-mvp's component set is taken as it stands at its current release.** Whether it covers these two pages is settled during planning, not assumed here; FR-009 is what handles the answer being no.
- **No contributor-centred page.** Contributors are shown on the reference page. A page collecting everything one contributor worked on is a possible later feature and is not assumed by anything here.
- **Templates are resolvable by Django's standard mechanism**, so a host can override one, but this feature promises no override contract and defines no extension points. A stable theming surface is a separate question.
- **Access control is a later specification.** The pages are open, and a host restricts them at the point it includes the URLs.
- **The store's existing limits are inherited.** One identifier per type per item, one date per slot, batch-scoped citation-key de-duplication, and partial-date fallbacks all apply as they do today. The interface displays them and does not widen them.

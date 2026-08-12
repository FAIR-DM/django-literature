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
- Q: What does a list entry have to carry? → A: Enough to recognise the reference without opening it — its title, its item type, its contributors in the order and roles stored, its issued date at the precision stored, and its citation key. The citation key is included because it is the handle a reader already uses to refer to an item, and it is the one thing a list of similar titles can be told apart by. *(Widened after this spec landed — an entry now also carries a snippet of the abstract, truncated. See issue #65 and FR-013's note. The set named here stays what an entry must carry; the abstract was added because "recognise the reference without opening it" is exactly what a reader cannot do from a title alone when the titles are unfamiliar, which is this answer's own test.)*
- Q: What addresses a single reference's page? → A: The item's primary key. A citation key is explicitly not globally unique — the store resolves collisions per import batch by suffixing — so it cannot address a page without inventing a uniqueness the model does not have. The citation key is displayed on both pages and never used to address one.
- Q: A contributor is stored as a shared record across items, so a page listing everything one contributor worked on is a short step from here. Is it in scope? → A: ~~No. The request names one list and one reference page, and no sibling issue in R6 owns a contributor-centred view.~~ *(Reversed at the specification gate — see the gate session below.)*

### Session 2026-08-11 — specification gate

- Q: Does the feature cover a contributor's own page, reachable by browsing to a name and showing everything they worked on? → A: Yes, added at the gate on the maintainer's instruction. A contributor's name on a reference page becomes a link to that contributor's page, which lists the items they contributed to and the role they held on each. It is a browsing destination reached by navigation, distinct from filtering the catalogue by contributor, which stays with #49. This reverses the scan's answer above, which had ruled it out as unrequested scope.
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

A project that only wants somewhere to keep references installs the core, and that is all it gets. No front-end package is resolved into its environment, no interface app appears in its project, and nothing it already runs changes. The interface is something it can add later by installing an extra and following the documented install steps.

**Why this priority**: It is a guarantee rather than a journey, and it delivers no browsing value on its own — which is exactly why it is stated separately and verified separately. It is the property the roadmap protects, and the one most easily lost by accident once the interface exists.

**Independent Test**: Resolve the package without the extra in a clean environment and confirm no front-end dependency is present and the core's behaviour is unchanged with the interface app absent.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** the package is installed without the interface extra, **Then** no front-end package is resolved into it.
2. **Given** a project with only the core in `INSTALLED_APPS`, **When** it runs, **Then** the core behaves exactly as it did before this feature and imports nothing from the interface app.
3. **Given** a project that later installs the extra and follows the documented install steps, **When** it includes the URLs, **Then** the interface works without it writing a view, a template, a URL pattern or a line of styling.

---

### User Story 4 - Follow a contributor to everything they worked on (Priority: P4)

A reader looking at a reference recognises one of its authors and wants to know what else by that person the catalogue holds. The contributor's name on the reference page is a link, and following it opens that contributor's own page: the name as the catalogue stores it, and the items they contributed to, each showing the role they held on it. The list is paginated in the same order as the catalogue, so a prolific contributor stays as usable as a large library. Because contributors are stored once and shared across items, this is the catalogue's own answer rather than a search built on top of it.

**Why this priority**: It is the newest addition and the one the other three do not depend on, so it is the last to be built and the safest to be interrupted. It is the second most-asked thing of a reference catalogue after the reference itself, and having it here means a reader gets there by browsing rather than by constructing a query.

**Independent Test**: Open a stored contributor's page directly and confirm it lists the items they contributed to, with roles, paginated, and that it is reachable from a reference page carrying that contributor.

**Acceptance Scenarios**:

1. **Given** a reference with contributors, **When** a reader opens its page, **Then** each contributor's name is a link to that contributor's own page.
2. **Given** a contributor credited on several items, **When** a reader opens their page, **Then** the items they contributed to are listed, each showing the role they held on it.
3. **Given** a contributor holding more than one role on the same item, **When** a reader opens their page, **Then** the item appears once, carrying every role they held on it.
4. **Given** a contributor credited on more items than fit on one page, **When** a reader opens their page, **Then** the list is paginated in the same order and with the same navigation as the catalogue.
5. **Given** a contributor stored as an unparsed or institutional name, **When** a reader opens their page, **Then** the name is shown as the store holds it.
6. **Given** a contributor credited on nothing, **When** a reader opens their page, **Then** the page renders and states that there is nothing stored against them.
7. **Given** a contributor that does not exist, **When** a reader requests their page, **Then** the response is a not-found, not an error.

---

### Edge Cases

- **A reference with no title.** The list entry stays recognisable by falling back to the handle the store itself falls back to, rather than rendering an empty row.
- **A very long title, abstract, or contributor list.** The list stays readable at any single entry's size; the reference page shows the whole value rather than truncating what the catalogue holds.
- **An item type the interface has never been shown.** Every one of the catalogue's item types renders on both pages, because the page is built from the fields the item carries rather than from a per-type layout.
- **A page number beyond the end of the catalogue.** A stated not-found rather than an unhandled error or a silent empty page.
- **A contributor stored as an unparsed or institutional name.** Shown as the store holds it, not split into parts it does not have, on the reference page and on their own page alike.
- **Two contributors whose stored names are identical.** They are separate records and keep separate pages. The interface does not merge them, and deciding whether two names are the same person is not attempted here.
- **A contributor credited on thousands of items.** Their page pages through them exactly as the catalogue does, so a prolific author is no more expensive to open than any other.
- **An identifier of an unknown type.** Shown with the type as stored; the interface does not reject or hide identifier types the store accepts.
- **A catalogue of several thousand references.** The first page renders without the work growing with the catalogue's size.

## Requirements *(mandatory)*

### Functional Requirements

**The app**

- **FR-001**: The package MUST ship a front-end app, `literature.ui`, which a host enables by adding it to `INSTALLED_APPS` alongside the core (Article X).
- **FR-002**: Installing the core MUST resolve no front-end dependency. django-mvp MUST arrive only through an optional extra the package declares, so opt-in is a property of the dependency graph and not a convention.
- **FR-003**: The app's URLs MUST be an optional, namespaced include that the host wires up. Nothing is mounted automatically (Article X).
- **FR-004**: The app MUST introduce no configuration of its own — a host that has installed it and its declared dependencies gets working pages without setting anything. Any configuration it later introduces MUST live under the namespaced `LITERATURE` settings key (Article X). Installing the app's dependencies, which the host does once from the documented steps, is not configuration in this sense (see D8).
- **FR-005**: Every name the app makes public MUST be importable from the `literature` namespace and MUST NOT collide with common Django project structures (Article X).
- **FR-006**: No core module may import from the app, and the core MUST behave exactly as it does today when the app is absent from `INSTALLED_APPS`.
- **FR-007**: Every user-facing string the app produces MUST be translatable (Article VIII).

**The design system**

- **FR-008**: Every visual element on both pages MUST be composed from django-mvp's own components and design system. The app MUST NOT ship a stylesheet of its own and MUST NOT define components of its own.
- **FR-009**: Where django-mvp carries no component for something these pages need, the need MUST be raised before anything is built, and a genuine gap MUST be filed as a request against django-mvp. A local implementation MAY stand in until a django-mvp release carries the component, and MUST be recorded in the specification's *Component gaps* section so that it is removed when the release lands.
- **FR-010**: The interface MUST NOT adopt or blend into the host project's styling.
- **FR-011**: The package MUST depend on django-mvp at its current release (0.17.0 at the time of writing). The shared development toolchain the package already pins is at its own current release and needs no move.

**The catalogue list**

- **FR-012**: The app MUST offer a page listing the references in the catalogue.
- **FR-013**: Each entry MUST carry the reference's title, its item type, its contributors in the roles and order stored, its issued date at the precision stored, and its citation key. Where an item has no title, the entry MUST fall back to the store's own fallback handle rather than rendering empty. *(Amended by issue #65: an entry also carries a truncated snippet of the abstract where the item holds one, and nothing where it does not. The list above remains the minimum, not the maximum.)*
- **FR-014**: The list MUST be paginated, and MUST NOT render the whole catalogue on one page at any catalogue size.
- **FR-015**: The list MUST use one fixed order — most recently added first, the catalogue's declared default. Offering a choice of order is out of scope.
- **FR-016**: Each entry MUST link to that reference's own page.
- **FR-017**: Pagination MUST state where in the catalogue the reader is and MUST be navigable forward and back. A requested page beyond the end MUST produce a not-found.
- **FR-018**: A catalogue holding no references MUST render the page with a stated empty result, not an error and not a blank page.

**The reference page**

- **FR-019**: The app MUST offer a page for one reference, addressed by the item's primary key. A citation key MUST NOT address the page, because citation keys are not globally unique.
- **FR-020**: The page MUST show every scalar field the item carries, each under a human-readable label.
- **FR-021**: A field the item does not carry MUST be absent from the page entirely, label included.
- **FR-022**: The page MUST show the item's contributors grouped by role and in the position order stored within each role, showing an unparsed or institutional name as the store holds it. Each contributor's name MUST link to that contributor's own page.
- **FR-023**: The page MUST show the item's dates by slot at the precision stored, showing a range as a range and a fallback value where the store holds one.
- **FR-024**: The page MUST show the item's identifiers with their type, including types the store does not recognise, and an identifier addressing a resolvable location MUST be followable.
- **FR-025**: A request for a reference that does not exist MUST produce a not-found response.
- **FR-026**: The page MUST render for every one of the catalogue's item types, and for an item carrying no contributors, no dates and no identifiers.

**The contributor page**

- **FR-032**: The app MUST offer a page for one contributor, addressed by the contributor record's primary key. A stored name is not unique and carries no other stable handle, so nothing else can address the page.
- **FR-033**: The page MUST show the contributor's name as the store holds it, including an unparsed or institutional name, without splitting it into parts it does not have.
- **FR-034**: The page MUST list the items the contributor is credited on, each entry carrying what a catalogue entry carries under FR-013 and linking to that reference's page.
- **FR-035**: Each entry MUST show the role or roles the contributor held on that item. An item on which they held more than one role MUST appear once, carrying every role.
- **FR-036**: The list MUST be paginated and ordered exactly as the catalogue list is under FR-014, FR-015 and FR-017.
- **FR-037**: A contributor credited on nothing MUST render the page with a stated empty result, and a request for a contributor that does not exist MUST produce a not-found.
- **FR-038**: Two contributor records holding identical names MUST keep separate pages. The interface MUST NOT merge them or attempt to decide that two stored names are the same person.

**The boundary**

- **FR-027**: Every page MUST be read-only. Nothing in this feature may create, change, or delete a reference or any of its related records.
- **FR-028**: The pages MUST be reachable without authentication and the app MUST NOT impose a permission check of its own. Restricting access is the host's to do.
- **FR-029**: Text search, filtering, a choice of ordering, importing a file through the interface, editing anything, and a runnable demo project MUST NOT be delivered here. They belong to issues #47, #48, #49, #50 and #46. The contributor page is a browsing destination reached by following a name, not a filter over the catalogue, and it does not deliver any part of #49.
- **FR-030**: No admin-based management ships with the package (README), and this feature MUST NOT add any.
- **FR-031**: The vocabulary this feature introduces MUST be added to `CONTEXT.md` in the same change (Article VI): the *UI app* as the name for `literature.ui`, and the *catalogue* as the name for the set of stored items when spoken about from the interface.

### Requirement coverage

- **User Story 1** carries FR-012 through FR-018, and rests on FR-001, FR-003 and FR-008.
- **User Story 2** carries FR-019 through FR-026, and rests on the same three.
- **User Story 3** carries FR-002 and FR-006, and is what FR-001's separation exists for.
- **User Story 4** carries FR-032 through FR-038, and depends on FR-022 for the link that reaches it and on FR-013 for what its entries carry.
- **FR-004, FR-005, FR-007, FR-010 and FR-011** constrain the feature as a whole and every story's acceptance is judged against them.
- **FR-009** is a process requirement covering the run, verified by the presence or absence of entries under *Component gaps*.
- **FR-027 through FR-031** are boundary and documentation requirements, verified by inspection.

### Key Entities

This feature persists nothing and adds no model. The entities it introduces are surfaces:

- **UI app** (`literature.ui`): the opt-in Django app carrying the interface. Installed alongside the core, never required by it.
- **Catalogue list**: the page listing stored items, paginated, in the store's declared default order.
- **Reference page**: the page showing one item's whole record — its scalar fields, and its contributors, dates and identifiers.
- **Contributor page**: the page for one stored contributor, showing the name as held and the items they are credited on with the role they held on each.

### Component gaps

Empty at specification time. FR-009 requires that any component built locally because django-mvp has none is recorded here, with the upstream request it was filed under, so it can be removed when a django-mvp release carries the component.

One file stands in for something django-mvp does not yet ship, filed upstream as django-mvp#219:

- `literature/ui/templates/base.html` — a single `{% extends "mvp/base.html" %}` and nothing else.

django-mvp routes every packaged page through the unqualified `base.html`: `page_view.html` extends it, and `list_view.html` and `detail_view.html` extend that in turn. The name belongs to the host project and django-mvp ships no default for it, so without this file the packaged chain raises `TemplateDoesNotExist` in a project that has written none — and SC-002 rules out asking a host to write one. With it, the app's pages render through django-mvp's own view templates, which is the arrangement this feature wants: no page template of ours to drift from the package.

The stand-in is polite by construction, and two tests hold that line: it defines no block, so a project inherits nothing invisible from it, and a project's own `base.html` wins because a project's template directory is searched before any app's. It is deleted when django-mvp ships a default, which is what django-mvp#219 asks for. It defines no component.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project installing the package without the interface extra resolves no front-end dependency, and its use of the core is unchanged.
- **SC-002**: A project installing the extra, following the documented install steps and including the URLs reaches a working catalogue list and reference page without writing a view, a template, a URL pattern, or a line of styling. The install steps are documented in one place and are sufficient (see D8).
- **SC-003**: A catalogue of several thousand references renders its first page, and the rendered page does not grow with the catalogue's size.
- **SC-004**: A reader can tell two references apart from their list entries and reach either one's page in a single step.
- **SC-005**: For any stored item, every scalar field it carries appears on its page and no field it does not carry appears at all.
- **SC-006**: Contributors appear in the roles and order the catalogue stores, dates at the precision they were stored with, and identifiers with their type — so the pages report the store rather than reinterpreting it.
- **SC-007**: The app ships no stylesheet and defines no component of its own, or every exception is listed under *Component gaps* with the upstream request that will retire it.
- **SC-008**: Every one of the catalogue's item types renders on the catalogue list and the reference page, including an item carrying no contributors, no dates and no identifiers, and no reference produces an unhandled error.
- **SC-009**: The core's existing behaviour is unchanged: its test suite passes with the interface app absent.
- **SC-010**: A reader who recognises a name on a reference page reaches everything else that contributor is credited on in one step, without typing a query.
- **SC-011**: A contributor's page reports the roles the catalogue stores, so a person credited as an author on one item and an editor on another is shown as both, and an item they hold two roles on appears once.
- **SC-012**: A contributor credited on thousands of items opens no more slowly than one credited on a handful, and the rendered page does not grow with the count.

## Assumptions

- **The catalogue is populated by existing means.** Items arrive through the import paths delivered in R5 or through code. Nothing here creates data, and nothing here depends on how it got there.
- **The demo project is a separate feature.** Issue #46 builds it and depends on this one. Verification here does not wait for it and does not assume it.
- **django-mvp's component set is taken as it stands at its current release.** Whether it covers these two pages is settled during planning, not assumed here; FR-009 is what handles the answer being no.
- **Contributors are not de-duplicated.** Two stored names that look identical are two records, and the contributor page reports the store rather than reconciling it. Deciding when two names are one person is a problem of its own, and nothing here forecloses it.
- **Templates are resolvable by Django's standard mechanism**, so a host can override one, but this feature promises no override contract and defines no extension points. A stable theming surface is a separate question.
- **Access control is a later specification.** The pages are open, and a host restricts them at the point it includes the URLs.
- **The store's existing limits are inherited.** One identifier per type per item, one date per slot, batch-scoped citation-key de-duplication, and partial-date fallbacks all apply as they do today. The interface displays them and does not widen them.

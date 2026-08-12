# Feature Specification: A Runnable Demo That Serves the Front End Over Real References

**Feature Branch**: `007-runnable-demo-project`

**Created**: 2026-08-12

**Status**: Draft

**Serves**: G6 (a runnable demo project that exercises the app and guards against regressions) · Roadmap R6 · Issue #46

**Input**: Anyone evaluating the package, and anyone changing it, should be able to start a working project with one documented command and see the interface running over a catalogue of real references that covers a spread of item types, contributors, dates and identifiers. The same project doubles as a regression guard. A check on every change confirms the demo still starts and its pages still render, so an interface that has quietly broken gets caught before a release rather than by the next person who tries it.

## Clarifications

### Session 2026-08-12 — intake

- Q: The test suite already renders the front end's pages, but it does so under `tests/settings.py`, a second wiring maintained alongside the demo project's own. Is the guard's purpose that it exercises the *demo project's* settings, URL configuration and data loading end to end — catching a demo that has drifted from the package while every test stays green — or did you mean something broader that also stands in for the front-end tests? → A: The former. The guard's subject is the project an evaluator actually runs. It is an addition to the test suite, not a replacement for any part of it.
- Q: Is "a catalogue of real references" a small fixed curated set that ships in the repository and is loaded when the demo starts — genuine published works rather than generated filler, chosen to cover the item types and the shapes that make the pages interesting, on the order of twenty to thirty items and thereafter stable — or should the demo be populated at a scale where volume itself is part of what is shown? → A: The former. Fixed, curated, stable, so a page that changes appearance changed because the code changed.

### Session 2026-08-12 — clarification scan

Resolved from the intake session's context rather than escalated. Fuller rationale is in `decisions.md`.

- Q: The store carries 45 CSL item types, which a catalogue of twenty to thirty items cannot hold one of each. Does the seed catalogue have to cover every type? → A: No. It carries a representative range — the types a research literature collection actually contains — and coverage of all 45 stays where it already lives, in the test suite, which FS-006's SC-008 already requires to render every one of them. A demo that exists to be looked at is not the right place to assert an exhaustive matrix, and making it one would trade the curated set the intake session asked for against a checklist nobody reads.
- Q: Does "one documented command" include installing the project's dependencies? → A: No. Installing dependencies is the step a clone of any Python project already requires and the repository already documents. The promise begins after it: from there, ~~one command creates the database, loads the seed catalogue and serves the front end~~ *(refined 2026-08-12 — the composite command was removed at the maintainer's instruction; the documented path is `migrate`, `seed_demo`, `runserver`, see decisions.md D15)*, with nothing else to run and nothing else to read. The part this answer settles — that dependency installation is a precondition rather than part of the demo's own steps — is unchanged.
- Q: What must the guard actually confirm, given "its pages still render"? → A: That every page the front end serves is reached through the demo project's own URL configuration over the seeded catalogue, responds successfully, and carries content from the seed rather than an empty shell. A page that returns a success code while rendering nothing of the catalogue is a page that has broken in the way this guard exists to catch.
- Q: Does starting the demo require creating an account, and does the admin the demo already mounts stay? → A: No account, and yes it stays. The front end's pages are open, which FS-006 already settled, so browsing needs no sign-in and the documented start creates no user. The admin stays mounted as it is today for anyone who wants to poke at the data, and reaching it is not part of the documented path.
- Q: Does the repository keep a pre-built demo database? → A: No. The repository holds the reference data as source, and the start command builds the database from it. A committed database is a binary nobody can review, drifts from the migrations silently, and would make the seed catalogue two things that can disagree.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start the demo and browse real references (Priority: P1)

Someone has found the package and wants to know what it does before reading any of it. They clone the repository, install its dependencies the way the repository already documents, and follow three documented steps: build the database, load the catalogue, serve the site. They open the address and browse a populated catalogue — a list of references, a page for any one of them, a page for any contributor named on it. Each step is a stock Django command doing the obvious thing, and nothing beyond them is run or read.

**Why this priority**: It is the whole of what the issue asks for on the evaluation side, and every other story here depends on the demo existing. Delivered alone it replaces the only way to see the front end today, which is to build a project around it by hand.

**Independent Test**: From a fresh clone on a machine holding no prior state, follow the documented steps and confirm a served front end over a populated catalogue is reached by following them, with nothing to work out.

**Acceptance Scenarios**:

1. **Given** a fresh clone with dependencies installed and no database present, **When** the documented steps are run in order, **Then** the database is created, the seed catalogue is loaded, the server starts, and the catalogue list renders the seeded references.
2. **Given** the demo running, **When** a reader follows a reference from the list, **Then** that reference's page renders its record, and a contributor named on it leads to that contributor's page.
3. **Given** a demo whose database already exists and has been changed, **When** the seed step is run again, **Then** the catalogue returns to exactly the seeded state.
4. **Given** the demo running, **When** a reader browses any of its pages, **Then** nothing asks them to sign in and no account was created to start it.
5. **Given** someone reading the repository for the first time, **When** they look for how to run the demo, **Then** the steps and what to expect from them are documented in one place.

---

### User Story 2 - A catalogue worth looking at (Priority: P2)

The references the demo serves are genuine published works, chosen so that between them the pages have something to show. Item types spread across the kinds of thing a research collection actually holds. Some references carry a long list of contributors and some carry two, some name the same person as an author on one work and an editor on another, dates appear at the precisions the store keeps them at, and identifiers appear in more than one flavour with at least one that resolves. One reference is deliberately sparse, so the pages' behaviour with nothing to show is visible rather than theoretical.

**Why this priority**: It is what separates a demo from a screenshot of an empty table. The interface's whole claim is that it reports whatever the store holds, and that claim is unevidenced against three identical journal articles.

**Independent Test**: Load the seed catalogue into any project running the front end and confirm the spread — item types, contributor shapes, date precisions, identifier types, and a sparse reference — without starting the demo at all.

**Acceptance Scenarios**:

1. **Given** the seed catalogue loaded, **When** the catalogue list is opened, **Then** references of clearly different item types are visible and the list spans more than one page.
2. **Given** the seed catalogue loaded, **When** a reference with many contributors and one with few are opened, **Then** each shows its contributors in the roles and order stored.
3. **Given** a contributor credited on more than one reference, **When** their page is opened, **Then** every work they are credited on is listed with the role they held on each.
4. **Given** references carrying a year-only date, a full date and a date range, **When** each is opened, **Then** each date is shown at the precision stored.
5. **Given** a reference carrying identifiers of more than one type, **When** it is opened, **Then** each identifier is shown with its type and the resolvable one is followable.
6. **Given** the sparse reference, **When** it is opened, **Then** the page renders without the sections it has nothing for.

---

### User Story 3 - A broken demo is caught before anyone tries it (Priority: P3)

Someone changes the package, opens a pull request, and the change quietly breaks the demo — a setting the front end now needs and the demo project does not set, a URL name that moved, a seed file the loader no longer understands, a template that resolves in the test suite's wiring and not in a real project's. A check on the pull request starts the demo the way the documented command does, walks its pages, and fails. The break is a red check on the change that caused it rather than a discovery by the next person who clones the repository.

**Why this priority**: It is the half of the issue that outlives the demo's first week. A demo without it rots between releases, silently, which is the failure the issue names.

**Independent Test**: Introduce a change that breaks the demo project's wiring while leaving the test suite green, and confirm the check fails on that change.

**Acceptance Scenarios**:

1. **Given** a pull request against the repository, **When** its checks run, **Then** one of them starts the demo through the demo project's own settings and URL configuration, over the seed catalogue, and reports on the pull request.
2. **Given** a change that leaves the test suite passing but stops the demo starting, **When** the checks run, **Then** the demo check fails and names what failed.
3. **Given** a change that leaves the demo starting but stops one of its pages rendering, **When** the checks run, **Then** the demo check fails.
4. **Given** a change that leaves the demo starting but empties what its pages show, **When** the checks run, **Then** the demo check fails rather than passing on a successful response over an empty page.
5. **Given** a pull request touching nothing the demo depends on, **When** its checks run, **Then** the demo check still reports rather than being skipped.

---

### User Story 4 - The demo stays out of what is published (Priority: P4)

A project installing the package gets the package. The demo project, its settings, its seed catalogue and anything that exists only to run it are absent from what is published, and nothing the demo needs becomes something an installing project resolves. The demo is a thing the repository holds, not a thing the package ships.

**Why this priority**: It is a guarantee rather than a journey and delivers no visible value on its own, which is exactly why it is stated and verified separately. It is true today by construction and is the property most easily lost the moment the demo grows a dependency of its own.

**Independent Test**: Build the distribution and inspect it, and resolve the package in a clean environment, confirming no demo artifact and no demo-only dependency is present.

**Acceptance Scenarios**:

1. **Given** the built distribution, **When** its contents are inspected, **Then** the demo project and the seed catalogue are absent.
2. **Given** a clean environment, **When** the package is installed without the front-end extra, **Then** nothing that exists only for the demo is resolved and the core's behaviour is unchanged.

---

### Edge Cases

- The start command is run when a database already exists, is partially seeded, or was left behind by an older version of the seed catalogue. The demo returns to the seeded state rather than merging into whatever was there.
- The start command is run without the front-end extra installed. It says so plainly instead of failing somewhere inside Django's app loading.
- The seed catalogue is edited and the demo restarted. What is served matches the edited file, with no stale rows surviving from the previous load.
- A change touches only documentation. The demo check still reports on the pull request — a check that skips itself cannot be required, and a required check that never reports blocks every merge (the same reasoning already recorded in `tests.yml` for the test workflow's path filters).
- A page responds successfully but renders none of the catalogue. The guard treats this as a failure, not a pass.

## Requirements *(mandatory)*

### Functional Requirements

**The demo project and how it starts**

- **FR-001**: The repository MUST carry a demo project that installs the front end and serves it.
- **FR-002**: The demo project MUST wire the front end the way the repository documents a host project should wire it, so what it demonstrates is the documented install path rather than an arrangement peculiar to itself.
- **FR-003**: A documented sequence of stock Django commands MUST take a clone with dependencies installed to a served front end — applying migrations, loading the seed catalogue and starting the server — with no step left for the reader to work out and nothing beyond those commands to run. *(Refined 2026-08-12: was "one documented command", delivered as a `demo` management command wrapping the three. Removed at the maintainer's instruction — see decisions.md D15.)*
- **FR-004**: Running the seed step MUST return the demo to the seeded state whatever state it was in beforehand, including a database left behind by an earlier run.
- **FR-005**: Starting the demo MUST create no user account, and browsing its pages MUST require no sign-in.
- **FR-006**: The demo MUST serve every page the front end offers — the catalogue list, a reference's page and a contributor's page — each reachable by browsing from the address the command prints.
- **FR-007**: The demo MUST NOT depend on a database file kept in the repository. The reference data is the source of truth and the database is built from it.
- **FR-008**: The command, what it does and what the reader should expect to see MUST be documented in one place in the repository, alongside a plain statement that the demo is not a production configuration.

**The seed catalogue**

- **FR-009**: The repository MUST carry a fixed seed catalogue of genuine published references, versioned as source and readable in review.
- **FR-010**: The seed catalogue MUST span a representative range of CSL item types — the kinds a research literature collection actually holds — rather than repeating one type.
- **FR-011**: The seed catalogue MUST include a reference carrying many contributors and one carrying few, and at least one contributor credited on more than one reference, in more than one role across them.
- **FR-012**: The seed catalogue MUST include dates at more than one precision, including a year-only date, a full date and a date range.
- **FR-013**: The seed catalogue MUST include references carrying identifiers of more than one type, at least one of which addresses a resolvable location.
- **FR-014**: The seed catalogue MUST include one deliberately sparse reference, carrying no contributors, no dates and no identifiers, so the pages' behaviour with nothing to show is on display.
- **FR-015**: The seed catalogue MUST hold enough references for the catalogue list to paginate.
- **FR-016**: Loading the seed catalogue MUST be repeatable: loading it twice MUST leave the same catalogue rather than a doubled one.

**The guard**

- **FR-017**: A check MUST run on every pull request and on every change landing on the default branch, starting the demo through the demo project's own settings and URL configuration.
- **FR-018**: The check MUST load the seed catalogue and request every page the front end serves, confirming each responds successfully.
- **FR-019**: The check MUST confirm each page carries content from the seed catalogue, so a page that responds successfully while rendering nothing is a failure.
- **FR-020**: The check MUST fail, and name what failed, when the demo cannot start, when the seed catalogue cannot load, or when any page does not render as FR-018 and FR-019 require.
- **FR-021**: The check MUST exercise the demo project's own wiring. It MUST NOT reach for the test suite's settings module, its URL configuration, or its fixtures, since a guard that shares the wiring it is guarding proves nothing about the project an evaluator runs.
- **FR-022**: The check MUST report on every pull request rather than filtering itself out by the paths a change touches.

**Boundaries**

- **FR-023**: The published distribution MUST contain neither the demo project nor the seed catalogue.
- **FR-024**: The demo MUST add no runtime dependency to the package, and nothing existing only for the demo may be resolved by a project installing it.
- **FR-025**: The demo MUST demonstrate the front end as it stands. Creating and editing references (#47), managing contributors, dates and identifiers (#48), search and filtering (#49) and importing a file through the interface (#50) extend the demo as part of their own work and are out of scope here.

### Requirement coverage

- **User Story 1** carries FR-003 through FR-006 and FR-008, and rests on FR-001, FR-002 and FR-007.
- **User Story 2** carries FR-009 through FR-016, and is what US-1's pages are populated from.
- **User Story 3** carries FR-017 through FR-022, and depends on FR-002 for the wiring it exercises and on FR-016 for the data it walks.
- **User Story 4** carries FR-023 and FR-024.
- **FR-001, FR-002 and FR-025** constrain the feature as a whole and every story's acceptance is judged against them.
- **FR-008 and FR-025** are documentation and boundary requirements, verified by inspection.

### Key Entities

This feature persists nothing in the package and adds no model. The entities it introduces are project surfaces:

- **Demo project**: the runnable Django project in the repository that installs the front end and serves it, configured as the documentation tells a host to configure one.
- **Seed catalogue**: the fixed, curated set of genuine published references the repository carries as source and the demo loads at start.
- **Start command**: the single documented command that takes a clone with dependencies installed to a served front end over the seed catalogue.
- **Demo guard**: the check that runs on every change, starts the demo through its own wiring, and fails when it does not start or its pages do not render.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Someone who has never seen the repository reaches a served, populated catalogue from a fresh clone by following what is written down, with no step they had to work out for themselves.
- **SC-002**: The demo starts on a machine holding no prior state — no database, no account, no manual configuration.
- **SC-003**: Every page the front end serves is reachable by browsing from the demo's entry point, with no address typed by hand.
- **SC-004**: The seeded catalogue shows a spread on its face: references of clearly different item types, a contributor credited on more than one of them, dates at three precisions, identifiers of more than one type, and one reference with nothing but its own fields.
- **SC-005**: The catalogue list paginates on the seeded data, so the paging the front end ships is visible rather than inferred.
- **SC-006**: A change that stops the demo starting, or stops any of its pages rendering, fails a check on the pull request that introduces it, with nobody having run the demo by hand.
- **SC-007**: The guard catches at least one class of breakage the existing test suite cannot: a demo project whose own settings or URL configuration have drifted from what the front end needs, while every test stays green. Demonstrated by reinstating such a break and observing the guard fail and the suite pass.
- **SC-008**: Running the start command twice, from two different starting states, leaves the same catalogue both times.
- **SC-009**: The published distribution contains no demo project and no seed catalogue, and a project installing the package resolves nothing that exists only for the demo.
- **SC-010**: The demo's wiring and the documented install path agree, so following the documentation in a new project produces what the demo runs.

## Assumptions

- **The front end exists and is what the demo serves.** #45 delivered the catalogue list, the reference page and the contributor page, and they are the pages in scope. This feature adds no page and changes none.
- **Later R6 features extend the demo themselves.** Each of #47 through #50 adds its own surface to the demo and its own coverage to the guard as part of its own delivery. Nothing here is built in anticipation of them.
- **Installing dependencies is a precondition, not part of the command.** The repository already documents how, and the demo's one-command promise begins after it.
- **The seed references are chosen once.** Correcting a typo in one or adding a reference to widen the spread is ordinary maintenance, not a change of scope.
- **The demo is not a production configuration** and never claims to be — debug on, a local file database, a throwaway key. Its documentation says so.
- **Requiring the new check in the branch ruleset is a repository-settings action** outside the code this feature lands, and is the maintainer's to arm once the check is reporting.
- **Access control is out of scope.** The front end's pages are open, which #45 settled, and the demo inherits that.
- **The store's existing limits are inherited.** One identifier per type per item, one date per slot and the store's partial-date handling apply to the seed catalogue as they do to any other data.

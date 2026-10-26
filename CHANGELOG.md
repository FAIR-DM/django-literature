# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `ItemChoiceField` in `literature.ui.picker` lets a project's own form choose one reference by
  searching the catalogue, with a JSON search route, `literature:item-search`, behind it. See
  [How to choose a reference in your own form](docs/how-to/choosing-a-reference.md).
- `ItemMultipleChoiceField` in `literature.ui.picker` lets a project's own form choose several
  references the same way, for a plain form or a `ManyToManyField` to `Item`.
- `Item.get_absolute_url()` returns the reference's page in the catalogue, `literature:item-detail`.
  It resolves only where `literature.ui.urls` is mounted.
- `Item.doi`, `Item.doi_url` and `Item.year` give a reference's DOI, its `https://doi.org/` link and
  the year of its issued date, or `None`. They read prefetched `item_identifiers` and `item_dates`
  when a queryset has them.

### Changed

- **The catalogue's write pages require Django's model permissions.** Adding a reference and every
  import page require `literature.add_item`, editing requires `literature.change_item`, and
  deleting requires `literature.delete_item`. A visitor who is not signed in is sent to
  `LOGIN_URL`, and a signed-in user without the permission is refused. The Add, Import, Edit and
  Delete actions are shown only to users holding the permission behind them. Until now any visitor
  could add, change, delete and import references. Grant the permissions to the users or groups
  that maintain your catalogue. The read pages stay open.
- The demo's `seed_demo` creates an `editor.user` account, password `password`, which signs in
  through the admin and holds the three permissions.
- `doi_url` moved from `literature.ui.links` to `literature.utils.doi`, and
  `literature.ui.fields.issued_year` is removed in favour of `Item.year`.

## [v0.2.0] - 2026-10-25

### Changed

- **The add and edit form is laid out in four tabs.** Reference holds the type, citation key,
  title, the sections the chosen type uses, the dates, and the abstract and keywords. Contributors,
  Identifiers and More (notes, annotation, alternate titles, source and call number) follow. Every
  section is a collapsible panel. A form sent back with errors lists every error above the tabs,
  each linking to its field and opening the tab that holds it. Labels and help text are written for
  the person filling the form in, in place of the model's CSL notes, and the Container section is
  now headed "Published in", on the reference page too.
- **Contributors are entered one list per role.** Authors are always listed, the roles the item
  type usually credits are listed beside them, and "Show other roles" lists the rest. Rows move up
  and down with buttons instead of a position number, and an organisation, a name's particles and
  its suffix are entered in the row's name details.
- **Each date slot is a field of the form.** Submitted, Published, Available online, Event date,
  Originally published and Accessed each have a year, month and day control, shown when the item
  type uses the slot or the slot holds a date. Emptying one removes that date.
- **Keywords are entered as tags**, with every keyword the catalogue already uses offered for reuse.
  They are still stored as one comma-separated string.
- **The identifier type is a choice** of the six known types, and any other type can still be typed
  in and is stored as typed.
- `literature.ui.forms.ItemDateForm`, `literature.ui.inlines.ItemDateFormSet` and
  `literature.ui.inlines.DateInline` are removed, and `literature.ui.inlines.ContributorInline` is
  now the base of one set per role, `CONTRIBUTOR_INLINES`. `NameForm` no longer declares `role`.
- django-mvp 0.31.0 or later is required, for django-mvp-forms 0.8.0's collapsible fieldsets.

- **The reference page leads with the citation.** It opens with the type and year, the authors,
  any other contributors by role, and where the work was published. Below come the abstract,
  the identifiers and dates, then the remaining fields under the same headings as the edit form.
  The page is titled with the full title rather than one cut at 80 characters, and sits in
  django-mvp's medium page width. A DOI stored without its resolver now links to `doi.org`.
  `literature.ui.fields.scalar_fields` is replaced by `field_sections`, and the page's context
  carries `field_sections`, `byline` and `other_contributors` in place of `scalar_fields` and
  `contributor_groups`.

- **The front end needs django-mvp 0.30.1 or later.** The `ui` extra now asks for
  `django-mvp (>=0.30.1,<1.0)`. The catalogue's search and filters share one definition. On the
  table they sit together in the toolbar, and on the card list the filters open in a drawer from a
  Filters button. Applying a filter or moving to another page updates the list without reloading
  it. Forms render through
  django-mvp-forms in place of crispy-tailwind. A filter value that cannot be read, such as a year
  that is not a number, is now ignored for that filter alone, where it used to empty the list.

  **To upgrade a project that installs `django-literature[ui]`:**

  - Remove `crispy_tailwind` from `INSTALLED_APPS` and add `mvp_forms` after `crispy_forms`.
  - Add `daisy_cotton` directly after `mvp`.
  - Set `CRISPY_TEMPLATE_PACK = "daisyui"` and `CRISPY_ALLOWED_TEMPLATE_PACKS = ["daisyui"]`.
  - Run `pip install --upgrade "django-literature[ui]"`. `django-mvp-forms` and `daisy-cotton`
    arrive with django-mvp.
  - A project that subclasses `ItemListView` or `ItemTableView` sets `filterset_class` to its own
    filterset, since `search_fields` is gone. `literature.ui.filters.get_active_filters` is gone
    too: the views report the filters in force themselves.

  The README lists the full set of settings.

- The package is built with hatchling instead of poetry-core, and developed with uv instead of
  Poetry. The wheel contains the same files as before. The source distribution does too, plus the
  repository's `.gitignore`, which hatchling includes so that a build from it leaves out the same
  files.

### Fixed

- `import literature.ui` no longer raises `ImportError` on a fresh install of
  `django-literature[ui]`. The extra's floor allowed django-mvp releases that no longer export
  `MVPInlineCreateView`, so a new install resolved one of them (#133). The floor is now 0.30.1 and
  the reference form uses django-mvp's own create and update views.
- An RIS date written month/day/year, such as `Y2  - 1/26/2023`, is read as that date. It was read
  year first, as year 1, month 26, day 2023, and the entry failed to import (#105). A date tag
  whose numbers make no calendar date now falls back to the date's literal text, and a zero month
  or day is read as unstated.

### Added

- Django 6.1 is supported, and tested on every change alongside 5.2 and 6.0.

- **Importing a bibliography file through the front end.** The table catalogue carries an Import
  action at the end of its toolbar, after the filters, that opens a page to choose a configured
  format and attach a file. The card list has no Import action; a project serving it links to the
  `literature:item-import` route from its own navigation. Submitting it previews by default: the file is set aside and you land on a preview page at
  its own address, saying plainly that nothing has been imported yet and showing the report a real
  import would produce. It gives the counts — how many entries would be created, skipped and
  failed — and one row per entry in source order, numbered from one, each outcome a colour-coded
  badge, with a reason on every failure and on every skip, and a link to the reference a created
  row would produce. A row of buttons above the table narrows it to one outcome and back again
  without reloading the page or fetching anything, and the counts above those buttons go on
  describing the whole file however far the table is narrowed. The preview is worked out from the
  file afresh each time it is opened, so reloading it changes nothing and imports nothing.

  The preview ends with three controls: back to the catalogue, restart, and confirm. Restarting
  throws the file away and opens an empty import form. Confirming carries out the import and
  returns you to the catalogue with a message stating what was created, rather than to a result
  page of its own — the per-entry detail was on the preview you have just read. Where the chosen
  format could not read the file at all, nothing would be created by confirming, so the preview
  offers no confirmation and leaves only restart and the way back.

  A previewed file is held on disk only until it is confirmed, or swept automatically after 24
  hours if it never is. Its identity lives in the browser session rather than on the page, so a
  confirmation can only ever complete what that same session staged, and one whose staged file is
  already gone says so plainly and imports nothing. Reaching the preview address with nothing set
  aside says the same rather than showing an empty page.

  Ticking the skip-preview checkbox on the form imports in one step instead. That path lands on a
  report of what was imported, carrying the same counts and the same row per entry, and ending
  with a button back to the catalogue and a second that opens an empty import form.

  The format is chosen, never detected from the file. Nothing checks whether a file has already
  been imported, so importing the same file twice creates the references twice, and the page warns
  of this before you submit. A failure partway through the file leaves the entries already created in
  place. The page carries no permission check of its own and imposes no size limit of its own on
  the file it accepts, the same as every other page in the front end.

- **Searching and filtering the catalogue.** Both the table and the card presentation carry a
  search box and three filters — item type, issued year and language — reading from one shared
  definition, so a narrowed catalogue returns the same references whichever route serves it. On
  the table every filter sits in the toolbar beside the search box. On the card list they open in a
  drawer from a Filters button, at every screen width.

  Item type takes several types at once. Year offers the years the catalogue's issued dates fall
  in, newest first, and Language the language values the catalogue holds. The table leaves a filter
  out of its toolbar when the catalogue holds nothing for it to offer, such as Language when no
  reference records one. There is no contributor filter: the search box already finds a reference
  by any credited contributor's name, in any role.

  The search box matches a fragment, case-insensitively, against a reference's citation key, its
  title, short title and original title, the container it appeared in, and every credited
  contributor's name. It does not reach the abstract or the keywords: that text runs much longer,
  and searching it well needs different infrastructure than a fast, predictable lookup over a
  handful of short fields.

  Choosing more than one value within a single filter widens what it accepts; a search term and a
  filter, or two different filters, narrow further. A filter value that matches nothing, such as a
  year no reference was issued in, returns no results rather than falling back to the whole
  catalogue or raising an error.

  A search, every filter, the chosen sort and the current page all live in the address, so moving to
  another page, changing the sort, or bookmarking the address and reopening it later keeps every one
  of them in force.

  New runtime dependency, in the `ui` extra only: `django-filter`. A core-only install, or a project
  that has not opted into the front end, resolves neither it nor django-mvp.

### Fixed

- A chosen sort no longer resets when moving to another page of the catalogue. The pagination links
  used to replace the whole query string, dropping a sort along with everything else in it; the
  django-mvp version this release requires preserves it instead, closing
  [#88](https://github.com/FAIR-DM/django-literature/issues/88).

- BibTeX imports no longer fail on every file uploaded through a browser. `BibTeXFormat.parse`
  required a text handle and raised an internal `TypeError` on the bytes every upload actually is;
  it now decodes a binary handle itself, the way `RISFormat` already did, and `RISFormat` now
  accepts a text handle the same way in return — both formats accept either, closing
  [#104](https://github.com/FAIR-DM/django-literature/issues/104).

- **An ISSN's check digit is now verified, not just its shape.** An ISSN of the right
  `NNNN-NNNX` form but with a mistyped final character used to be stored as though it were
  sound; it is now checked against the standard's own modulo-11 checksum, the same way an
  ISBN's check digit already was, and a mismatch is told apart from a value that is the wrong
  shape entirely, closing [#118](https://github.com/FAIR-DM/django-literature/issues/118).

### Changed

- **A skipped entry in an import report may now show why.** A `@comment` or `@preamble` block in a
  BibTeX file, and header material or a reference-type-only record in an RIS file, each name what
  they were in the report's reason column — the same column a failed entry's reason already uses.
  Previously a skipped entry never carried a reason at all, however specific a cause the format
  actually had, and the report showed a row with no citation key and no explanation. A created entry
  still never carries one (issue #107).

- **The catalogue serves as a table by default.** `literature.ui`'s catalogue page used to be a list
  of cards; a project installing the front end with no configuration now gets a row per reference —
  citation key, item type, title, the journal or book it appeared in, its credited names and its
  issued date — with a sort on every column heading but the credited names. A row's title opens the
  reference's page, where it is edited. Paging, the page size, the empty state and the Add action are
  unchanged.

  The card presentation the package served before is still there, reachable the same way, and still
  what the contributor page's own configuration is drawn from. A project that prefers cards for its
  own catalogue restores the previous page with a settings key,
  `LITERATURE = {"CATALOGUE_VIEW": "literature.ui.views.ItemListView"}`, which also takes a project's
  own subclass of either view. Nothing is deprecated and nothing needs to be copied out of the
  package to do it.

  Sorting the table by item type orders by the type's stored value rather than by its translated
  label, since the label reads differently in every language the catalogue is served in and the order
  behind it should not.

  New runtime dependency, in the `ui` extra only: `django-tables2`. A core-only install, or a project
  that has not opted into the front end, resolves neither it nor django-mvp.

### Removed

- **`Item` no longer has the five fields a citation processor assigns**: `citation_label`,
  `citation_number`, `first_reference_note_number`, `locator` and `year_suffix`. They describe one
  citation in one document, not a reference. Migration `0004` drops the columns and the values they
  held. CSL JSON import no longer keeps `citation-label`, `citation-number`,
  `first-reference-note-number`, `locator` or `year-suffix`, and export no longer writes them, so a
  file carrying them comes back without them. The Processor-generated group is gone from
  `literature.ui.fieldgroups.GROUPS` and from the reference page.
- The one-line `base.html` `literature.ui` used to ship. django-mvp now ships a default of its own,
  which was the stated condition for dropping this one. A project with its own `base.html` is
  unaffected, and a project with none still gets a working shell.

## [v0.1.9] - 2026-08-14

### Changed

- **An imported citation key is stored exactly as it was given.** Importing a reference whose key
  the catalogue already held used to store it under a different key: `smith2020` became
  `smith2020b`, so the key someone had written in their manuscript was no longer the key on the
  record. Nothing rewrites a key now, and nothing warns about a collision. Two references may
  share a key, and keeping keys apart is the reader's business, as it is in every other reference
  manager.

  A key may now use the whole 255-character column. Ten characters used to be held back to leave
  room for a suffix, so a long key could be refused for want of space that nothing needed.

  Code reading `Item.objects.get(citation_key=...)` should move to `filter()`: a duplicate key was
  already possible through the interface's own forms, and is now possible through an import too.

### Added

- **Adding, editing and removing a reference through the front end.** `literature.ui` gains three
  pages, reachable from the catalogue list and a reference's own page: add a reference by hand,
  correct one, and remove one behind a confirmation that lists what goes with it.

  One form serves all three. It scopes itself to the chosen reference type: picking "Journal
  Article" reveals a different set of fields than picking "Map", with a toggle to show every field
  regardless. Nothing is ever lost by narrowing or widening that view: every field stays part of the
  form and keeps whatever value it already holds, whether or not its group is currently shown, and
  correcting one field leaves every other field exactly as it was. The type-to-field mapping behind
  this is the package's own, documented at `docs/field-groups.md`.

  These pages carry no permission check, the same as the read-only ones. Restricting them to
  particular users is left to the host project. Installing them needs `CRISPY_TEMPLATE_PACK =
  "tailwind"` and `CRISPY_ALLOWED_TEMPLATE_PACKS = ["tailwind"]` in settings, now documented in
  `README.md`'s install steps.

  The bundled demo exercises all three pages: `demo/smoke.py`, the script that walks the demo as a
  regression guard, now creates, corrects and removes a reference over HTTP as part of its walk.

- A standard contract for importing bibliographic files, at `literature.importers`. A `BibFormat`
  subclass supplies two stages — turning a file into entries, and expressing one entry as CSL
  JSON — and gets the rest of the workflow for free: `import_file(file, dry_run=False)` returns a
  report holding one outcome per entry the file contained. Every format is invoked the same way and
  returns the same shape, so a caller handles nothing specific to the file's syntax. The workflow's
  other steps (`import_entries`, `import_entry`, `get_result`) are ordinary, overridable methods, so
  a format with an unusual need may replace any of them deliberately.

  Importing is per entry. An entry that cannot be stored is reported individually with a reason and
  its position in the file, and the entries after it are still imported — one unreadable entry
  from 2011 no longer blocks a four-hundred-entry library. Each entry's fate is one of `created`,
  `skipped`, or `failed`, where *skipped* means the format recognised the element but it is not a
  bibliographic record. Nothing is dropped to a log message and left out of the report.

  An entry is atomic by default: it lands with its contributors, dates, and identifiers, or nothing
  from it is stored at all.

  `import_file(..., dry_run=True)` rehearses the whole thing. Every stage genuinely runs, so the
  outcomes are observed rather than predicted, and the catalogue is untouched when it finishes.

  Which formats an installation can read is declared in settings, under the namespaced `LITERATURE`
  key (`LITERATURE = {"BIB_FORMATS": ["path.to.Format", ...]}`), and the configured set can be
  enumerated through `available_formats()`, so code that accepts an uploaded file can list what
  this installation reads without knowing anything about the individual formats. Defaults to the
  formats this package ships, so the built-in behaviour needs no configuration.

  RIS follows, and adding a format means supplying a `BibFormat`
  subclass with a parser and a conversion to CSL JSON, then listing its dotted path in
  `LITERATURE["BIB_FORMATS"]` — the import workflow, the reported result, and the code that builds
  an `Item` all stay as they are.

- **Reading BibTeX files.** The first format behind that contract, shipped and enabled by default,
  so `get_format("bibtex")` works with no settings at all.

  One format reads both dialects: classic BibTeX, which publisher export links and academic
  databases emit, and BibLaTeX, which current Zotero and JabRef write. Someone exporting a library
  has no way to know which they were given, and a BibLaTeX file read as classic BibTeX would
  produce records with no journal and no date that still reported as created.

  It recovers before it refuses. A DOI carrying a resolver URL or a `doi:` label is normalized to
  the bare identifier, LaTeX-encoded text becomes the characters it represents, XML escaping left
  over from a publisher's pipeline is resolved, a language name becomes a language tag, and a date
  of the right shape but no calendar meaning is kept as written rather than failing its entry.
  `@string` macros are expanded and `crossref` inheritance is resolved, including a forward
  reference and including a cycle, which is reported rather than followed.

  Nothing a source entry states is thrown away. A field this package maps to no CSL variable — the
  `file`, `owner` and `timestamp` bookkeeping reference managers write into every export — is kept
  on the item under `custom["bibtex"]` and can be read back. This adds no new import outcome and no
  per-field reporting: an entry carrying unmapped fields is reported exactly like one without them.

  New runtime dependencies: `bibtexparser` (and its own `pyparsing`).

  `from_csl_json` and `from_csl_json_list` behave exactly as before for callers using them
  directly. The import contract calls the first of these and does not modify either.

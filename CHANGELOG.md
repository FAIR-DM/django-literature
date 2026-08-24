# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Importing a bibliography file through the front end.** The catalogue carries an Import
  action, on both presentations, that opens a page to choose a configured format and attach a
  file. Submitting it previews by default — the same report a real import would produce, with
  nothing yet written to the catalogue — and a control on that page carries out the import;
  ticking a checkbox on the form skips the preview for a one-step import instead. Either way you
  land on a report: how many entries were created, skipped and failed, and one row per entry in
  source order, numbered from one, each outcome shown as a colour-coded badge, with a reason on
  every failure and a link to the reference a created row produced.

  A previewed file is held on disk only until it is confirmed, or swept automatically after 24
  hours if it never is. Its identity lives in the browser session rather than on the page, so a
  confirmation can only ever complete what that same session staged, and one whose staged file is
  already gone says so plainly and imports nothing. The report page carries the upload form above
  its results, divided from them, so another file can be submitted without leaving the page, and
  ends with a button back to the catalogue and a second that opens an empty import form. Where the
  attached file could not be read at all, the form's submit control reads Retry and stays disabled
  until the attachment changes.

  The format is chosen, never detected from the file. Nothing checks whether a file has already
  been imported, so importing the same file twice creates the references twice, and the page warns
  of this before you submit. A failure partway through the file leaves the entries already created in
  place. The page carries no permission check of its own and imposes no size limit of its own on
  the file it accepts, the same as every other page in the front end.

- **Searching and filtering the catalogue.** Both the table and the card presentation carry a
  search box and four filters — item type, contributor, language, and issued year — reading from
  one shared definition, so a narrowed catalogue looks the same whichever route serves it.

  The search box matches a fragment, case-insensitively, against a reference's citation key, its
  title, short title and original title, the container it appeared in, and every credited
  contributor's name. It does not reach the abstract or the keywords: that text runs much longer,
  and searching it well needs different infrastructure than a fast, predictable lookup over a
  handful of short fields.

  Choosing more than one value within a single filter widens what it accepts; a search term and a
  filter, or two different filters, narrow further. An invalid or unmatched filter value returns no
  results rather than falling back to the whole catalogue or raising an error.

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
  issued date — with an edit control on every row and a sort on every column heading but the credited
  names and the edit control themselves. Paging, the page size, the empty state and the Add action are
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

# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
  formats this package ships — none yet — so the built-in behaviour needs no configuration.

  No format ships in this release. BibTeX and RIS follow, and adding one means supplying a `BibFormat`
  subclass with a parser and a conversion to CSL JSON, then listing its dotted path in
  `LITERATURE["BIB_FORMATS"]` — the import workflow, the reported result, and the code that builds
  an `Item` all stay as they are.

  `from_csl_json` and `from_csl_json_list` behave exactly as before for callers using them
  directly. The import contract calls the first of these and does not modify either.

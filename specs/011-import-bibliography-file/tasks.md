# Tasks — 011 Import a bibliography file through the front end

Test-first throughout (Article I): each task writes its failing test before the code that satisfies
it. Task ids are stable; phase order is the dispatch order.

**Legend** — `[P]` may run in parallel with its siblings once the phase's predecessors are done.

---

## Phase 0 — Foundational (sequential, blocks everything)

The two shipped formats disagree about whether a file handle is text or bytes, and a browser upload
is always bytes. See `research.md` R1, `decisions.md` D10 and issue #104.

- **T001** — `tests/test_importers/test_bibtex.py`: add `TestParseAcceptsEitherHandle`, asserting
  that a `.bib` fixture opened in binary produces the same entry results as the same fixture opened
  as text, and that a file of undecodable bytes reports a `ParseError` naming the encoding problem
  rather than a `TypeError`. Red first.
- **T002** — `literature/importers/bibtex.py`: `parse` decodes a bytes read with `utf-8-sig`,
  raising the same shaped `ParseError` as `RISFormat` on `UnicodeDecodeError`, and passes a text
  read through unchanged. Green T001.
- **T003** — `tests/test_importers/test_ris.py`: add `TestParseAcceptsEitherHandle`, the mirror of
  T001 — a `.ris` fixture opened as text produces the same results as the same fixture opened in
  binary. Red first.
- **T004** — `literature/importers/ris.py`: `parse` accepts a text read as well as a bytes read.
  Green T003.
- **T005** — `literature/importers/base.py`: `import_file`'s docstring states what a handle may be,
  replacing "an open file object, or anything with a `read()`". `tests/test_importers/test_base.py`
  gains an assertion that both handle types reach `parse` unchanged.
- **T006** — `CHANGELOG.md`: a fixed entry for the handle-type defect, citing issue #104.

**Phase exit:** `pytest tests/test_importers/` green, the whole suite green, no behaviour change for
any existing caller.

---

## Phase 1 — US-1: Import a file and see what became of every entry (P1)

Issue #100. Depends on Phase 0.

### The form

- **T101** — `tests/test_ui/test_forms.py`: `TestImportForm` — the format field offers exactly the
  configured formats and nothing else; the choices are built when the form is instantiated, so a
  format configured after import time still appears; both fields are required; a form submitted
  with neither is invalid with a reason on each; the form is multipart.
- **T102** — `literature/ui/forms.py`: `ImportForm(forms.Form)` with a `ChoiceField` whose choices
  come from `available_formats()` at `__init__` time and a `FileField`. Labels and help text through
  `gettext_lazy`. Green T101.

### The report adapter

- **T103** — `tests/test_ui/test_importing.py`: `TestImportReport` — one row per entry in source
  order; position is the entry's index plus one; outcome carried through unchanged; citation key
  present where the entry has a handle and absent where it does not; reason present only on
  failures; a created row carries the URL of its item and a non-created row carries none; the
  created, skipped and failed counts match the result's own.
- **T104** — `literature/ui/importing.py`: `ImportReportRow` (frozen dataclass) and `ImportReport`
  (wraps an `ImportResult`, exposes `rows`, `created`, `skipped`, `failed`, `total`). Green T103.

### The table

- **T105** — `tests/test_ui/test_tables.py`: `TestImportReportTable` — renders a list of rows with
  no queryset; every column present; the outcome cell renders the outcome's own translated label;
  a failure reason containing markup characters is escaped in the output; a created row's citation
  key links to the item and a failed row's does not.
- **T106** — `literature/ui/tables.py`: `ImportReportTable` over `ImportReportRow`, using
  django-mvp's table template. Green T105.

### The view and its route

- **T107** — `tests/test_ui/test_urls.py`: the import route reverses under the `literature`
  namespace and resolves to the import view.
- **T108** — `literature/ui/urls.py`: the import route, named for the model the way the others are.
  Green T107.
- **T109** — `tests/test_ui/test_views.py`: `TestItemImportView` — GET renders the form page with a
  format choice and a file control; a valid BibTeX upload creates the references and responds with
  the report page rather than a redirect; the response carries the counts and one row per entry in
  source order; a created row links to its reference; the same file uploaded as RIS behaves the
  same way for a `.ris` fixture; a file mixing entries that convert with one that does not reports
  each correctly and leaves the created ones in the catalogue; the report is not paginated.
- **T110** — `literature/ui/views.py`: `ItemImportView(MVPFormView)` with `model = Item`,
  `form_valid` resolving the format through `get_format`, calling `import_file` on the uploaded
  file, and rendering the report template with an `ImportReport` and an `ImportReportTable` in the
  context. Green T109.

### The templates

- **T111** — `tests/test_ui/test_templates.py`: the import form page carries a multipart form, a
  file control and the repeat-import warning; the report page carries the counts, the table and a
  link back to the catalogue; both pass the suite's existing i18n and utility-class guards.
- **T112** — `literature/ui/templates/literature/ui/import_form.html` extending `form_view.html`,
  and `import_report.html` extending the page layout, carrying the counts, the table and the way
  back. Every string translated. Green T111.

### The toolbar action on both presentations

- **T113** — `tests/test_ui/test_views.py`: `TestCatalogueImportAction` — the rendered table
  catalogue carries a link to the import route; the rendered card catalogue carries the same link;
  the contributor page carries none.
- **T114** — `literature/ui/views.py` and templates: `"import"` joins `CRUD_VIEWS`; `ItemListView`
  and `ItemTableView` each gain `"import"` in `directory` and `show_import_action = True`;
  `catalogue_actions.html` holds the action markup; `item_list_page.html` and `item_table_page.html`
  override `page.actions` and are set as `template_name` on the two views directly, never on
  `CatalogueListMixin`. Green T113.

**Phase exit:** `pytest tests/test_ui/` green, full suite green, story comment posted on #100.

---

## Phase 2 — US-2: Be told when the file cannot be used (P2)

Issue #101. Depends on Phase 1.

- **T201** — `tests/test_ui/test_views.py`: `TestItemImportViewRejects` — a submission with no file
  redisplays the form with a reason and imports nothing; the same with no format; an empty file, a
  file the chosen format cannot read, and a file of undecodable bytes each produce a page carrying
  the format's own reason rather than an exception; the catalogue is unchanged after each; no case
  returns a 500.
- **T202** — `literature/ui/views.py` and `forms.py`: whatever the tests in T201 show is missing —
  expected to be the empty-file path and confirming that `form_invalid` renders rather than
  redirects. Green T201.
- **T203** — `tests/test_ui/test_templates.py`: form errors render beside their fields on the import
  page, in the idiom the create page already uses.

**Phase exit:** `pytest tests/test_ui/` green, full suite green, story comment posted on #101.

---

## Phase 3 — US-3: The demo serves it, and a broken one is caught (P3)

Issue #102. Depends on Phase 2.

- **T301** — `demo/seed/import-sample.bib`: a small BibTeX file holding entries that convert and at
  least one that does not, so the walk exercises a failure row.
- **T302** — `tests/test_demo/test_smoke.py`: `TestMultipartEncoder` — the encoder produces a body
  and a content type Django parses back into the same fields and file; and `TestImportLinkPattern` —
  the import-link regex matches the anchor the catalogue really renders, asserted against markup
  from the test client, the way every other pattern in that module is asserted.
- **T303** — `demo/smoke.py`: a multipart encoder beside the existing urlencoded one, and the
  import-link regex. Green T302.
- **T304** — `demo/smoke.py`: `walk_import()` — from the already-fetched catalogue body, find the
  import action, follow it, read the form, submit the fixture, assert on where it landed and on the
  report's content (the created references present, the failing entry reported with a reason), then
  re-fetch the catalogue and assert the references arrived. Wired into `run()`.
- **T305** — verify the guard fails when it should: remove the toolbar action, then break the
  import, then empty the report, and confirm the walk fails each time with a reason naming what was
  missing. Restore.

**Phase exit:** the demo walk passes against a running demo; `pytest tests/test_demo/` green; story
comment posted on #102.

---

## Phase 4 — Documentation and close-out

Depends on Phase 3. Documentation ships in this PR (Article VI).

- **T401** — `docs/importing-through-the-interface.md`: the reader-facing walkthrough — reaching the
  page, choosing a format, what the report shows, that the format is chosen rather than detected,
  that a repeated import creates the references again, that entries created before a failure stay
  created, and that the import runs while the reader waits with the host's own upload and request
  limits bounding a large file. Added to the Getting Started toctree in `docs/index.md`.
- **T402** — `README.md`: an import section beside "Adding, editing and removing a reference",
  matching the depth of its neighbours.
- **T403** — `docs/api/ui.md`: `literature.ui.forms` and `literature.ui.importing` entries.
- **T404** — `docs/api/importers.md`: a line pointing at the front-end path, so a reader on the
  code-facing page learns the interface exists.
- **T405** — `CONTEXT.md`: *import report* defined as the front end's rendering of an import result
  (FR-037).
- **T406** — `CHANGELOG.md`: the feature entry.
- **T407** — run the humanizer over every public markdown this run authored or rewrote, and confirm
  no internal vocabulary reached any of it.

**Phase exit:** documentation gate green, full verify green.

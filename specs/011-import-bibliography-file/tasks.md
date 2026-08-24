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
- **T004** — `literature/importers/ris.py`: `RISParser.parse` (`ris.py:116-124`, where the decode
  lives — `RISFormat.parse` only delegates) accepts a text read as well as a bytes read. Green T003.
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
  no queryset; every column present; the outcome cell renders the outcome's own translated label,
  which is what keeps a failed entry distinguishable in place (FR-019); a failure reason containing
  markup characters is escaped in the output; **a created row's position number links to the item, a
  failed row's does not, and a created row whose entry carries no citation key still links** — the
  link hangs on the position, never on the key (`EntryResult.handle` is `None` by default and AS-10
  forbids inventing one); the citation key renders as plain text beside it.
- **T106** — `literature/ui/tables.py`: `ImportReportTable` over `ImportReportRow`, using
  django-mvp's table template, with the item URL on the position column. Green T105.

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
  `form_valid` resolving the format class through `get_format`, **instantiating it** —
  `get_format(name)().import_file(...)`, because `get_format` returns the class and `import_file` is
  an instance method — and rendering the report template with an `ImportReport` and an
  `ImportReportTable` in the context. Green T109.

### The templates

- **T111** — `tests/test_ui/test_templates.py`: the import form page carries a multipart form, a
  file control and the repeat-import warning; the report page carries the counts, the table and a
  link back to the catalogue, **and carries no form posting to the import route and no other control
  that would run the import again** — the surviving half of FR-023, which is an assertion of absence
  and so has to be written as one. Both pages pass the suite's existing i18n and utility-class
  guards — and widen that module's template glob so it also reaches the Cotton component directory.
  Today it globs `literature/ui/templates/literature/ui/*.html` only, so the new action component
  would be checked by neither guard.
- **T112** — `literature/ui/templates/literature/ui/import_form.html` extending `form_view.html`,
  and `import_report.html` extending the page layout, carrying the counts, the table and the way
  back. Every string translated. Green T111.

### The toolbar action on both presentations

- **T113** — `tests/test_ui/test_views.py`: `TestCatalogueImportAction` — the rendered table
  catalogue carries a link to the import route; the rendered card catalogue carries the same link;
  the contributor page carries none; **and both catalogues still render the search box, the filter
  control and the create action** — the card list reaches its action row by replacing the block that
  renders the whole row, so the regression this guards against is silent and shipped tests
  (`TestItemTableView::test_carries_search_and_filter_but_no_column_chooser`,
  `TestItemListView::test_the_add_link_renders_and_points_at_the_create_page`) are evidence about
  intent, never something to edit green.
- **T114** — `literature/ui/views.py` and templates: `"import"` joins `CRUD_VIEWS`; `ItemListView`
  and `ItemTableView` each gain `"import"` in `directory` and `show_import_action = True`; the action
  ships as `literature/ui/templates/cotton/page/list/actions/import.html`. The two presentations then
  diverge (`research.md` R2):
  - `ItemTableView` sets `actions = ["search", "filter", "create", "import"]` and gets no template.
    Update the existing assertion on that list, which is the one place a shipped test legitimately
    changes here.
  - `ItemListView` supplies `list_actions = ["search", "sort", "filter", "create", "import"]` to its
    context and sets `item_list_page.html` as `template_name` **directly, never on
    `CatalogueListMixin`**; that wrapper overrides `page.actions` with
    `<c-page.list.actions :actions="list_actions" />`. The packaged default must be carried through,
    not replaced by the import link alone.

  Also refresh the docstring on
  `tests/test_ui/test_templates.py::TestPackagedChain::test_no_page_template_of_our_own_stands_in_for_a_packaged_one`,
  which says neither catalogue has a template here. The assertion still holds — it names `base.html`,
  `item_list.html` and `contributor_detail.html` — but the docstring needs a line distinguishing a
  wrapper that *extends* a packaged template from one that stands in for it.

  Green T113.

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
  least one that does not, so the walk exercises a failure row. Its entries must carry no citation
  key, title, item type or language that the narrowing assertions at `demo/smoke.py:218-256` name —
  those are exact-membership assertions over the whole catalogue, and an imported reference sharing
  a seeded value makes them fail for a reason that has nothing to do with importing.
- **T302** — `tests/test_demo/test_smoke.py`: `TestMultipartEncoder` — the encoder produces a body
  and a content type Django parses back into the same fields and file; and `TestImportLinkPattern` —
  the import-link regex matches the anchor the catalogue really renders, asserted against markup
  from the test client, the way every other pattern in that module is asserted.
- **T303** — `demo/smoke.py`: a multipart encoder beside the existing urlencoded one, and the
  import-link regex. Green T302.
- **T304** — `demo/smoke.py`: `walk_import()` — from the already-fetched catalogue body, find the
  import action, follow it, read the form, submit the fixture, assert on where it landed and on the
  report's content (the created references present, the failing entry reported with a reason), then
  re-fetch the catalogue and assert the references arrived. Wired into `run()` **last**, after
  `walk_narrowed_catalogue()` and `walk_write_pass()`: unlike the write pass it leaves its references
  behind, and on a developer's persistent demo database that accumulates across runs.
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
  limits bounding a large file. It must also say plainly that **the import page carries no permission
  check of its own** — it is reachable by anyone who can reach the catalogue, and a host that needs
  it restricted restricts it at its own routing (D12). Added to the Getting Started toctree in
  `docs/index.md`.
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

**Phase exit:** documentation gate green, full verify green, and `makemigrations --check` across
every app confirms the run ships no migration (SC-007), which nothing local otherwise asserts.

---

# Refinement, 2026-08-24

Everything above landed. What follows is the cascade from the specification amendment — see the
`**Refined**` note in `spec.md` and decisions D16–D18. Phases run in order; Phase 5 is the largest
and the other three sit on it.

---

## Phase 5 — US-4: Preview an import before it happens (P1)

Issue #108. FR-038 to FR-044, plus the amended FR-035.

### Staging

- **T501** — `tests/test_ui/test_staging.py`: `TestStagedUpload` — saving a file returns a token and
  writes the bytes where they can be read back; reading with a token this session did not issue
  returns nothing; a staged file is removed on discard; a staged file older than the retention
  window is swept and a fresh one is not; a token is not derivable from the file's contents or name.
- **T502** — `literature/ui/staging.py`: `StagedUpload` — a class holding save / open / discard /
  sweep over a directory obtained from Django's storage API, with a random token as the stored name
  and the retention window a module constant. No new dependency. Green T501.

### The two-step view

- **T503** — `tests/test_ui/test_forms.py`: `TestImportForm` gains the skip control — present,
  unticked by default, labelled; and `TestConfirmImportForm` — carries no file field and no token
  field, because the token comes from the session (FR-042).
- **T504** — `literature/ui/forms.py`: the skip-preview `BooleanField` (`required=False`,
  `initial=False`) and, if the confirmation needs a form at all, one carrying nothing the page can
  set. Green T503.
- **T505** — `tests/test_ui/test_views.py`: `TestItemImportPreview` — a default submission imports
  nothing and the catalogue is unchanged; the response reports every entry as a real import would;
  the response states nothing was imported and carries a confirm control; the session holds the
  staged token and format; the page does not contain the token.
- **T506** — `tests/test_ui/test_views.py`: `TestItemImportConfirm` — confirming imports the staged
  file and the created entries match what the preview reported; the reader is not asked for the file
  again; the staged file is gone afterwards; a confirmation from a session that staged nothing
  imports nothing and says so; a confirmation whose staged file has been swept says so and imports
  nothing; a second confirmation of the same token imports nothing.
- **T507** — `literature/ui/views.py`: `form_valid` stages the upload, runs `import_file(...,
  dry_run=True)` and renders the preview; a confirm route reads the token and format from the
  session, re-opens the staged file, runs the real import, discards the staging and renders the
  report. Sweep stale stagings on entry to the import view. Green T505/T506.
- **T508** — `tests/test_ui/test_views.py`: `TestItemImportSkipPreview` — ticking the skip control
  imports in one step, reports what was imported rather than what would be, and stages nothing.
- **T509** — `literature/ui/views.py`: the skip branch. Green T508.

### Presentation and the guard

- **T510** — `tests/test_ui/test_templates.py`: the preview page is labelled as a preview, says
  nothing was imported, carries the confirm control, and carries no token; the report page after a
  real import carries no confirm control.
- **T511** — `literature/ui/templates/literature/ui/`: the preview state of the report page. Every
  string translated.
- **T512** — `tests/test_demo/test_smoke.py`: the confirm-control pattern matches the markup the
  preview really renders.
- **T513** — `demo/smoke.py`: `walk_import()` submits, reads the preview, asserts the catalogue is
  still unchanged at that point, confirms, then asserts the references arrived. Green T512.
- **T514** — verify the guard fails when it should: break the preview, then the confirmation, and
  confirm the walk fails each time naming what was missing. Restore.

**Phase exit:** full suite green, `forge verify` green, story comment on #108.

---

## Phase 6 — US-5: Read why an entry was skipped (P2)

Issue #109, contract change tracked as #107. FR-018, amended FR-028.

- **T601** — `tests/test_importers/test_results.py`: a skipped entry may carry a reason and one
  without a reason is still valid; a created entry carrying a reason still raises; a failed entry
  without one still raises.
- **T602** — `literature/importers/results.py`: relax `EntryResult.__post_init__` for the skipped
  outcome only. Green T601.
- **T603** — `tests/test_importers/test_bibtex.py`: a `@comment` and a `@preamble` block each report
  skipped with a reason naming what it was.
- **T604** — `tests/test_importers/test_ris.py`: header material before the first record, and a
  record whose only tag is `TY`, each report skipped with a reason naming what it was.
- **T605** — `literature/importers/`: both formats pass a reason when they raise `SkipEntry`, and the
  runner carries it onto the result. Green T603/T604.
- **T606** — `tests/test_ui/test_tables.py` and `test_importing.py`: a skipped row shows its reason
  in the column a failure's reason uses.
- **T607** — `literature/ui/`: the report renders it. Green T606.
- **T608** — `docs/adr/`: a decision record for a reason on a skipped entry, superseding nothing but
  citing the contract it amends. `CHANGELOG.md` entry citing #107.

**Phase exit:** full suite green, story comment on #109.

---

## Phase 7 — US-1 refinement: what the report looks like (P1)

Issue #100. FR-011a, FR-015, FR-021, FR-023a. Decisions D17.

- **T701** — `tests/test_ui/test_tables.py`: the outcome cell renders a badge, and the three
  outcomes render three distinct variants — asserted on the variant, never on a colour name.
- **T702** — `literature/ui/tables.py`: the outcome column renders django-mvp's badge component.
  Green T701.
- **T703** — `tests/test_ui/test_templates.py`: the report page carries the import form above the
  results with a divider between them; a back-to-catalogue button carrying a backward arrow; a
  second button leading to an empty import form; and where the file could not be read, a submit
  control reading *Retry* that is disabled until the attached file changes.
- **T704** — `literature/ui/templates/literature/ui/`: the report page layout. The Retry state is
  Alpine on the file input, in the idiom the package already uses. Green T703.
- **T705** — re-run the module's i18n and utility-class guards over every template this phase
  touched.

**Phase exit:** full suite green.

---

## Phase 8 — Documentation of the refinement

- **T801** — `docs/importing-through-the-interface.md`: the preview step, how to skip it, that a
  staged file is held only until it is confirmed or swept, and that a skipped entry now says why.
- **T802** — `README.md` import section: the preview, in a sentence.
- **T803** — `docs/api/ui.md`: the staging module.
- **T804** — `CONTEXT.md`: *preview* and *staged file*, if the glossary's own test says they are
  terms this package now uses.
- **T805** — `CHANGELOG.md`: one entry for the refinement.
- **T806** — the humanizer pass over every public markdown this refinement authored or rewrote, and
  a check that no internal vocabulary reached any of it.

**Phase exit:** documentation gate green, `forge verify` green.

---

# Second refinement, 2026-08-24

The preview becomes a page in its own right, and a carried-out import returns the reader to the
catalogue. See the second `**Refined**` note in `spec.md`, FR-045 to FR-055, and `decisions.md` D30
as amended by D31 and D32.

---

## Phase 9 — US-6: The preview is a page, not a response (P1)

Issue #110. FR-045 to FR-055.

### The outcome filter component

- **T901** — `tests/test_ui/test_templates.py`: `TestOutcomeFilter` — the component renders one
  control per outcome plus a way back to all of them; each control names its outcome in translated
  text; it carries no form action and no link, because it never issues a request. Also that the
  counts rendered above the table are the whole file's and are not written by the filter (FR-049a).
- **T902** — `literature/ui/templates/cotton/filter.html`: a Cotton component in daisyUI's filter
  idiom, shipped here because django-mvp does not define one. Narrowing is client-side over rows
  already on the page, in the same JavaScript idiom the package already uses. No new dependency.
  Green T901.

### The preview page

- **T903** — `tests/test_ui/test_urls.py`: the preview route reverses under the `literature`
  namespace and resolves to its view.
- **T904** — `literature/ui/urls.py`: `import/preview/`. Green T903.
- **T905** — `tests/test_ui/test_views.py`: `TestItemImportPreviewPage` — submitting the import form
  redirects to the preview address; a GET of that address rebuilds the preview from the staged file
  and imports nothing; reloading it changes nothing; reaching it with nothing staged says so and
  does not raise.
- **T906** — `literature/ui/views.py`: the import form's valid branch stages, then redirects. The
  preview view rebuilds the report from the staged file on GET. Green T905.
- **T907** — `tests/test_ui/test_templates.py`: `TestImportPreviewTemplate` — the page carries no
  import form; it is titled for what it is with a description beneath; a warning appears above the
  table when any entry was skipped or failed and does not when none was; the filter component is
  present above the table; the foot carries exactly three controls in one row.
- **T908** — `literature/ui/templates/literature/ui/import_preview.html`: the page. Every string
  translated. Green T907.

### Restart and confirm

- **T909** — `tests/test_ui/test_views.py`: `TestItemImportRestart` — restarting discards the staged
  file and lands on an empty import form; restarting with nothing staged still lands there.
- **T910** — `literature/ui/views.py` and `urls.py`: the restart route. Green T909.
- **T911** — `tests/test_ui/test_views.py`: `TestItemImportConfirm` — confirming redirects to the
  catalogue rather than rendering; the message it leaves behind states what was created; the staged
  file is gone by then; following the redirect renders that message once.
- **T912** — `literature/ui/views.py`: the confirm branch imports, leaves its counts as a message
  through the framework the interface already renders, and redirects to the catalogue. Green T911.
  *There is no success page and no success address — D31.*
- **T913** — *removed by D31 with the success page.*
- **T914** — *removed by D31 with the success page.*

### The breadcrumb, and what the reshape leaves behind

- **T915** — `tests/test_ui/test_views.py`: `TestCatalogueBreadcrumb` — on the import form, the
  preview and the create page, the step back to the catalogue is a link and reads the catalogue's
  own title rather than the model's plural name.
- **T916** — `literature/ui/views.py`: `show_list_action` and `list_view_title` set wherever either
  is missing. Green T915. *The create page has the mirror of the reported defect — it links but
  reads the model's plural name — so both halves are fixed here.*
- **T917** — remove what the reshape orphans: the form-above-the-results layout and its *Retry*
  state (FR-011a and FR-023a, both reversed), and any test asserting them. These are this run's own
  tests from Phase 7, not shipped ones, and removing them is the point of the reversal — but check
  each against the spec before deleting, and leave anything still required standing.
- **T918** — `demo/smoke.py` and `tests/test_demo/test_smoke.py`: the walk follows the redirect to
  the preview, reads it, confirms, follows the redirect to the catalogue and reads the message
  waiting there. Then break the preview, the restart and the confirm in turn and confirm the walk
  fails each time.

**Phase exit:** full suite green, `forge verify` green, story comment on #110.

---

## Phase 10 — Documentation of the second refinement

- **T1001** — `docs/importing-through-the-interface.md`: the preview page, the three controls, the
  outcome filter, that restarting discards the staged file, and that confirming returns to the
  catalogue.
- **T1002** — `docs/api/ui.md` and `CHANGELOG.md`.
- **T1003** — the humanizer pass over what this phase authored, and a check that no internal
  vocabulary reached any of it.

**Phase exit:** documentation gate green.

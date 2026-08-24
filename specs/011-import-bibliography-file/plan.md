# Implementation Plan: Import a Bibliography File Through the Front End

**Branch**: `011-import-bibliography-file` | **Date**: 2026-08-24 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `specs/011-import-bibliography-file/spec.md`

## Summary

Add an import path to `literature.ui`: a toolbar action on both catalogue presentations leads to a
page carrying a format choice and a file input; submitting it runs the file through the package's
existing import contract and renders an import report of every entry.

The front end is thin. Everything the report needs is already returned by `ImportResult` /
`EntryResult`, so the work is a form, a view, two templates, a table and a toolbar seam — plus one
foundational core fix, because the two shipped formats currently disagree about whether
`import_file` takes a text or a binary handle and a browser upload is always binary (`research.md`
R1). That fix comes first; nothing downstream works without it.

## Technical Context

**Language/Version**: Python 3.13 (package floor 3.12), Django 5.1/5.2

**Primary Dependencies**: django-mvp 0.19.1 (through the `ui` extra, never the core), django-tables2,
django-filter, crispy-forms + crispy-tailwind, django-cotton. No new dependency.

**Storage**: none added. No model, no field, no migration.

**Testing**: pytest + pytest-django, settings module `tests.settings`; `factory_boy` factories in
`tests/factories.py`; the demo walked by `demo/smoke.py` over real HTTP in CI.

**Target Platform**: server-rendered Django, embedded in a host project.

**Project Type**: reusable Django package with an opt-in front-end app and a demo project.

**Performance Goals**: none stated, and none claimed. The import runs in the request, so a large
file blocks for as long as it takes; the documentation says so rather than the package inventing a
bound.

**Constraints**: the core resolves no front-end dependency (Article X and the architecture
constraints); every user-facing string translatable (Article VIII); test modules mirror the source
tree with class grouping (Article XIV); new lines ≥85% covered, package ≥90% (`codecov.yml`).

**Scale/Scope**: one form, one view, two templates, one table, one presentation module, two
four-line layout wrappers, one core fix, one demo fixture and one demo walk step.

## Constitution Check

*Re-checked after the design below was settled.*

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I — Test-First | Every behaviour here is testable through the `client` fixture and the importer's own result. | Tasks are written test-first; the demo walk step is written against a fixture whose failures are known. |
| II — Simplicity | The temptation is an import framework — a pluggable report renderer, a progress channel, an upload registry. | None of it is built. One form, one view, one table. |
| III — Anti-Abstraction | The report needs a presentation row, which is one frozen dataclass over `EntryResult`, not a layer. | Pass. No base class, no registry. |
| V — Security & data-safety | First file upload in the project. Untrusted bytes, a failure reason rendered into a page, and a chosen format name arriving from a POST. | Reason rendered through the template layer so markup in it is escaped (FR-022); the format name resolved through `get_format`, which raises `UnknownFormat` for anything not configured, so the choice cannot select arbitrary code; the file never written to a path the package builds. |
| VI — Documentation | Public surface changes: a new URL name, a new form, a new setting-free behaviour. | README section, `docs/` page, CHANGELOG entry and docstrings all in this PR. |
| VII — Dependency discipline | Nothing new is needed — django-tables2 and the upload machinery are already present. | Pass, `deptry` unaffected. |
| VIII — i18n (non-negotiable) | Every label, every outcome word, every error, every button. | `gettext_lazy` in Python, `{% translate %}` in templates. The outcome words come from the existing `Outcome` text choices, already translated. |
| X — Embeddable package | Nothing may require the host to change structure. | Rules out the session-backed report (`research.md` R6). URL stays namespaced and optional. |
| XII — Living demo | The demo must show the feature and guard it. | US-3 is exactly this. |
| XIII / XIV / XV | Data-model conventions do not bite (no model). Test layout mirrors, grouped in classes. Related behaviour grouped in a class rather than loose functions. | The report adapter is a class, not four module functions. |

**No violations to track.** The one thing that reads like a violation — a core change inside a
front-end feature — is a defect fix that the feature cannot proceed without, recorded as D10 and
raised on the tracker in its own right.

## Project Structure

### Documentation (this feature)

```text
specs/011-import-bibliography-file/
├── spec.md
├── decisions.md
├── research.md
├── plan.md
├── progress.md
└── tasks.md
```

No `data-model.md` (no model changes), no `contracts/` (no new API surface beyond one namespaced
URL), no `quickstart.md` (the README and docs pages carry the reader-facing walkthrough).

### Source code

```text
literature/
├── importers/
│   ├── base.py                 # docstring: what a handle may be
│   ├── bibtex.py               # decode bytes, matching RIS and ADR 0012
│   └── ris.py                  # tolerate text as well as bytes
└── ui/
    ├── forms.py                # + ImportForm
    ├── importing.py            # NEW — ImportReport, the presentation adapter
    ├── tables.py               # + ImportReportTable
    ├── urls.py                 # + import route
    ├── views.py                # + ItemImportView; import action on both catalogue views
    └── templates/literature/ui/
        ├── catalogue_actions.html    # NEW — the shared action row
        ├── item_list_page.html       # NEW — card list, action row
        ├── item_table_page.html      # NEW — table, action row
        ├── import_form.html          # NEW
        └── import_report.html        # NEW

demo/
├── seed/import-sample.bib      # NEW — entries that convert, and one that does not
└── smoke.py                    # + multipart encoder, + the import walk

tests/
├── test_importers/{test_base,test_bibtex,test_ris}.py
├── test_ui/{test_forms,test_importing,test_tables,test_urls,test_views,test_templates}.py
└── test_demo/test_smoke.py

docs/importing-through-the-interface.md   # NEW, in the Getting Started toctree
README.md · CHANGELOG.md · docs/index.md · docs/api/ui.md
```

**Structure decision.** The front-end work stays inside `literature/ui/` and follows what is already
there: forms in `forms.py`, views in `views.py`, tables in `tables.py`, templates flat under
`literature/ui/`. One new module, `importing.py`, holds the adapter between the import result and
the page — justified the way `tables.py` justifies itself, as something that is neither a view nor a
form, and by Article XV, which wants the row-building grouped on a class rather than scattered.

### The three seams worth naming before implementation

1. **The toolbar.** `"import"` joins `CRUD_VIEWS`; both `ItemListView` and `ItemTableView` gain
   `"import"` in `directory` and `show_import_action = True`, so `directory.import_url` resolves
   through django-mvp's own mechanism. Rendering is a `page.actions` block override: one partial
   (`catalogue_actions.html`) included by two wrappers, one extending `list_view.html` and one
   extending `table_view.html`, set as `template_name` on the two views **directly, never on
   `CatalogueListMixin`** — the mixin also serves the contributor page, which stays as it is.

2. **The view.** `ItemImportView(MVPFormView)` with `model = Item` (`research.md` R3),
   `form_class = ImportForm`. `form_valid` resolves the format with `get_format`, calls
   `import_file(request.FILES[...])`, and renders the report template with an `ImportReport` in the
   context. It does not redirect and does not touch `success_url`.

3. **The report.** `ImportReport` wraps an `ImportResult` and yields one row per entry carrying
   position (index + 1), outcome, citation key, reason and the created item's URL. `ImportReportTable`
   renders those rows through django-mvp's table template. The counts come off `ImportResult`'s own
   `created` / `skipped` / `failed` properties.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| A core change (both formats accept either handle) inside a front-end feature | A browser upload is bytes; BibTeX currently fails every one of them with an internal type error reported as an entry failure. The feature cannot work without it. | Decoding in the view was rejected: it puts a per-format handle table in the front end, contradicts ADR 0012 and FR-010, and breaks for any third format a project configures. |
| Three new template files for one toolbar action | django-mvp offers no way for a view to add an action to its own toolbar, and the two catalogue layouts do not share a template. | Shadowing django-mvp's action component was rejected: `literature.ui` is installed after `mvp`, so the shadow never resolves from inside this package. Duplicating the markup in two wrappers was rejected for the obvious reason. |

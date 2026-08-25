# Research — 011 Import a bibliography file through the front end

Findings gathered before planning, each one read out of the source rather than assumed. Every
entry states what was checked, what was found, and what the plan does about it.

## R1 — The two configured formats disagree about what `import_file` accepts

**Checked:** `literature/importers/base.py:117-135` (the documented entry point), `bibtex.py:696`,
`ris.py:115-119`, and both format's tests.

**Found:** the base class documents the argument as "an open file object, or anything with a
`read()`", and the two shipped formats mean different things by it.

- `RISFormat.parse` calls `raw.decode("utf-8-sig")`, so it requires a **binary** handle. Its tests
  open fixtures with `open("rb")` (`tests/test_importers/test_ris.py:43`).
- `BibTeXFormat.parse` calls `text.strip()` and matches a `str` pattern against it, so it requires a
  **text** handle. Its tests open fixtures with `open(encoding="utf-8")`
  (`tests/test_importers/test_bibtex.py:37`).

Confirmed by running both formats against both handle types. Neither raises to the caller, because
the runner catches everything — each returns a report of one failed entry whose reason is an
internal type error:

| Format | Handle | Result |
|---|---|---|
| BibTeX | binary | `TypeError: cannot use a string pattern on a bytes-like object` |
| BibTeX | text | parses |
| RIS | binary | parses |
| RIS | text | `AttributeError: 'str' object has no attribute 'decode'` |

**Why it blocks this feature:** a file arriving from a browser is bytes. Django hands a view an
`UploadedFile` whose `read()` returns bytes, always. So the import path works for RIS and fails for
every BibTeX file, with a reason that names a Python type error rather than anything the reader
did — the exact failure the report exists to prevent.

**Why the front end must not paper over it:** the alternative is for the view to decode for BibTeX
and not for RIS, which means the front end holding a table of which format wants which handle. That
contradicts ADR 0012 (the format owns decoding), contradicts FR-010 (no separate reading path in the
front end), and breaks the moment a project configures a third format — which FR-005 explicitly
supports.

**What the plan does:** a foundational task makes both formats accept either handle, decoding bytes
themselves, before any front-end work begins. RIS already owns its decoding and only needs to
tolerate text; BibTeX gains the decoding step RIS already has, including the same `ParseError` on
undecodable bytes. The base class's docstring stops saying "a file object" and says what is actually
accepted. This is a core change inside a front-end feature and is called out as such — see D10 in
`decisions.md`, and it is raised on the tracker in its own right so the defect has a record
independent of this feature.

## R2 — The table view has an actions hook; the card list does not

**Checked:** the django-mvp 0.19.1 copy this project actually resolves —
`<venv>/lib/python3.14/site-packages/mvp`, `django_mvp-0.19.1.dist-info`, confirmed with
`poetry run python -c "import mvp; print(mvp.__path__)"`. A separate working checkout at
`/home/sam/projects/django-mvp/` carries the same version number and different code. It is not what
this project runs, and reading it instead is what an earlier pass of this section got wrong.

**Found:** the two catalogue layouts differ, and only one of them lacks a hook.

- **Table.** `MVPTableViewMixin` declares `actions = ["search", "filter", "create"]` and publishes it
  as `context["table_actions"]` (`mvp/integrations/django_tables/views.py:43,108`);
  `mvp/templates/table_view.html:76-78` renders `<c-page.list.actions :actions="table_actions" />`.
  A table view adds an action by naming it on the class. This repo already depends on that hook —
  `tests/test_ui/test_views.py::TestItemTableView` asserts the exact list.
- **Card list.** `mvp/templates/list_view.html:3-5` renders `<c-page.list.actions />` with no
  attribute, so the row falls back to the component's own `c-vars` default of
  `['search','sort','filter','create']`, and no list mixin declares an `actions` attribute. A
  `c-vars` default shadows a context variable of the same name, so the only way in is to pass the
  list as an attribute — which means overriding the block that renders the component.

`cotton/page/list/actions/index.html` iterates the list as
`<c-component is="page.list.actions.{{ action_item }}" />`, and the shipped component directory holds
only `create`, `filter`, `index`, `search`, `share` and `sort`. `page.list.actions.import` is a name
django-mvp does not define, so supplying it from this package **adds** a component rather than
shadowing one, and the `INSTALLED_APPS`-order problem that would sink a shadow does not arise.

`CRUDDirectoryMixin` (`mvp/views/detail.py:101-163`) resolves the URL half: a custom action added to
`directory` stays hidden until the view sets `show_<name>_action`.

**What the plan does:** carries the URL through `CRUD_VIEWS` / `directory` / `show_import_action` on
both catalogue views, ships one component at
`literature/ui/templates/cotton/page/list/actions/import.html`, and reaches it two ways — the table
view names `"import"` in its own `actions`, and the card list gets a `page.actions` block override
rendering `<c-page.list.actions :actions="list_actions" />` against a view-supplied list. The
override must render the whole row: the block it replaces is the sole renderer of search, sort,
filter and create, so an override emitting only the import link would strip them.

The gap is raised upstream, narrowly — a *list* view has no supported way to add an action to its
own toolbar, where a table view does (django-mvp/django-mvp#293). This feature does not wait on it.

## R3 — `MVPFormView` cannot render without a model

**Checked:** `mvp/views/edit.py:263`, its inheritance chain to `ModelInfoMixin`
(`mvp/views/base.py:332-357`), and by rendering one.

**Found:** `MVPFormView` is exported for plain (non-model) forms, but every render passes through
`ModelInfoMixin.get_context_data`, which calls `get_model_class()` and raises
`ImproperlyConfigured` when there is none. A modelless `MVPFormView` raises on first render.
Upstream's own tests only exercise its URL and title helpers, never a render, which is why the gap
has survived.

**What the plan does:** sets `model = Item` on the import view. That is honest rather than a
workaround — the page imports items, its breadcrumb belongs under the catalogue, and the title and
page classes it derives are the ones wanted. Nothing about the form becomes a model form.

## R4 — The report is not a queryset, and django-tables2 handles that

**Checked:** rendered a `tables.Table` over a list of frozen dataclasses through django-mvp's
`bootstrap5-mvp.html` template and its `<c-addons.django-table />` component.

**Found:** it works. `MVPTableView` itself is unusable here (it is a `ListView` and inherits the
same `ModelInfoMixin` problem as R3), but the table class and the component are independent of it —
the view builds the table and puts it in the context.

**What the plan does:** an `ImportReportTable` over presentation rows built from the import result,
rendered by the component inside the report page's content block. The alternative, the card-list
component, was rejected: a report is columnar by nature and a card per entry would make a
four-hundred-entry file unreadable.

## R5 — The demo walker cannot post a file

**Checked:** `demo/smoke.py:430-478`.

**Found:** every POST body is `urllib.parse.urlencode(fields)` with no content type, so the walker
can submit an ordinary form and nothing else. There is no multipart encoder anywhere in the
repository — no `FileField`, no `request.FILES`, no `SimpleUploadedFile` appears in the package,
the suite or the demo. This feature introduces the first file upload in the project.

**What the plan does:** adds a small multipart encoder to the walker beside the existing urlencoded
one, and a bibliography file under `demo/seed/` for it to submit. The encoder is tested the way
every other piece of the walker is tested — against markup the front end really renders, in
`tests/test_demo/test_smoke.py`.

## R6 — Reloading the report

**Checked:** what it would take to satisfy FR-023 (a reload must not re-run the import) while
holding FR-031 (nothing about the run is stored).

**Found:** the two cannot both be met literally. Rendering the report on the response to the upload
means a browser reload offers to resubmit the form, and a reader who accepts imports the file
again. Avoiding that needs the result to survive between two requests, which means session storage —
and a four-hundred-entry report does not fit a signed-cookie session, so it would require the host
project to run a database or cache session backend. Article X forbids the package requiring
structural changes of its host, so that is not available to a reusable app.

**What the plan does:** renders the report on the response, and FR-023 is narrowed to the guarantee
that can actually be kept — the report page offers no control that re-runs the import, and the
import happens once per submission. A browser's resubmission prompt is the browser's, and it is
what every server-rendered upload in Django does. Recorded as D11 and raised in the plan
notification, because it is a criterion written at specification time that implementation reality
narrowed.

## R7 — What the report can show, from what the result already carries

**Checked:** `literature/importers/results.py:15-116`.

**Found:** `EntryResult` carries `outcome`, `index` (zero-based, source order), `handle` (the cite
key, or the minted one for RIS, or `None`), `item` (the created object, `None` otherwise) and
`reason` (set if and only if the outcome is failed — enforced in `__post_init__`). `ImportResult`
carries the entries plus `created`, `skipped`, `failed` and `ok` properties.

Every column the spec asks for is there, so nothing is added to the contract for the report's sake:
position from `index`, outcome from `outcome`, citation key from `handle`, reason from `reason`, and
the link to the created reference from `item`.

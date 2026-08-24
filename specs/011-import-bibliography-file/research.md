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

## R2 — There is no view attribute for adding a toolbar action

**Checked:** django-mvp 0.19.1 at `/home/sam/projects/django-mvp/django-mvp/mvp/`, matching the copy
resolved into this project's environment.

**Found:** the action row is rendered by `cotton/page/list/actions/index.html`, whose action list is
a Cotton `c-vars` default of `['search','sort','filter','create']`. A `c-vars` default shadows any
context variable of the same name, so a view cannot add to the list by putting `actions` in its
context. There is no `toolbar_actions`, `list_actions` or `get_*_actions()` hook anywhere in
`mvp/views/` or `mvp/integrations/` — django-mvp's documented design is that each control follows
the thing that drives it (`search_fields` draws search, a FilterSet draws filter, and so on).

What does exist is `CRUDDirectoryMixin` (`mvp/views/detail.py:101-163`), which resolves arbitrary
named actions to URLs — its docstring says a custom action added to `directory` stays hidden until
the view opts in with a `show_<name>_action` attribute. So the URL half of a custom action is
supported; only the rendering half is missing.

**What the plan does:** carries the URL through the supported mechanism — `"import"` joins
`CRUD_VIEWS`, `directory` and `show_import_action` on both catalogue views — and renders it by
overriding the `page.actions` block, which is Django template inheritance rather than a fork of
anyone's markup. One partial holds the markup; two four-line wrappers put it into each parent
layout. Shadowing `cotton/page/list/actions/index.html` from inside this package was considered and
rejected: template resolution follows `INSTALLED_APPS` order and `literature.ui` is installed after
`mvp`, so the shadow would never win. A host project could do it; a package cannot.

The gap is worth raising upstream — a list view has no supported way to add an action to its own
toolbar — but this feature does not wait on it.

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

# django-literature

[![Tests](https://github.com/FAIR-DM/django-literature/actions/workflows/tests.yml/badge.svg)](https://github.com/FAIR-DM/django-literature/actions/workflows/tests.yml)
[![Build](https://github.com/FAIR-DM/django-literature/actions/workflows/build.yml/badge.svg)](https://github.com/FAIR-DM/django-literature/actions/workflows/build.yml)
[![Docs](https://github.com/FAIR-DM/django-literature/actions/workflows/docs.yml/badge.svg)](https://github.com/FAIR-DM/django-literature/actions/workflows/docs.yml)
[![Publish](https://github.com/FAIR-DM/django-literature/actions/workflows/publish.yml/badge.svg)](https://github.com/FAIR-DM/django-literature/actions/workflows/publish.yml)
[![Coverage](https://codecov.io/gh/FAIR-DM/django-literature/branch/main/graph/badge.svg)](https://codecov.io/gh/FAIR-DM/django-literature)
[![PyPI](https://img.shields.io/pypi/v/django-literature)](https://pypi.org/project/django-literature/)
[![Development status](https://img.shields.io/pypi/status/django-literature)](https://pypi.org/project/django-literature/)
[![Python](https://img.shields.io/pypi/pyversions/django-literature)](https://pypi.org/project/django-literature/)
[![Django](https://img.shields.io/pypi/djversions/django-literature)](https://pypi.org/project/django-literature/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Licence](https://img.shields.io/github/license/FAIR-DM/django-literature)](https://github.com/FAIR-DM/django-literature/blob/main/LICENSE)

A Django app for storing, managing, and converting bibliographic references using the [CSL JSON 1.0.2](https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html) standard.

---

## Features

- **Normalized data model** — five Django models (`Item`, `Name`, `ItemName`, `ItemDate`, `ItemIdentifier`) that faithfully represent the CSL JSON 1.0.2 specification.
- **Full CSL JSON coverage** — all 45 item types, 26 name roles, 6 date-variable slots, and 6 known identifier types.
- **Bidirectional conversion** — import CSL JSON dicts into the database and export model instances back to valid CSL JSON with full round-trip fidelity.
- **Partial date support** — year-only, year-month, full year-month-day, and date ranges via `django-partial-date`.
- **Identifier validation** — model-layer validators for DOI, ISBN, ISSN, URL, PMID, and PMCID formats.
- **Ordered contributors** — author, editor, and translator order is preserved independently within each role on an item.
- **i18n ready** — all user-facing strings wrapped with `gettext_lazy`; ships a pre-generated `locale/en/LC_MESSAGES/django.po` catalog.

---

## Scope & philosophy

**What it is.** Two Django apps that ship together. The core (`literature`) stores bibliographic
references as a normalized relational representation of CSL JSON 1.0.2 and converts between the two
in both directions with round-trip fidelity. It is headless: add `literature` to `INSTALLED_APPS`,
point a `ForeignKey` at an `Item`, and the host project owns its reference catalogue with no front
end pulled in. Layered on top is an opt-in UI app (`literature.ui`, built on
[django-mvp](https://github.com/django-mvp)) that provides a full front end, which is the intended
way to use the package in full. Install the core on its own, or add the UI when you want it.

**What it deliberately is not.**

- **Not a citation renderer in the core.** The core stores and converts CSL JSON. Formatting
  citations and bibliographies is added over time through a downstream CSL processor, never baked
  into the store.
- **Not a bundled admin.** No admin-based management ships with the package. A host that wants one
  registers its own; the UI app is where reference management lives.
- **Not a set of generic, restylable views.** The only views provided are the ones in
  `literature.ui`. Anything beyond that, a host builds against the models.
- **Not a host-styled UI.** `literature.ui` follows its own design system (django-mvp), not the
  host project's. It will not blend into your app's styling, and that is a deliberate trade for a UI
  that is complete and consistent on its own terms.
- **Not an external-registry client.** It does not sync with CrossRef, PubMed, or similar services
  at runtime.

**Tie-break principles**, when a design choice is contested:

1. **CSL JSON faithfulness wins.** The option closest to the CSL JSON structure and naming is
   preferred; any deviation is documented and mapped back to its CSL JSON equivalent.
2. **The core stays UI-free.** The store carries no front-end dependencies. Anything heavy, django-mvp
   included, sits behind the opt-in `literature.ui`, so embedding the core never drags in the UI stack.
3. **Relational integrity over convenience.** Known, stable fields (names, dates, identifiers) live
   in queryable relational structures, never JSON blobs.
4. **Translatable by default.** User-facing strings are always wrapped for i18n.

---

## Requirements

- Python 3.12+
- Django 5.2, 6.0 or 6.1
- [django-partial-date](https://github.com/ktowen/django_partial_date)

---

## Installation

```bash
pip install django-literature
```

Add `literature` to `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "literature",
]
```

Apply migrations:

```bash
python manage.py migrate
```

### Installing the front end

`literature.ui` is a second, opt-in app that adds a catalogue list page, a reference page and a
contributor page over whatever the core already stores, plus pages to add, edit and remove a
reference by hand. It is not required by the core and it is
not installed by default. It needs Python 3.12 or later and Django 5.2 or later, floors the core
does not share, so a project on an older Python or Django keeps the core available and simply
cannot resolve the extra.

```bash
pip install django-literature[ui]
```

Add the following to `INSTALLED_APPS`, in this order, alongside `literature`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "literature",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django_cotton",
    "easy_icons",
    "flex_menu",
    "django_tables2",
    "django_filters",
    "mvp",
    "daisy_cotton",
    "crispy_forms",
    "mvp_forms",
    "django_tomselect",
    "literature.ui",
]
```

`daisy_cotton` comes directly after `mvp`, because both ship an `icon` component and the first app
listed wins. `crispy_forms`, `mvp_forms` and `daisy_cotton` arrive with django-mvp as hard
dependencies, so listing them installs nothing extra. `django_tomselect` comes after `mvp_forms`, so
that django-mvp-forms' template for its controls wins; the `ui` extra installs it, and it draws the
reference picker.

The add, edit and delete pages render through crispy-forms with the `daisyui` template pack from
django-mvp-forms. crispy-forms needs the pack chosen before anything renders. With neither setting
below in place, the first form page raises an error rather than falling back to a default:

```python
# settings.py
CRISPY_TEMPLATE_PACK = "daisyui"
CRISPY_ALLOWED_TEMPLATE_PACKS = ["daisyui"]
```

### The page shell

django-mvp's packaged pages extend a template named `base.html`, which is the shell a project
writes for itself. django-mvp ships a default, so a project that has none still gets a working
shell rather than `TemplateDoesNotExist`. A project that writes its own `base.html` takes over with
nothing else to change, since a project's template directory is searched before any app's.

The UI app is built on [django-mvp](https://github.com/django-mvp), which needs a few settings of
its own before a page renders. `mvp/base.html`, the shell every page extends, loads its stylesheet
through `{% static %}` unconditionally, so having `django.contrib.staticfiles` installed is not
enough on its own:

```python
STATIC_URL = "static/"
```

Every icon the shell renders resolves through django-easy-icons. Without a default renderer
configured, opening any page in the UI app raises `ImproperlyConfigured`:

```python
EASY_ICONS = {
    "default": {
        "renderer": "easy_icons.renderers.ProviderRenderer",
        "config": {"tag": "i"},
        "packs": ["mvp.utils.BS5_ICONS"],
    },
}
```

The shell's sidebar and mobile navigation are rendered by django-flex-menus, which raises
`ValueError` at render time without renderers configured:

```python
FLEX_MENUS = {
    "renderers": {
        "sidebar": "mvp.renderers.SidebarRenderer",
        "dock": "mvp.renderers.MobileFooterNavRenderer",
    },
}
```

The shell also reads the current site, through `django.contrib.sites` and the `mvp_config` context
processor:

```python
TEMPLATES = [
    {
        # ...
        "OPTIONS": {
            "context_processors": [
                # ...
                "mvp.context_processors.mvp_config",
            ],
        },
    },
]

SITE_ID = 1
```

Pages render without it, but the site name is part of every page title, and reaching it needs the
matching middleware:

```python
MIDDLEWARE = [
    # ...
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django_tomselect.middleware.TomSelectMiddleware",
]
```

`TomSelectMiddleware` lets django-tomselect's controls read the request they are drawn for. The
reference picker below needs it.

Then include the app's URLs at whatever prefix the project wants:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    # ...
    path("catalogue/", include("literature.ui.urls")),
]
```

The routes are namespaced `literature`, so a template reverses them as `{% url 'literature:item-list' %}`
and `{% url 'literature:item-detail' pk=item.pk %}`.

One route the shell expects is the project's own. django-mvp's mobile navigation carries a Home
item pointing at a view named `home`, and the shell renders that navigation on every page, so a
project without a route of that name gets a reversal warning on each render and a Home button that
goes nowhere. Point it wherever your project's front door is:

```python
# urls.py
from django.views.generic import RedirectView

urlpatterns = [
    # ...
    path("", RedirectView.as_view(pattern_name="literature:item-list"), name="home"),
]
```

That is every step. Once the URLs are included, the catalogue list, the reference page and the
contributor page are live. No view, template, URL pattern, or line of styling is left for the host
to write.

### The catalogue: a table by default, cards if you prefer

With no further configuration, the catalogue route above serves references as a table — one row per
reference, carrying its citation key, item type, title, the journal or book it appeared in, its
credited names and its issued date, with a click to sort on every column heading but the credited
names. A row's title opens the reference's page, where it is edited. That is what a project
managing its own library gets out of the box.

The card presentation the package served before the table existed is still there: `ItemListView`,
reachable the same way as ever, one reference per card rather than per row, searching and filtering
the same set of references the table does. The contributor page keeps a plain, unfiltered version of
it regardless of which view backs the catalogue, since a contributor's credited works read better as
cards than as a table of one person's output. A project building a public-facing reading list, rather
than a tool for managing one, can prefer the card presentation for the catalogue too.

Selecting it is a settings change, under the same namespaced `LITERATURE` key the format registry
uses:

```python
# settings.py
LITERATURE = {
    "CATALOGUE_VIEW": "literature.ui.views.ItemListView",
}
```

The value is a dotted path rather than a two-way switch, so a project that has subclassed either
view — to add a column, change the page size, or narrow the queryset — can name its own class there
instead.

Everything else about the front end is unchanged: the route keeps the name `literature:item-list`, so
every breadcrumb, redirect and link that reverses it keeps working, and the create, edit and delete
pages are unaffected either way.

Sorting the table by item type orders by the type's stored value, not by the translated label shown
in the column — the label reads differently in every language the catalogue is served in, and the
order behind it does not change with it.

### Searching and filtering the catalogue

Both presentations carry a search box and three filters, reading from one shared definition, so a
narrowed catalogue returns the same references whichever route serves it. On the table the search
box and every filter sit together in the toolbar, each filter a dropdown. On the card list the
search box sits in the toolbar and the filters open in a drawer from a Filters button, at every
screen width. Applying a filter, removing one or moving to another page updates the list without
reloading the page.

The search box matches a fragment, case-insensitively, against a reference's citation key, its
title, short title and original title, the container it appeared in, and every credited
contributor's name. It deliberately does not reach a reference's abstract or its keywords: that text
runs much longer, and searching it well needs different infrastructure than a fast, predictable
lookup over a handful of short fields.

The three filters narrow on:

- **Type** — the kind of reference: an article, a book, a dataset, and so on. Several can be ticked
  at once.
- **Year** — the year a reference's issued date falls in, including a reference whose date covers a
  range beginning that year. It offers the years the catalogue's issued dates fall in, newest
  first. A reference with no issued date never matches a year.
- **Language** — whichever language values the catalogue actually holds, offered as a chooser built
  from the stored data rather than a fixed list a project has to keep in sync with it.

The table leaves Year or Language out of its toolbar when the catalogue holds nothing for it to
offer, such as Language when no reference records one.

There is no contributor filter. To find everything a person is credited on, search their name: the
search box matches every contributor's family, given and literal name, in any role.

Choosing more than one value within a single filter widens what it accepts — an article or a book.
A search term and a filter, or two different filters, narrow further — an article, published in
2019. A filter value that matches no reference, such as a year no reference was issued in, returns
no results. A value a filter cannot accept, such as a year that is not a number, is ignored for that
filter alone, and the search and the other filters still apply.

A search, every filter, the chosen sort and the current page all live in the address, so moving to
another page, changing the sort, or bookmarking the address and reopening it later keeps every one
of them in force.

### Adding, editing and removing a reference

The catalogue list carries an Add action, and a reference page carries Edit and Delete actions.
Between them, a reference can be entered by hand, corrected, and removed without leaving the front
end. Each opens a route under the same `literature:` namespace: `literature:item-create`,
`literature:item-update` and `literature:item-delete`.

The form is laid out in four tabs:

- **Reference**: the type, citation key and title, the sections the chosen type uses, the dates,
  and the abstract and keywords.
- **Contributors**: one list per role.
- **Identifiers**: a DOI, an ISBN, a URL and any other identifier.
- **More**: notes, an annotation, alternate titles and where the reference was catalogued.

The form scopes itself to the reference's type: choosing a type reveals only the sections, dates and
contributor roles that kind of reference typically carries, with toggles to show the rest. Nothing
is ever dropped by choosing a narrower type: every field stays part of the form and keeps whatever
value it already holds, whether or not its section is currently shown. A form sent back with errors
lists every one of them above the tabs, each linking to its field.

The type, identifier type and keyword controls are Tom Select controls, and the form page loads Tom
Select from jsDelivr. Without it they are plain selects and the form still works.

Each of these pages requires Django's model permission for what it does: `literature.add_item` to
add, `literature.change_item` to edit and `literature.delete_item` to delete. A visitor who is not
signed in is sent to your project's `LOGIN_URL`, and a signed-in user without the permission is
refused. The Add, Edit and Delete actions are only shown to users who hold the permission behind
them. Grant the three permissions to a group for the people who maintain the catalogue. The
catalogue list, reference pages and contributor pages stay open to everyone. To apply a different
rule, subclass the view and set `permission_required` or override `has_permission()`.

### Importing a bibliography file

The table catalogue carries an Import action at the end of its toolbar, after the filters, opening
a page with a format choice and a file control. The card list has none, so a project serving the
catalogue as cards links to the `literature:item-import` route from its own navigation. Submitting previews the file by default, on a page of its own: the same report a real
import would produce, with nothing yet written to the catalogue — how many entries would be
created, skipped and failed, and one row per entry in the order the file held them, narrowable to
one outcome without leaving the page. A control at the foot carries out the import it described
and returns you to the catalogue with a message stating what was created. A checkbox on the form
skips the preview for a one-step import instead, which lands on the same report of what it did.

The format is chosen, never detected from the file itself — pick the wrong one and the format's
own message says so on every entry, rather than the file being silently misread. Nothing checks
whether a file has already been imported, so submitting the same file twice creates the references
twice. The page says so before you submit. A failure partway through the file does not undo what
already succeeded — the entries created before it stay in the catalogue.

Importing creates references, so the import page, its preview and its confirm control all
require `literature.add_item`, the same permission as adding one by hand. The package imposes no
size limit of its own on the file it accepts. Bounding it is left to the host project.

### Choosing a reference in your own form

A project whose own model points at a reference can add a searchable picker to its form with one
field, `ReferenceField` from `literature.ui.picker` (`ReferenceMultipleField` for several). It is a
django-tomselect field whose default points at the catalogue's search. People find the reference by
typing part of its title, a contributor's name, its citation key or its DOI. See
[How to choose a reference in your own form](https://github.com/FAIR-DM/django-literature/blob/main/docs/how-to/choose-a-reference-in-your-own-form.md).

### Try it: the demo project

The repository carries a runnable demo of everything above, wired the same way this section
documents. From a fresh clone, with dependencies installed:

```bash
uv sync --extra ui
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

`migrate` builds the database, `seed_demo` loads a small catalogue of real references into it, and
`runserver` serves the site at `http://127.0.0.1:8000/catalogue/`, where the catalogue list, a
reference page and a contributor page are all live and populated. Browsing needs no account. To
add, edit, remove or import references, sign in at `http://127.0.0.1:8000/admin/login/` as
`editor.user` with the password `password`, the account `seed_demo` creates. The Add, Edit, Delete
and Import actions then appear, so you can enter, correct, remove and import references the same
way a host project's own users would. The Add and Edit forms carry the reference's
contributors, dates and identifiers as part of the same page, so crediting a contributor, dating a
reference and identifying it are all things you can try there too — see
[Add and edit form](https://github.com/FAIR-DM/django-literature/blob/main/docs/reference/add-and-edit-form.md) for what each of those does.
`demo/seed/import-sample.bib` is there to import: it holds entries that convert and one that does
not, so the report has something to show.

`seed_demo` is destructive and idempotent: it clears the catalogue before loading, so running it
again returns the demo to the same seeded state whatever state it was in before — including
discarding anything you added through the admin. It also resets the editor account's password to
`password`. Once seeded, `runserver` on its own is enough for
subsequent runs.

The demo is not a production configuration: `DEBUG` is on, the database is a local SQLite file, and
the secret key is a throwaway value committed in `demo/settings.py`. Do not deploy it as-is.

---

## Quick Start

### Import from CSL JSON

```python
from literature.converters import from_csl_json

item = from_csl_json({
    "id": "Jennings2019",
    "type": "article-journal",
    "title": "A new compositionally based thermal conductivity model",
    "author": [
        {"family": "Jennings", "given": "S"},
        {"family": "Hasterok", "given": "D"},
    ],
    "issued": {"date-parts": [[2019, 8, 16]]},
    "DOI": "10.1093/gji/ggz376",
    "container-title": "Geophysical Journal International",
    "volume": "219",
    "issue": "2",
    "page": "1377-1394",
})

print(item.citation_key)  # "Jennings2019"
print(item.title)         # "A new compositionally based thermal conductivity model"
```

### Export to CSL JSON

```python
from literature.converters import to_csl_json

csl = to_csl_json(item)
# csl is a standards-compliant dict ready for citeproc-js or any CSL processor
```

### Batch import

```python
import json
from literature.converters import from_csl_json_list

with open("references.json") as f:
    items = from_csl_json_list(json.load(f))

print(f"Imported {len(items)} references")
```

### Import a bibliography file

CSL JSON is what this package stores, but researchers keep their libraries in BibTeX and RIS. The
import contract reads any configured format through one call and tells you what happened to every
entry in the file. Declare which formats your project reads in settings:

BibTeX and RIS are both read out of the box and need no configuration. Declare `BIB_FORMATS` only
to add a format of your own, which replaces the default list rather than extending it — so list the
built-ins you still want alongside it:

```python
# settings.py
LITERATURE = {
    "BIB_FORMATS": [
        "literature.importers.bibtex.BibTeXFormat",
        "literature.importers.ris.RISFormat",
        "myapp.formats.EndNoteXMLFormat",
    ],
}
```

Then import by name:

```python
from literature.importers import get_format

with open("library.bib") as handle:
    result = get_format("bibtex")().import_file(handle)

print(f"{len(result.created)} stored, {len(result.failed)} could not be read")

for entry in result.failed:
    label = entry.handle or f"entry {entry.index}"
    print(f"  {label}: {entry.reason}")
```

Importing is per entry. One unreadable entry does not stop the rest of the file, and every entry
is accounted for in the result whether it was stored or not — you never have to compare counts to
find out something went wrong. An entry is stored in full or not at all, so a rejected contributor
never leaves an item behind without its authors.

Rehearse it first if you like. Every stage runs, nothing is written:

```python
with open("library.bib") as handle:
    preview = get_format("bibtex")().import_file(handle, dry_run=True)

if not preview.ok:
    print(f"{len(preview.failed)} entries need attention first")
```

To find out which formats an installation can read:

```python
from literature.importers import available_formats

for name, format_class in available_formats().items():
    print(name, "—", format_class.label)
```

#### Reading BibTeX

`bibtex` reads a `.bib` file in either dialect — classic BibTeX, which is what a publisher's
"export citation" link and most academic databases emit, and BibLaTeX, which is what current
Zotero and JabRef write. You do not have to know which one you were given.

An export is rarely clean, so the format recovers before it refuses. A DOI written as a resolver
URL is normalized to the bare identifier, LaTeX-encoded text becomes the characters it stands for,
XML escaping left over from a publisher's pipeline is resolved, and a value that cannot be
recovered is kept with the record instead of costing you the whole entry. `@string` macros are
expanded and `crossref` inheritance is resolved, including a reference to an entry defined further
down the file.

Fields that no bibliographic standard defines — the `file`, `owner` and `timestamp` bookkeeping
every reference manager writes into its exports — have no CSL equivalent and are not thrown away
either. They are stored on the item under `custom["bibtex"]` and can be read back:

```python
item = result.created[0].item
print(item.custom["bibtex"])   # {'file': ':papers/curie1898.pdf:PDF', 'owner': 'sam', ...}
```

[What maps to what](https://django-literature.readthedocs.io/en/latest/reference/bibtex-mapping.html) is
generated from the mapping tables themselves, so it cannot fall out of step with the code.

#### Reading RIS

`ris` reads a `.ris` file the way EndNote, Web of Science and Scopus write it, with no producer
detection: one format, reading every tag the original specification defines and every tag these
producers use beyond it, decided from the tag itself rather than from which tool wrote the file.
RIS supplies no cite key of its own — where an entry carries no `ID` tag, one is minted from its
own author, year and title instead, and importing the same file twice mints the same key both
times.

Bibliographic exports vary more than any one specification can promise to cover, so this package
reads the common producers as best it can. It makes no promise that every variant imports
perfectly, and its coverage grows over time through bug reports and feature requests rather than
a fixed target: EndNote is the primary support target, with Web of Science and Scopus supported
secondarily. A file from a producer this package does not name is still read — tags the
specification defines are read, and tags it does not are preserved rather than dropped.

Tags with no CSL equivalent are kept with the record rather than discarded, the same as BibTeX's
own bookkeeping fields:

```python
item = result.created[0].item
print(item.custom["ris"])   # {'C7': 'e70142', 'N1': 'Funding: NIH grant R01-GM12345'}
```

[What maps to what](https://django-literature.readthedocs.io/en/latest/reference/ris-mapping.html) is
generated from the mapping tables themselves too, the same way as BibTeX's own page.

Adding a further format means writing a `BibFormat` subclass with a parser and a conversion to CSL
JSON, then listing its dotted path in `LITERATURE["BIB_FORMATS"]` — the workflow above does not
change. A format with an unusual need may override any of the workflow's other steps
(`import_entries`, `import_entry`, `get_result`); the base class only has to get the job done when
its two required stages are supplied, not stop you from replacing the rest.

### Query

```python
from literature.models import Item

# All journal articles
articles = Item.objects.filter(type="article-journal")

# Items authored by a specific person
by_jennings = Item.objects.filter(
    item_names__name__family="Jennings",
    item_names__role="author",
)
```

---

## Data Model Overview

```
Item ──< ItemName >── Name
  │
  ├──< ItemDate
  │
  └──< ItemIdentifier
```

| Model | Purpose | CSL JSON equivalent |
|---|---|---|
| `Item` | Core bibliographic entry | Top-level item object |
| `Name` | Person or organization | Name-variable object |
| `ItemName` | Associates names with items in a role and order | Name-variable array entry |
| `ItemDate` | Structured date per CSL date-variable slot | Date-variable object |
| `ItemIdentifier` | Typed identifier (DOI, ISBN, etc.) | Top-level string fields |

See the [data model documentation](https://github.com/FAIR-DM/django-literature/blob/main/docs/reference/data-model.md) for the full field reference.

---

## Documentation

Full documentation is available in [docs/](https://github.com/FAIR-DM/django-literature/tree/main/docs).

A database still on the old `LiteratureItem` schema is moved to the current models with
`python manage.py upgrade_literature`. See
[How to upgrade a database from the `LiteratureItem` schema](https://github.com/FAIR-DM/django-literature/blob/main/docs/how-to/upgrade-a-database-from-the-literatureitem-schema.md).

To build locally:

```bash
uv sync --group docs
uv run sphinx-build -b html docs docs/_build/html
```

---

## Development

```bash
git clone https://github.com/FAIR-DM/django-literature.git
cd django-literature
uv sync
uv run pytest
```

---

## Changelog

See [CHANGELOG.md](https://github.com/FAIR-DM/django-literature/blob/main/CHANGELOG.md).

## License

MIT — see [LICENSE](https://github.com/FAIR-DM/django-literature/blob/main/LICENSE).

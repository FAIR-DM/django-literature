# django-literature

A Django app for storing, managing, and converting bibliographic references using the [CSL JSON 1.0.2](https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html) standard.

[![Tests](https://github.com/FAIR-DM/django-literature/actions/workflows/tests.yml/badge.svg)](https://github.com/FAIR-DM/django-literature/actions)
[![codecov](https://codecov.io/gh/FAIR-DM/django-literature/branch/main/graph/badge.svg)](https://codecov.io/gh/FAIR-DM/django-literature)
[![PyPI](https://img.shields.io/pypi/v/django-literature.svg)](https://pypi.org/project/django-literature/)
[![Python](https://img.shields.io/pypi/pyversions/django-literature.svg)](https://pypi.org/project/django-literature/)
[![Django](https://img.shields.io/pypi/djversions/django-literature.svg)](https://pypi.org/project/django-literature/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
- Django 5.2 or 6.0
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
contributor page over whatever the core already stores. It is not required by the core and it is
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
    "mvp",
    "crispy_forms",
    "crispy_tailwind",
    "literature.ui",
]
```

`mvp` comes before `crispy_tailwind` because django-mvp overrides one of crispy-tailwind's
templates and the first app to declare a template path wins. Both crispy apps arrive with django-mvp
as hard dependencies, so listing them installs nothing extra.

### The `base.html` this app ships

django-mvp's packaged pages extend a template named `base.html`, which is the shell a project
writes for itself. Until django-mvp ships a default of its own, `literature.ui` carries one: a
single line forwarding to `mvp/base.html`, with no blocks of its own.

A project that has its own `base.html` keeps it — a project's template directory is searched before
any app's — and a project that has none gets a working shell instead of `TemplateDoesNotExist`. If
you want the pages inside your own layout, write `base.html` in your project and it takes over with
nothing else to change.

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
]
```

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

### Try it: the demo project

The repository carries a runnable demo of everything above, wired the same way this section
documents. From a fresh clone, with dependencies installed:

```bash
poetry install --extras ui
python manage.py demo
```

That one command creates the database, applies migrations, loads a small catalogue of real
references, and starts the server. It prints the address to open — `http://127.0.0.1:8000/catalogue/`
— where the catalogue list, a reference page and a contributor page are all live and populated.
Running the command again returns the demo to that same seeded state, whatever state it was in
before.

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

[What maps to what](https://django-literature.readthedocs.io/en/latest/bibtex-mapping.html) is
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

[What maps to what](https://django-literature.readthedocs.io/en/latest/ris-mapping.html) is
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

See the [data model documentation](docs/data-model.md) for the full field reference.

---

## Documentation

Full documentation is available in [docs/](docs/).

To build locally:

```bash
poetry install --with docs
poetry run sphinx-build -b html docs docs/_build/html
```

---

## Development

```bash
git clone https://github.com/FAIR-DM/django-literature.git
cd django-literature
poetry install
poetry run pytest
```

---

## License

MIT — see [LICENSE](LICENSE).

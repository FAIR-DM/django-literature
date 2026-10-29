# Django Literature

Django Literature stores bibliographic references in your Django project and converts them to and
from [CSL JSON 1.0.2](https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html), the
format citeproc-js, Pandoc and most reference managers exchange. Its models are a direct relational
translation of CSL JSON, so a reference imported from CSL JSON, BibTeX or RIS can be exported again
to any CSL processor. An optional web interface adds a catalogue, pages to add and edit references, and
a reference picker for your own forms.

Some reasons you might want to use Django Literature:

- **A real relational model.** Five models, `Item`, `Name`, `ItemName`, `ItemDate` and
  `ItemIdentifier`, cover all 45 CSL item types, 26 contributor roles and every date slot. See
  [Storing references](developer/references.md).
- **Import from what people already have.** CSL JSON, BibTeX and RIS, from code or from an import
  page with a preview, and new formats can be added. See [Importing](developer/importing.md).
- **Export without loss.** A stored reference exports back to the CSL JSON it came from. See
  [Exporting](developer/exporting.md).
- **Partial dates and checked identifiers.** A date holds only the precision you know, and a
  malformed DOI, ISBN, ISSN, URL, PMID or PMCID is refused when it is saved.
- **A complete web interface, if you want one.** A searchable, filterable catalogue, reference and
  contributor pages, and add, edit, delete and import pages. See [The catalogue](ui/catalogue.md).
- **References in your own forms and pages.** A searchable picker field and a display component.
  See [The reference picker](ui/picker.md) and [Displaying references](ui/displaying.md).

## Requirements

Django Literature requires:

- Python 3.11 or later
- Django 4.2 or later

The web interface, installed with the `ui` extra, requires:

- Python 3.12 or later
- Django 5.2 or later
- [django-mvp](https://github.com/django-mvp), installed with the extra

## Installation

Install the package with `pip`:

```bash
pip install django-literature
```

Add `literature` to your `INSTALLED_APPS` setting:

```python
INSTALLED_APPS = [
    # ...
    "literature",
]
```

Apply the migrations:

```bash
python manage.py migrate
```

The models are ready to use. To add the catalogue and its pages as well, see
[Installing the web interface](ui/installation.md). Every step, with what each one sets up, is in
the [installation guide](developer/installation.md).

## Example

Store a reference from a CSL JSON record, then read it back:

```python
from literature.converters import from_csl_json, to_csl_json

item = from_csl_json(
    {
        "id": "Jennings2019",
        "type": "article-journal",
        "title": "A new compositionally based thermal conductivity model",
        "container-title": "Geophysical Journal International",
        "author": [
            {"family": "Jennings", "given": "S"},
            {"family": "Hasterok", "given": "D"},
        ],
        "issued": {"date-parts": [[2019, 8, 16]]},
        "DOI": "10.1093/gji/ggz376",
    }
)

item.doi       # "10.1093/gji/ggz376"
item.year      # 2019
item.item_names.filter(role="author").count()  # 2

to_csl_json(item)  # the same record, ready for any CSL processor
```

With the web interface installed and its URLs mounted at `catalogue/`, open
`http://127.0.0.1:8000/catalogue/` to see the reference in the catalogue.

## Next steps

- The [developer guide](developer/index.md) covers using the package from Python, starting with
  [installation](developer/installation.md).
- The [web interface](ui/index.md) section covers the catalogue and its pages.
- The [reference](reference/index.md) describes every model, setting, page and Python API entry.

## About the project

Three documents in the repository set out what the package is for and how it is built:

- [Goals](https://github.com/FAIR-DM/django-literature/blob/main/GOALS.md): the directions the package works toward, and how important each one is.
- [Domain model](https://github.com/FAIR-DM/django-literature/blob/main/CONTEXT.md): the names the package gives to things, such as item,
  contributor and citation key, and what each one means. Read it before writing about the package
  or proposing a change.
- [Constitution](https://github.com/FAIR-DM/django-literature/blob/main/CONSTITUTION.md): the rules every change to the package follows.

What changed in each release is in the [changelog](https://github.com/FAIR-DM/django-literature/blob/main/CHANGELOG.md).

## Support

Report a bug or ask for a feature on the
[issue tracker](https://github.com/FAIR-DM/django-literature/issues). See
[Contributing](contributing/index.md) for how to run the tests and work on the package. Everyone
taking part follows the
[code of conduct](https://github.com/FAIR-DM/.github/blob/main/CODE_OF_CONDUCT.md).

## Licence

Django Literature is released under the
[MIT licence](https://github.com/FAIR-DM/django-literature/blob/main/LICENSE).

```{toctree}
:hidden:

Home <self>
developer/index
ui/index
reference/index
contributing/index
```

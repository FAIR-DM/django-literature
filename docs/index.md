# django-literature

A Django app for storing, managing, and converting bibliographic references. Its models are a
direct relational translation of
[CSL JSON 1.0.2](https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html), so a reference
can be imported from CSL JSON, BibTeX or RIS and exported again to any CSL processor. An optional
front end adds a catalogue, pages to add and edit references, and a reference picker for your own
forms.

```{toctree}
:maxdepth: 1
:caption: How-to guides

how-to/install-django-literature
how-to/add-a-translation
how-to/create-a-reference-in-code
how-to/import-csl-json
how-to/export-a-reference-as-csl-json
how-to/find-references
how-to/link-to-a-reference-and-cite-its-doi
how-to/import-a-bibliography-file
how-to/import-a-bibliography-file-in-code
how-to/add-an-import-format
how-to/choose-a-reference-in-your-own-form
how-to/show-a-reference-on-your-own-page
how-to/upgrade-a-database-from-the-literatureitem-schema
```

```{toctree}
:maxdepth: 1
:caption: Reference

reference/data-model
reference/settings
reference/add-and-edit-form
reference/import-pages
reference/bibtex-mapping
reference/ris-mapping
reference/api/index
```

```{toctree}
:maxdepth: 1
:caption: Explanation

explanation/citation-keys
explanation/round-trip-fidelity
explanation/contributor-records
explanation/field-groups
```

```{toctree}
:maxdepth: 1
:caption: Decision records

adr/index
```

```{toctree}
:maxdepth: 1
:caption: Roadmap

ROADMAP
```

```{toctree}
:maxdepth: 1
:caption: Contributing

contributing/standards/testing
contributing/standards/code-documentation
contributing/standards/django
contributing/standards/documentation
```

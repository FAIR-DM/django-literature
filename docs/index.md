# django-literature

A Django app for storing, managing, and converting bibliographic references. Its models are a
direct relational translation of
[CSL JSON 1.0.2](https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html), so a reference
can be imported from CSL JSON, BibTeX or RIS and exported again to any CSL processor. An optional
front end adds a catalogue, pages to add and edit references, and a reference picker for your own
forms.

- [How-to guides](how-to/index.md) take you through one task.
- [Reference](reference/index.md) describes the models, settings, pages and Python API.
- [Explanation](explanation/index.md) covers why the package works the way it does.

The [decision records](adr/index.md), the [roadmap](ROADMAP.md) and the
[contributing standards](contributing/index.md) are for the package's maintainers.

```{toctree}
:hidden:

how-to/index
reference/index
explanation/index
adr/index
ROADMAP
contributing/index
```

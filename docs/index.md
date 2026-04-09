# django-literature

A Django app for storing, managing, and converting bibliographic references using the
[CSL JSON 1.0.2](https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html) standard.

---

```{toctree}
:maxdepth: 2
:caption: Getting Started

installation
usage
```

```{toctree}
:maxdepth: 2
:caption: Reference

data-model
api/index
```

---

## Overview

**django-literature** provides a normalized relational data model for bibliographic data
modelled directly on the [CSL JSON 1.0.2 specification](https://github.com/citation-style-language/schema).
It is designed to be dropped into any Django project as a reusable app.

### Key capabilities

::::{grid} 2
:::{grid-item-card} CSL JSON conversion
Import a list of references from a CSL JSON file or API response in a single call.
Export any stored item back to a standards-compliant CSL JSON dict for use with
citeproc-js, Pandoc, or any other CSL processor.
:::
:::{grid-item-card} Complete data model
All 45 CSL item types, 26 name roles, and 6 date-variable slots are supported.
Partial dates (year-only, year-month, full date, date ranges) are preserved with
full precision.
:::
:::{grid-item-card} Identifier validation
Model-layer validators enforce correct format for DOI, ISBN, ISSN, URL, PMID, and
PMCID values so invalid identifiers are never silently stored.
:::
:::{grid-item-card} Ordered contributors
Author/editor/translator ordering is preserved per item and role using
`django-ordered-model`.
:::
::::

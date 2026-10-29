# Installation

Django Literature is two apps that ship together. The core, `literature`, holds the models and the
converters and pulls in no front end. This page installs the core. The front end, `literature.ui`,
adds the catalogue and its pages, and is installed on top of it as described in
[Installing the front end](front-end.md).

The core needs Python 3.11 or later and Django 4.2 or later.

## Steps

1. Install the package:

   ```bash
   pip install django-literature
   ```

   [django-partial-date](https://github.com/ktowen/django_partial_date), which stores dates at the
   precision they are known, is installed with it.

2. Add `literature` to `INSTALLED_APPS`:

   ```python
   # settings.py
   INSTALLED_APPS = [
       # ...
       "literature",
   ]
   ```

3. Apply the migrations:

   ```bash
   python manage.py migrate
   ```

The database now has one table for each model in the [data model](../reference/data-model.md):

| Table | Django model |
|---|---|
| `literature_item` | `Item` |
| `literature_name` | `Name` |
| `literature_itemname` | `ItemName` |
| `literature_itemdate` | `ItemDate` |
| `literature_itemidentifier` | `ItemIdentifier` |

A database that still holds the old `LiteratureItem` tables is moved over as described in
[Upgrading from the `LiteratureItem` schema](upgrading.md) instead.

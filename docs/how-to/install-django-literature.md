# Install django-literature

Add django-literature's models to a Django project, so it can store references and convert them
to and from CSL JSON. The pages for browsing and editing references are a separate, optional app,
installed as described in the README's
[Installing the front end](https://github.com/FAIR-DM/django-literature#installing-the-front-end).

## Before you start

The project needs Python 3.11 or later and Django 4.2 or later.

## Steps

1. Install the package from PyPI:

   ```bash
   pip install django-literature
   ```

   Or with [uv](https://docs.astral.sh/uv/):

   ```bash
   uv add django-literature
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

## The result

The database has five new tables, one for each model in the [data model](../reference/data-model.md):

| Table | Django model |
|---|---|
| `literature_item` | `Item` |
| `literature_name` | `Name` |
| `literature_itemname` | `ItemName` |
| `literature_itemdate` | `ItemDate` |
| `literature_itemidentifier` | `ItemIdentifier` |

A database that already holds the old `LiteratureItem` tables is moved over with
[Upgrade a database from the `LiteratureItem` schema](upgrade-a-database-from-the-literatureitem-schema.md)
instead.

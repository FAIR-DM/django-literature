# Installation

## Requirements

- Python 3.11+
- Django 4.2+
- [django-partial-date](https://github.com/ktowen/django_partial_date) — partial date precision

## Install from PyPI

```bash
pip install django-literature
```

Or with [Poetry](https://python-poetry.org/):

```bash
poetry add django-literature
```

## Configure Django

Add `literature` to `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "literature",
]
```

## Apply migrations

```bash
python manage.py migrate
```

This creates five tables in your database:

| Table | Django model |
|---|---|
| `literature_item` | `Item` |
| `literature_name` | `Name` |
| `literature_itemname` | `ItemName` |
| `literature_itemdate` | `ItemDate` |
| `literature_itemidentifier` | `ItemIdentifier` |

## Internationalization (optional)

The package ships a pre-generated English `django.po` catalog in
`literature/locale/en/LC_MESSAGES/`. If you need translations into other languages,
add the `literature` locale directory to Django's
[`LOCALE_PATHS`](https://docs.djangoproject.com/en/stable/ref/settings/#locale-paths):

```python
# settings.py
LOCALE_PATHS = [
    # your project locales …
    BASE_DIR / "venv" / "lib" / "site-packages" / "literature" / "locale",
]
```

Then run `makemessages` and `compilemessages` as usual.

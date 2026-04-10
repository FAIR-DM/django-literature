# Quickstart: Django Admin Interface for Bibliographic Data

**Feature Branch**: `002-django-admin-interface`
**Date**: 2026-04-10

## Prerequisites

- Django 4.2+
- `django-literature` installed and added to `INSTALLED_APPS`
- `django.contrib.admin`, `django.contrib.auth`, `django.contrib.contenttypes`, and `django.contrib.sessions` in `INSTALLED_APPS`
- Admin URL patterns included in your project's `urls.py`

## Setup

The admin interface is automatically registered when `literature` is in `INSTALLED_APPS`.
No additional configuration is needed.

### Verify Installation

```python
# settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "ordered_model",
    "literature",
    # ...
]
```

```python
# urls.py
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
```

## Usage

1. Navigate to `/admin/` and log in with a staff account
2. Under the **Literature** section you will see:
   - **Items** — Bibliographic entries
   - **Names** — Contributor name records
3. Click **Items** → **Add Item** to create a new entry
4. Fill in the Identity & Type fields, Titles, and any other relevant sections
5. Add contributors, dates, and identifiers using the inline sections at the bottom of the form
6. Click **Save**

## Admin Features

- **Fieldset grouping**: Item fields are organized into 12 logical sections; infrequently used sections (Numbering, Additional Titles, Content, Event, etc.) are collapsed by default
- **Inline editing**: Contributors (ItemName), Dates (ItemDate), and Identifiers (ItemIdentifier) are edited directly on the Item form
- **Search**: Items list supports searching by title and citation key
- **Filtering**: Items list has sidebar filters for item type and publisher
- **Name management**: Separate admin section for managing shared Name records (search by family/given name)

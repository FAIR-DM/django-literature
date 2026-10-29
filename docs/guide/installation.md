# Installation

Django Literature is two apps that ship together. The core, `literature`, holds the models and the
converters and pulls in no front end. The front end, `literature.ui`, adds the catalogue and its
pages, and is optional.

## Install the core

The core needs Python 3.11 or later and Django 4.2 or later.

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

## Install the front end

The front end needs Python 3.12 or later and Django 5.2 or later. A project on an older Python or
Django keeps the core and cannot install the extra.

1. Install the `ui` extra:

   ```bash
   pip install "django-literature[ui]"
   ```

2. Add the apps to `INSTALLED_APPS`, in this order, alongside `literature`:

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

   `daisy_cotton` comes directly after `mvp`, because both ship an `icon` component and the first
   app listed wins. `django_tomselect` comes after `mvp_forms`, so that django-mvp-forms' template
   for its controls wins.

3. Add the settings the page shell and the forms need:

   ```python
   # settings.py
   STATIC_URL = "static/"
   SITE_ID = 1

   CRISPY_TEMPLATE_PACK = "daisyui"
   CRISPY_ALLOWED_TEMPLATE_PACKS = ["daisyui"]

   EASY_ICONS = {
       "default": {
           "renderer": "easy_icons.renderers.ProviderRenderer",
           "config": {"tag": "i"},
           "packs": ["mvp.utils.BS5_ICONS"],
       },
   }

   FLEX_MENUS = {
       "renderers": {
           "sidebar": "mvp.renderers.SidebarRenderer",
           "dock": "mvp.renderers.MobileFooterNavRenderer",
       },
   }

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

   MIDDLEWARE = [
       # ...
       "django.contrib.sites.middleware.CurrentSiteMiddleware",
       "django_tomselect.middleware.TomSelectMiddleware",
   ]
   ```

   Without the crispy-forms pack, the first form page raises an error. Without `EASY_ICONS` or
   `FLEX_MENUS`, every page does.

4. Mount the URLs, and give the shell's Home item somewhere to go:

   ```python
   # urls.py
   from django.urls import include, path
   from django.views.generic import RedirectView

   urlpatterns = [
       # ...
       path("catalogue/", include("literature.ui.urls")),
       path("", RedirectView.as_view(pattern_name="literature:item-list"), name="home"),
   ]
   ```

   The routes are namespaced `literature`, so a template reverses them as
   `{% url 'literature:item-list' %}`. The shell's mobile navigation links to a view named `home`
   on every page, so a project without one gets a warning on each render.

Open `/catalogue/`. The catalogue list, the reference pages and the contributor pages are live, with
no view, template or styling left for you to write.

### The page shell

The front end's pages extend a template named `base.html`. django-mvp ships a default, so a
project with none still gets a working shell. A `base.html` in your own template directory is found
first and takes over.

## Try the demo project

The repository carries a runnable demo of everything above. From a fresh clone:

```bash
uv sync --extra ui
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

`seed_demo` loads a small catalogue of real references, and the site is served at
`http://127.0.0.1:8000/catalogue/`. Browsing needs no account. To add, edit, remove or import
references, sign in at `http://127.0.0.1:8000/admin/login/` as `editor.user` with the password
`password`. `demo/seed/import-sample.bib` is there to import.

`seed_demo` clears the catalogue before loading, so running it again returns the demo to the same
state. The demo is not a production configuration: `DEBUG` is on and its secret key is committed.

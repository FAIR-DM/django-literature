# Translations

Every label, help text and message in the package is marked for translation. The package ships an
English catalogue in `literature/locale/en/LC_MESSAGES/django.po` to translate from.

## Add a translation

1. Add the package's locale directory to Django's
   [`LOCALE_PATHS`](https://docs.djangoproject.com/en/stable/ref/settings/#locale-paths):

   ```python
   # settings.py
   LOCALE_PATHS = [
       # your project locales …
       BASE_DIR / "venv" / "lib" / "site-packages" / "literature" / "locale",
   ]
   ```

2. Run `makemessages` and `compilemessages` as usual.

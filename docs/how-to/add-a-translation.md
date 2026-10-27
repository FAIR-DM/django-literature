# How to add a translation

Translate the package's labels, help text and messages into another language. The package ships
an English `django.po` catalog in `literature/locale/en/LC_MESSAGES/` to translate from.

## Steps

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

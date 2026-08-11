"""The opt-in front end for browsing the catalogue.

``literature.ui`` is an installed Django app, so this module is imported
during app-registry phase 1 — before ``literature.models`` is ready. It stays
a docstring and nothing else for exactly the reason ``literature/__init__.py``
does: a re-export reaching ``views.py`` reaches the models and raises
``AppRegistryNotReady`` at ``django.setup()``, failing every install. Unlike
``literature.importers`` (a plain sub-package, not an installed app), there is
no curated re-export here — import from ``literature.ui.views`` directly.
"""

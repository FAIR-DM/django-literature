"""Empty URLconf for ``tests.settings_core``.

The core-only settings module must stay free of the UI app's URLs (plan.md
D-4) — this is what T016's core-only boot subprocess resolves
``ROOT_URLCONF`` against.
"""

urlpatterns = []

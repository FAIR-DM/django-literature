"""Empty URLconf for ``tests.settings_core``.

The core-only settings module must stay free of the UI app's URLs (FS-006) —
this is what the core-only boot subprocess resolves ``ROOT_URLCONF`` against.
"""

urlpatterns = []

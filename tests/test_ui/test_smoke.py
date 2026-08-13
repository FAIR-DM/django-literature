"""Smoke tests proving ``tests.settings_core`` and ``tests.settings`` boot as
plan.md D-4 requires. The subject is the test settings modules themselves,
not a source module, so ``test_smoke.py`` is one of the org's standing
non-mirror exceptions (Article X) — no ``[tool.forge.conformance]``
declaration is needed here.
"""

import subprocess
import sys
from importlib import import_module

from django.conf import settings

# A fresh subprocess, never the pytest process: django.setup() only ever runs
# once per interpreter, and the pytest session has already populated the app
# registry from tests.settings before this test executes.
_CORE_BOOT_SCRIPT = """
import os
# Force, not setdefault: pytest-django exports DJANGO_SETTINGS_MODULE=tests.settings
# into the environment, and this subprocess inherits it by default.
os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings_core"
import django
django.setup()

from django.conf import settings
from importlib import import_module

assert "literature.ui" not in settings.INSTALLED_APPS
assert "mvp" not in settings.INSTALLED_APPS

urlconf = import_module(settings.ROOT_URLCONF)
assert urlconf.urlpatterns == []
"""


class TestSettingsCore:
    """``tests/settings_core.py`` stays free of the UI stack — plan.md D-4."""

    def test_boots_with_no_ui_app_and_an_empty_urlconf(self):
        result = subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
            [sys.executable, "-c", _CORE_BOOT_SCRIPT],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    def test_urls_core_module_has_no_routes(self):
        urlconf = import_module("tests.urls_core")
        assert urlconf.urlpatterns == []


class TestSettings:
    """``tests/settings.py`` — the UI stack wired on top of the core-only base."""

    def test_installed_apps_carries_the_ui_stack(self):
        for app in [
            "django.contrib.sites",
            "django.contrib.staticfiles",
            "django_cotton",
            "easy_icons",
            "flex_menu",
            "mvp",
            "literature.ui",
        ]:
            assert app in settings.INSTALLED_APPS

    def test_mvp_config_context_processor_is_wired(self):
        processors = settings.TEMPLATES[0]["OPTIONS"]["context_processors"]
        assert "mvp.context_processors.mvp_config" in processors

    def test_site_id_is_set(self):
        assert settings.SITE_ID == 1

    def test_root_urlconf_is_the_ui_wired_urls_module(self):
        assert settings.ROOT_URLCONF == "tests.urls"

    def test_crispy_is_configured_for_the_packaged_list_template(self):
        # django-mvp's ``list_view.html`` loads ``crispy_forms_tags``, and a tag
        # library resolves only from an installed app. Both arrive with
        # django-mvp as hard dependencies, so this costs no extra install.
        assert "crispy_forms" in settings.INSTALLED_APPS
        assert "crispy_tailwind" in settings.INSTALLED_APPS

    def test_mvp_precedes_crispy_tailwind(self):
        # django-mvp overrides crispy-tailwind's help-text template, and the
        # first app to declare a template path wins.
        apps = settings.INSTALLED_APPS
        assert apps.index("mvp") < apps.index("crispy_tailwind")
        # Both crispy settings are now set (plan.md D-5). This module used to
        # assert each was absent, which was right while the package rendered no
        # form and wrong the moment one rendered: CRISPY_TEMPLATE_PACK has no
        # default and raises, and CRISPY_ALLOWED_TEMPLATE_PACKS is validated
        # against at template-compile time, so leaving it unset stops every
        # template carrying {% crispy %} from compiling at all. Both assertions
        # are deliberately dropped rather than flipped — the Article I decision
        # is plan.md D-5, and T013 already asserts the tailwind pack renders.

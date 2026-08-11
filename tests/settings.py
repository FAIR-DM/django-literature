"""Django settings for the literature test suite, with the opt-in front end wired in.

``tests.settings_core`` is the base — everything a core-only consumer needs —
and this module imports from it and appends the UI stack (plan.md D-4).
"""

from tests.settings_core import *  # noqa: F403

INSTALLED_APPS = [
    *INSTALLED_APPS,  # noqa: F405
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django_cotton",
    "easy_icons",
    "flex_menu",
    "mvp",
    "literature.ui",
]

TEMPLATES[0]["OPTIONS"]["context_processors"] = [  # noqa: F405
    *TEMPLATES[0]["OPTIONS"]["context_processors"],  # noqa: F405
    "mvp.context_processors.mvp_config",
]

SITE_ID = 1

ROOT_URLCONF = "tests.urls"

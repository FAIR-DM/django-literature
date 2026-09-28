"""Django settings for the literature test suite, with the opt-in front end wired in.

``tests.settings_core`` is the base — everything a core-only consumer needs —
and this module imports from it and appends the UI stack (FS-006).
"""

from tests.settings_core import *  # noqa: F403

INSTALLED_APPS = [
    *INSTALLED_APPS,  # noqa: F405
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django_cotton",
    "easy_icons",
    "flex_menu",
    # The tabular catalogue renders through django-tables2. It ships the
    # templatetag library the table component loads, and Django resolves
    # those only from installed apps.
    "django_tables2",
    # The catalogue's search and filter controls render through
    # django-filter, reached through django-mvp's own guarded integration
    # (FS-006).
    "django_filters",
    # ``mvp`` before ``crispy_tailwind``: django-mvp ships an override of
    # crispy-tailwind's help-text template, and the first app to declare a
    # template path wins (django-mvp's getting-started guide).
    "mvp",
    "crispy_forms",
    "crispy_tailwind",
    "literature.ui",
]

# Both required together; see demo/settings.py for why (FS-008).
CRISPY_TEMPLATE_PACK = "tailwind"
CRISPY_ALLOWED_TEMPLATE_PACKS = ["tailwind"]

TEMPLATES[0]["OPTIONS"]["context_processors"] = [  # noqa: F405
    *TEMPLATES[0]["OPTIONS"]["context_processors"],  # noqa: F405
    "mvp.context_processors.mvp_config",
]

SITE_ID = 1

ROOT_URLCONF = "tests.urls"

# Required for any UI page render; see demo/settings.py for why.
STATIC_URL = "static/"

# Required for any page using <c-icon>; see demo/settings.py for why.
EASY_ICONS = {
    "default": {
        "renderer": "easy_icons.renderers.ProviderRenderer",
        "config": {"tag": "i"},
        "packs": ["mvp.utils.BS5_ICONS"],
    },
}

# Required for the shell's sidebar and mobile dock; see demo/settings.py for why.
FLEX_MENUS = {
    "renderers": {
        "sidebar": "mvp.renderers.SidebarRenderer",
        "dock": "mvp.renderers.MobileFooterNavRenderer",
    },
}

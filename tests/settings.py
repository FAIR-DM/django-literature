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
    # ``mvp`` before ``crispy_tailwind``: django-mvp ships an override of
    # crispy-tailwind's help-text template, and the first app to declare a
    # template path wins (django-mvp's getting-started guide).
    "mvp",
    "crispy_forms",
    "crispy_tailwind",
    "literature.ui",
]

# crispy-forms 2.7's get_template_pack() is getattr(settings, "CRISPY_TEMPLATE_PACK")
# with no default, so leaving this unset is an AttributeError on the first form
# render rather than a fallback to another pack (plan.md D-5).
CRISPY_TEMPLATE_PACK = "tailwind"

# And the allowlist has to name it too. The {% crispy %} tag validates the pack
# at TEMPLATE-COMPILE time against CRISPY_ALLOWED_TEMPLATE_PACKS, whose default
# is ("uni_form", "bootstrap3", "bootstrap4") — so every template carrying the
# tag fails to compile, whether or not the tag is given an explicit pack and
# whether or not that branch is the one taken at runtime. django-mvp's own demo
# sets both settings together for the same reason (plan.md D-5).
CRISPY_ALLOWED_TEMPLATE_PACKS = ["tailwind"]

TEMPLATES[0]["OPTIONS"]["context_processors"] = [  # noqa: F405
    *TEMPLATES[0]["OPTIONS"]["context_processors"],  # noqa: F405
    "mvp.context_processors.mvp_config",
]

SITE_ID = 1

ROOT_URLCONF = "tests.urls"

# ``mvp/base.html`` loads the packaged stylesheet with ``{% static %}``
# unconditionally, so any UI page render needs this — django.contrib.staticfiles
# being installed is not enough on its own (research R1).
STATIC_URL = "static/"

# django-mvp resolves every icon name it renders through django-easy-icons;
# without a "default" renderer configured, any page using <c-icon> (which
# mvp/base.html does) raises ImproperlyConfigured (docs/getting-started.md).
EASY_ICONS = {
    "default": {
        "renderer": "easy_icons.renderers.ProviderRenderer",
        "config": {"tag": "i"},
        "packs": ["mvp.utils.BS5_ICONS"],
    },
}

# ``mvp/base.html``'s chrome (sidebar, mobile dock) is rendered by
# django-flex-menus, which raises ValueError at render time without these
# renderers configured (docs/getting-started.md's minimal example).
FLEX_MENUS = {
    "renderers": {
        "sidebar": "mvp.renderers.SidebarRenderer",
        "dock": "mvp.renderers.MobileFooterNavRenderer",
    },
}

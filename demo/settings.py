"""Django settings for the demo / dev server."""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# django.setup() imports every INSTALLED_APPS entry before any command runs, so a missing
# 'ui' extra is caught here rather than as a traceback from deep inside mvp or django_cotton (FS-007).
try:
    import mvp  # noqa: F401
except ImportError:
    sys.stderr.write(
        "The demo needs the front end's dependencies, which are not installed. "
        "Install them with: pip install django-literature[ui] "
        "(or uv sync --extra ui).\n"
    )
    sys.exit(1)

SECRET_KEY = "django-insecure-demo-secret-key-do-not-use-in-production"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# DEMO_DB_PATH points the destructive seed_demo command at a scratch file in a test run (FS-007).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DEMO_DB_PATH", str(BASE_DIR / "demo" / "db.sqlite3")),
    }
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "demo",
    # The front end, wired as the README's "Installing the front end" section documents (FS-007).
    "literature",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django_cotton",
    "easy_icons",
    "flex_menu",
    # Ships the templatetag library the table component loads (README, "The catalogue").
    "django_tables2",
    # The search and filter controls, reached through django-mvp's integration (README).
    "django_filters",
    # Your own apps go above ``mvp`` so their templates win; ``daisy_cotton`` goes below it.
    "mvp",
    "daisy_cotton",
    "crispy_forms",
    "mvp_forms",
    "django_tomselect",
    "literature.ui",
]

# Live reload while developing. Both packages come with the dev dependency group, not
# the `ui` extra, so the demo still starts without them.
try:
    import django_browser_reload  # noqa: F401
    import django_watchfiles  # noqa: F401
except ImportError:
    LIVE_RELOAD = False
else:
    LIVE_RELOAD = True
    INSTALLED_APPS += ["django_watchfiles", "django_browser_reload"]

# crispy-forms has no default pack: leaving this unset is an AttributeError on the first
# form render (FS-008). Shared with tests/settings.py.
CRISPY_TEMPLATE_PACK = "daisyui"

# The {% crispy %} tag checks the pack against this allowlist at template-compile time (FS-008).
CRISPY_ALLOWED_TEMPLATE_PACKS = ["daisyui"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django_tomselect.middleware.TomSelectMiddleware",
]

if LIVE_RELOAD:
    MIDDLEWARE += ["django_browser_reload.middleware.BrowserReloadMiddleware"]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # The shell's site name in every page title needs this (README.md).
                "mvp.context_processors.mvp_config",
            ],
        },
    }
]

ROOT_URLCONF = "demo.urls"

# The demo has no sign-in page of its own, so visitors who are not signed in go to the admin's.
LOGIN_URL = "admin:login"

# mvp/base.html loads its stylesheet with {% static %}, so this must be set (README, tests/settings.py).
STATIC_URL = "static/"

# Where a preview's staged upload lives (FS-011, literature/ui/staging.py); the default
# would be the working directory.
MEDIA_ROOT = BASE_DIR / "demo" / "media"

# Without a "default" icon renderer, any page in the UI app raises ImproperlyConfigured
# (README, tests/settings.py).
EASY_ICONS = {
    "default": {
        "renderer": "easy_icons.renderers.ProviderRenderer",
        "config": {"tag": "i"},
        "packs": ["mvp.utils.BS5_ICONS"],
    },
}

# django-flex-menus raises ValueError at render time without these renderers (README, tests/settings.py).
FLEX_MENUS = {
    "renderers": {
        "sidebar": "mvp.renderers.SidebarRenderer",
        "dock": "mvp.renderers.MobileFooterNavRenderer",
    },
}

# The shell reads the current site through the mvp_config context processor.
SITE_ID = 1

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
USE_I18N = True

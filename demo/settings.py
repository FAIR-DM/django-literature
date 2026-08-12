"""Django settings for the demo / dev server."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-demo-secret-key-do-not-use-in-production"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# DEMO_DB_PATH lets a test run point the destructive seed_demo command at a
# scratch file instead of the developer's real demo database (plan.md D-3).
# With no variable set, the documented start path is unchanged.
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
    # The front end, wired exactly as README.md documents at lines 93-220 (plan.md D-3).
    "literature",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django_cotton",
    "easy_icons",
    "flex_menu",
    # ``mvp`` before ``crispy_tailwind``: django-mvp overrides one of
    # crispy-tailwind's templates and the first app to declare a template
    # path wins (README.md).
    "mvp",
    "crispy_forms",
    "crispy_tailwind",
    "literature.ui",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
]

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

# mvp/base.html loads the packaged stylesheet with {% static %} unconditionally,
# so having django.contrib.staticfiles installed is not enough on its own
# (README.md, tests/settings.py).
STATIC_URL = "static/"

# Every icon the shell renders resolves through django-easy-icons; without a
# "default" renderer configured, opening any page in the UI app raises
# ImproperlyConfigured (README.md, tests/settings.py).
EASY_ICONS = {
    "default": {
        "renderer": "easy_icons.renderers.ProviderRenderer",
        "config": {"tag": "i"},
        "packs": ["mvp.utils.BS5_ICONS"],
    },
}

# The shell's sidebar and mobile navigation are rendered by django-flex-menus,
# which raises ValueError at render time without these renderers configured
# (README.md, tests/settings.py).
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

"""Minimal Django settings for the literature test suite — the core-only base.

This is the base ``tests/settings.py`` imports from and appends the opt-in
front end to, not a copy of it (plan.md D-4). Its own ``ROOT_URLCONF`` points
at an empty urlconf, and it stays free of ``literature.ui`` and every UI
dependency — it is what the core-only boot test (T016) boots against to
prove the core still starts with nothing UI installed.
"""

SECRET_KEY = "django-insecure-test-secret-key-for-tests-only"

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
    # A second alias, used by the import tests that route ``literature`` models
    # away from ``default``. This package is a reusable app, so the project
    # installing it chooses the routing, and a transaction opened on the wrong
    # connection is invisible until it fails to roll anything back.
    "secondary": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "literature",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

ROOT_URLCONF = "tests.urls_core"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
USE_I18N = True

"""Tests for ``literature/ui/apps.py`` and ``literature/ui/__init__.py``."""

import ast
import subprocess
import sys
from pathlib import Path

INIT_PATH = Path(__file__).resolve().parents[2] / "literature" / "ui" / "__init__.py"

# A host installs ``literature.ui`` alongside the core app. Run in a fresh
# subprocess, never the pytest process itself: ``django.setup()`` only ever
# runs once per interpreter, and the pytest session has already populated the
# app registry from ``tests.settings`` before this test executes.
BOOT_SCRIPT = """
import django
from django.conf import settings

settings.configure(
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "literature",
        "literature.ui",
    ],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
)
django.setup()

from django.apps import apps

config = apps.get_app_config("literature_ui")
assert config.name == "literature.ui"
"""


class TestLiteratureUIConfig:
    def test_app_registry_populates_without_app_registry_not_ready(self):
        result = subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
            [sys.executable, "-c", BOOT_SCRIPT],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


class TestLiteratureUIInit:
    # Imported during app-registry phase 1, so any statement here runs before the
    # registry is ready.

    def test_init_module_is_a_docstring_and_nothing_else(self):
        tree = ast.parse(INIT_PATH.read_text())
        assert len(tree.body) == 1
        (statement,) = tree.body
        assert isinstance(statement, ast.Expr)
        assert isinstance(statement.value, ast.Constant)
        assert isinstance(statement.value.value, str)

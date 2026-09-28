"""Tests proving the core boots and passes system checks with the UI app absent.

A static import scan cannot see a runtime dependency, so this boots ``tests.settings_core`` in a
fresh subprocess: ``django.setup()`` runs once per interpreter and pytest has already loaded the
UI stack. ``DJANGO_SETTINGS_MODULE`` is set inside the script because pytest-django exports its
own value into the inherited environment.
"""

import subprocess
import sys
from pathlib import Path

LITERATURE_ROOT = Path(__file__).resolve().parents[2] / "literature"
UI_ROOT = LITERATURE_ROOT / "ui"


def core_module_names():
    """Every importable dotted module name under ``literature/``, excluding ``literature.ui``.

    Migration filenames such as ``0001_initial`` are not valid Python
    identifiers, so the subprocess script below imports each name with
    ``importlib.import_module`` rather than a literal ``import`` statement.
    """
    names = []
    for path in sorted(LITERATURE_ROOT.rglob("*.py")):
        if UI_ROOT in path.parents:
            continue
        parts = list(path.relative_to(LITERATURE_ROOT.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        names.append(".".join(parts))
    return names


BOOT_SCRIPT_TEMPLATE = """
import importlib
import os
import sys

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings_core"
import django
django.setup()

from django.core.management import call_command
call_command("check")

for name in {module_names!r}:
    importlib.import_module(name)

assert "literature.ui" not in sys.modules, "literature.ui was imported by the core boot"
print("BOOT_OK")
"""


class TestCoreBootsWithNoUIAppInstalled:
    def test_core_boots_checks_clean_and_imports_every_core_module(self):
        script = BOOT_SCRIPT_TEMPLATE.format(module_names=core_module_names())
        result = subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "BOOT_OK" in result.stdout

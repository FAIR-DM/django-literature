"""The core-only boot test — plan.md D-4, third proof.

A static import scan (``test_architecture.py``) cannot see a *runtime*
dependency: a module that never names ``mvp`` in an import statement but
would still explode if the UI stack were absent from ``INSTALLED_APPS`` (for
example, a template that ``{% extends %}`` a UI base only reachable once the
app is registered). This test proves the core actually boots — ``django.setup()``
*and* the system check framework — against ``tests.settings_core``, then
imports every module under ``literature/`` except ``literature.ui``.

Run in a fresh subprocess, never the pytest process itself: ``django.setup()``
only ever runs once per interpreter, and the pytest session has already
populated the app registry from ``tests.settings`` (which *does* install the
UI stack) before this test executes. Calling it a second time in-process would
not exercise a clean, UI-free app registry at all — it would raise
``RuntimeError: populated apps aren't allowed`` from the settings already
loaded, or silently reuse them. ``DJANGO_SETTINGS_MODULE`` is forced inside
the subprocess script itself, not read from the parent's exported environment
variable: pytest-django exports ``DJANGO_SETTINGS_MODULE=tests.settings`` into
the environment, and this subprocess inherits it by default.

There is no ``literature/ui/boot.py`` for this to mirror — the subject is the
core package as a whole, booted with the UI app absent — so this file is one
of the standing non-mirror exceptions (T025 extends
``[tool.forge.conformance] non-mirror-paths`` with it; see decisions.md D13).
"""

import subprocess
import sys
from pathlib import Path

LITERATURE_ROOT = Path(__file__).resolve().parents[2] / "literature"
UI_ROOT = LITERATURE_ROOT / "ui"


def _core_module_names():
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


_BOOT_SCRIPT_TEMPLATE = """
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
    """FR-006, SC-009 — the core still boots and passes system checks with nothing UI installed."""

    def test_core_boots_checks_clean_and_imports_every_core_module(self):
        script = _BOOT_SCRIPT_TEMPLATE.format(module_names=_core_module_names())
        result = subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "BOOT_OK" in result.stdout

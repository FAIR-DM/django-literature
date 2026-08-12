"""Tests proving the core imports nothing from the opt-in front end.

The subject is every module under ``literature/`` outside ``literature/ui/``,
not a single source module — like ``test_smoke.py`` and unlike most of this
tree, there is no ``literature/ui/architecture.py`` to mirror against, so this
file is one of the standing non-mirror exceptions (T025 extends
``[tool.forge.conformance] non-mirror-paths`` with it; see decisions.md D13).
"""

import ast
from pathlib import Path

import pytest

LITERATURE_ROOT = Path(__file__).resolve().parents[2] / "literature"
UI_ROOT = LITERATURE_ROOT / "ui"

FORBIDDEN_ROOTS = ("mvp", "django_cotton", "crispy_forms", "easy_icons", "flex_menu", "literature.ui")


def _core_modules():
    return [path for path in sorted(LITERATURE_ROOT.rglob("*.py")) if UI_ROOT not in path.parents]


def _imported_names(path):
    """Every dotted name this module's import statements name.

    Parsed rather than grepped, so a forbidden name inside a docstring or a
    comment cannot fail the test and a real import cannot hide in one.
    """
    tree = ast.parse(path.read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


class TestCoreImportsNothingFromTheUIStack:
    """FR-006 — no core module names ``mvp``, its dependencies, or ``literature.ui``."""

    @pytest.mark.parametrize(
        "path",
        _core_modules(),
        ids=lambda p: str(p.relative_to(LITERATURE_ROOT)),
    )
    def test_module_imports_no_ui_dependency(self, path):
        imported = _imported_names(path)
        offending = {
            name
            for name in imported
            if any(name == forbidden or name.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_ROOTS)
        }
        assert not offending, f"{path} imports forbidden module(s): {offending}"

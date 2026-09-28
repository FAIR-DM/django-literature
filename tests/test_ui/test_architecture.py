"""Tests proving the core imports nothing from the opt-in front end.

The subject is every module outside ``literature/ui/``, so there is no single module to mirror.
"""

import ast
from pathlib import Path

import pytest

LITERATURE_ROOT = Path(__file__).resolve().parents[2] / "literature"
UI_ROOT = LITERATURE_ROOT / "ui"

FORBIDDEN_ROOTS = (
    "mvp",
    "django_cotton",
    "crispy_forms",
    "easy_icons",
    "flex_menu",
    "django_tables2",
    "django_filters",
    "literature.ui",
)


def core_modules():
    return [
        path
        for path in sorted(LITERATURE_ROOT.rglob("*.py"))
        if UI_ROOT not in path.parents
    ]


def imported_names(path):
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
    @pytest.mark.parametrize(
        "path",
        core_modules(),
        ids=lambda p: str(p.relative_to(LITERATURE_ROOT)),
    )
    def test_module_imports_no_ui_dependency(self, path):
        imported = imported_names(path)
        offending = {
            name
            for name in imported
            if any(
                name == forbidden or name.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_ROOTS
            )
        }
        assert not offending, f"{path} imports forbidden module(s): {offending}"


class TestSearchAndFilterAreDeclaredOnce:
    def test_views_module_imports_search_fields_and_filterset_rather_than_declaring_them(
        self,
    ):
        views_path = UI_ROOT / "views.py"
        imported = imported_names(views_path)
        assert "literature.ui.filters.SEARCH_FIELDS" in imported
        assert "literature.ui.filters.ItemFilterSet" in imported

        tree = ast.parse(views_path.read_text())
        top_level_assignments = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        class_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        }
        assert "SEARCH_FIELDS" not in top_level_assignments, (
            "SEARCH_FIELDS is declared again in views.py"
        )
        assert "ItemFilterSet" not in class_names, (
            "ItemFilterSet is declared again in views.py"
        )

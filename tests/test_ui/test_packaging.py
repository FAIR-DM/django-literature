"""Tests proving django-mvp only ever arrives through the opt-in `ui` extra.

There is no ``literature/ui/packaging.py`` to mirror against — the subject is
``pyproject.toml`` itself — so this file is one of the standing non-mirror
exceptions (T025 extends ``[tool.forge.conformance] non-mirror-paths`` with
it; see decisions.md D13).
"""

import tomllib
from pathlib import Path

PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _load_pyproject():
    return tomllib.loads(PYPROJECT_PATH.read_text())


def _names_django_mvp(requirement):
    """A PEP 508 requirement string names django-mvp if it starts with the
    package name, ignoring any version specifier or environment marker."""
    return requirement.split(";")[0].split("(")[0].strip().split()[0].lower() == "django-mvp"


class TestDjangoMVPIsOptOnly:
    """FR-002 — installing the core alone resolves no front-end dependency."""

    def test_django_mvp_is_declared_in_the_ui_extra(self):
        pyproject = _load_pyproject()
        ui_extra = pyproject["project"]["optional-dependencies"]["ui"]
        assert any(_names_django_mvp(requirement) for requirement in ui_extra)

    def test_django_mvp_is_absent_from_the_hard_dependency_list(self):
        pyproject = _load_pyproject()
        dependencies = pyproject["project"]["dependencies"]
        assert not any(_names_django_mvp(requirement) for requirement in dependencies)

    def test_django_mvp_is_absent_from_every_other_optional_dependency_list(self):
        pyproject = _load_pyproject()
        extras = pyproject["project"]["optional-dependencies"]
        for extra_name, requirements in extras.items():
            if extra_name == "ui":
                continue
            assert not any(_names_django_mvp(requirement) for requirement in requirements)

    def test_django_mvp_is_absent_from_every_poetry_dependency_group(self):
        pyproject = _load_pyproject()
        groups = pyproject.get("tool", {}).get("poetry", {}).get("group", {})
        for group_name, group in groups.items():
            dependencies = group.get("dependencies", {})
            assert "django-mvp" not in dependencies, f"django-mvp found in poetry group '{group_name}'"

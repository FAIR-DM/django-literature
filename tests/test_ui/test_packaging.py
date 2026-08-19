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


class TestOnlyLiteratureIsPackaged:
    """FR-023 — the built distribution contains neither the demo project nor
    its seed catalogue, because the packages declaration names nothing else."""

    def test_the_packages_declaration_includes_only_literature(self):
        pyproject = _load_pyproject()
        assert pyproject["tool"]["poetry"]["packages"] == [{"include": "literature"}]


class TestNoDemoOnlyDependencyEntersTheBuild:
    """FR-024 — the demo adds no runtime dependency to the package, and
    nothing existing only for the demo is resolved by a project installing
    it. Both dependency lists are pinned to their known-good contents, so
    any addition — whatever it is for — fails here first."""

    def test_the_hard_dependency_list_is_exactly_the_declared_runtime_dependencies(self):
        pyproject = _load_pyproject()
        dependencies = pyproject["project"]["dependencies"]
        assert dependencies == [
            "django>=4.2",
            "django-partial-date",
            "bibtexparser (>=1.4.4,<2)",
        ]

    def test_the_ui_extra_is_exactly_the_front_end_packages(self):
        pyproject = _load_pyproject()
        ui_extra = pyproject["project"]["optional-dependencies"]["ui"]
        assert ui_extra == [
            "django-mvp (>=0.19,<1.0) ; python_version >= '3.12'",
            "django-tables2 (>=3.0,<4) ; python_version >= '3.12'",
        ]

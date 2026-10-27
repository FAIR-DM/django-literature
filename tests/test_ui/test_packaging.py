"""Tests proving django-mvp only ever arrives through the opt-in ``ui`` extra."""

import tomllib
from pathlib import Path

PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def load_pyproject():
    return tomllib.loads(PYPROJECT_PATH.read_text())


def names_django_mvp(requirement):
    """Return whether a PEP 508 requirement string names django-mvp."""
    return (
        requirement.split(";")[0].split("(")[0].strip().split()[0].lower()
        == "django-mvp"
    )


class TestDjangoMVPIsOptOnly:
    def test_django_mvp_is_declared_in_the_ui_extra(self):
        pyproject = load_pyproject()
        ui_extra = pyproject["project"]["optional-dependencies"]["ui"]
        assert any(names_django_mvp(requirement) for requirement in ui_extra)

    def test_django_mvp_is_absent_from_the_hard_dependency_list(self):
        pyproject = load_pyproject()
        dependencies = pyproject["project"]["dependencies"]
        assert not any(names_django_mvp(requirement) for requirement in dependencies)

    def test_django_mvp_is_absent_from_every_other_optional_dependency_list(self):
        pyproject = load_pyproject()
        extras = pyproject["project"]["optional-dependencies"]
        for extra_name, requirements in extras.items():
            if extra_name == "ui":
                continue
            assert not any(
                names_django_mvp(requirement) for requirement in requirements
            )

    def test_django_mvp_is_absent_from_every_dependency_group(self):
        pyproject = load_pyproject()
        groups = pyproject.get("dependency-groups", {})
        for group_name, requirements in groups.items():
            for requirement in requirements:
                if not isinstance(requirement, str):
                    continue
                assert not names_django_mvp(requirement), (
                    f"django-mvp found in dependency group '{group_name}'"
                )


class TestOnlyLiteratureIsPackaged:
    def test_the_packages_declaration_includes_only_literature(self):
        pyproject = load_pyproject()
        wheel = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
        assert wheel["packages"] == ["literature"]

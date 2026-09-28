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


class TestNoDemoOnlyDependencyEntersTheBuild:
    def test_the_hard_dependency_list_is_exactly_the_declared_runtime_dependencies(
        self,
    ):
        pyproject = load_pyproject()
        dependencies = pyproject["project"]["dependencies"]
        assert dependencies == [
            "django>=4.2",
            "django-partial-date",
            "bibtexparser (>=1.4.4,<2)",
        ]

    def test_the_ui_extra_is_exactly_the_front_end_packages(self):
        pyproject = load_pyproject()
        ui_extra = pyproject["project"]["optional-dependencies"]["ui"]
        # The django-mvp floor is 0.19.3 for the inline formset
        # machinery the reference form composes its related rows from; the
        # pinned list moves with it, as it did at 0.19.1.
        assert ui_extra == [
            "django-mvp (>=0.19.3,<1.0) ; python_version >= '3.12'",
            "django-tables2 (>=3.0,<4) ; python_version >= '3.12'",
            "django-filter (>=26.1,<27) ; python_version >= '3.12'",
        ]

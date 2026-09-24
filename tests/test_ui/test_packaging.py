"""Tests proving django-mvp only ever arrives through the opt-in `ui` extra.

There is no ``literature/ui/packaging.py`` to mirror against — the subject is
how the package is assembled, ``pyproject.toml`` and the wheel built from it —
so this file is one of the standing non-mirror exceptions (T025 extends
``[tool.forge.conformance] non-mirror-paths`` with it; see decisions.md D13).
"""

import subprocess
import tomllib
from email.parser import Parser
from pathlib import Path
from zipfile import ZipFile

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

#: The packages a project installing ``django-literature`` resolves.
RUNTIME_PACKAGES = {"bibtexparser", "django", "django-partial-date"}

#: The packages the opt-in ``ui`` extra adds on top of those.
UI_EXTRA_PACKAGES = {"django-filter", "django-mvp", "django-tables2"}


def load_pyproject():
    return tomllib.loads(PYPROJECT_PATH.read_text())


def names_in(requirements):
    """The distribution names a list of PEP 508 requirement strings refers to,
    normalized so that ``Django`` and ``django`` are the same package."""
    return {canonicalize_name(Requirement(text).name) for text in requirements}


@pytest.fixture(scope="session")
def built_package(tmp_path_factory):
    """The metadata of a wheel built from the working tree.

    A wheel's ``Requires-Dist`` lines are what a project installing this
    package actually resolves, so the guards below read the artefact rather
    than the declaration that produced it. Building costs about a second and
    happens once for the whole session.
    """
    output_dir = tmp_path_factory.mktemp("wheel")
    build = subprocess.run(
        ["poetry", "build", "--format", "wheel", "--output", str(output_dir)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        pytest.fail(f"building the wheel failed:\n{build.stdout}{build.stderr}")
    (wheel,) = output_dir.glob("*.whl")
    with ZipFile(wheel) as archive:
        (metadata_name,) = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        return Parser().parsestr(archive.read(metadata_name).decode())


def required_names(metadata, extra=None):
    """The distribution names the built package requires — those a plain
    install resolves when ``extra`` is ``None``, or those one named extra adds.
    """
    names = set()
    for line in metadata.get_all("Requires-Dist") or []:
        requirement = Requirement(line)
        marker = str(requirement.marker or "")
        if extra is None:
            if "extra ==" in marker:
                continue
        elif f'extra == "{extra}"' not in marker:
            continue
        names.add(canonicalize_name(requirement.name))
    return names


def names_django_mvp(requirement):
    """A PEP 508 requirement string names django-mvp if it starts with the
    package name, ignoring any version specifier or environment marker."""
    return (
        requirement.split(";")[0].split("(")[0].strip().split()[0].lower()
        == "django-mvp"
    )


class TestDjangoMVPIsOptOnly:
    """FR-002 — installing the core alone resolves no front-end dependency."""

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
    """FR-023 — the built distribution contains neither the demo project nor
    its seed catalogue, because the packages declaration names nothing else."""

    def test_the_packages_declaration_includes_only_literature(self):
        pyproject = load_pyproject()
        wheel = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
        assert wheel["packages"] == ["literature"]


class TestNoDemoOnlyDependencyEntersTheBuild:
    """FR-024 — the demo adds no runtime dependency to the package, and
    nothing existing only for the demo is resolved by a project installing it.

    The guard is a closed set of package *names*: a project installing this
    package resolves those and nothing else, so a newcomer fails here whatever
    it was added for, and no list of forbidden names has to be kept up to date
    (decisions.md D13). Version specifiers are deliberately outside the
    assertion — raising a floor on a package already in the set changes which
    release is resolved, never which packages are, and that is the question
    these tests ask.
    """

    def test_a_plain_install_resolves_only_the_declared_runtime_packages(
        self, built_package
    ):
        assert required_names(built_package) == RUNTIME_PACKAGES

    def test_the_ui_extra_adds_only_the_front_end_packages(self, built_package):
        assert required_names(built_package, extra="ui") == UI_EXTRA_PACKAGES

    def test_the_built_package_requires_what_pyproject_declares(self, built_package):
        pyproject = load_pyproject()
        assert required_names(built_package) == names_in(
            pyproject["project"]["dependencies"]
        )
        assert required_names(built_package, extra="ui") == names_in(
            pyproject["project"]["optional-dependencies"]["ui"]
        )

    def test_no_development_only_package_is_resolved_by_installing_it(
        self, built_package
    ):
        """The demo, the test tooling and the documentation build are declared
        in Poetry groups, which never reach an installing project. Reading the
        groups rather than naming packages keeps this true as they change."""
        groups = load_pyproject()["tool"]["poetry"].get("group", {})
        development_only = {
            canonicalize_name(name)
            for group in groups.values()
            for name in group.get("dependencies", {})
        }
        assert development_only, "no development-only packages left to check against"
        assert development_only.isdisjoint(required_names(built_package))
        assert development_only.isdisjoint(required_names(built_package, extra="ui"))

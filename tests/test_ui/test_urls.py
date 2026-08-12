"""Tests for ``literature/ui/urls.py``."""

import ast
from pathlib import Path

import pytest
from django.test import override_settings
from django.urls import include, path, reverse

URLS_PATH = Path(__file__).resolve().parents[2] / "literature" / "ui" / "urls.py"


def _urlconf():
    """A URLconf mounting the app at a prefix, the way a host would."""
    patterns = [path("catalogue/", include("literature.ui.urls"))]
    return type("_URLConf", (), {"urlpatterns": patterns})


class TestURLs:
    """``literature/ui/urls.py`` — FR-003, FR-019, FR-032."""

    @pytest.mark.parametrize(
        ("name", "kwargs", "expected"),
        [
            ("literature:item-list", {}, "/catalogue/"),
            ("literature:item-detail", {"pk": 1}, "/catalogue/1/"),
            ("literature:contributor-detail", {"pk": 1}, "/catalogue/contributors/1/"),
        ],
    )
    def test_route_reverses_under_the_mounted_prefix(self, name, kwargs, expected):
        with override_settings(ROOT_URLCONF=_urlconf()):
            assert reverse(name, kwargs=kwargs) == expected

    def test_importing_urls_has_no_import_time_side_effect_on_the_core(self):
        """Parsed rather than imported-and-inspected: an import statement naming
        ``literature`` is the failure mode, whether or not it is ever reached."""
        tree = ast.parse(URLS_PATH.read_text())
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        assert "literature" not in imported_roots

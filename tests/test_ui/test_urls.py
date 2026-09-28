"""Tests for ``literature/ui/urls.py``."""

import ast
from pathlib import Path

import pytest
from django.test import override_settings
from django.urls import include, path, resolve, reverse

from literature.models import Item
from literature.ui import views
from literature.ui.catalogue import catalogue, catalogue_view_class

URLS_PATH = Path(__file__).resolve().parents[2] / "literature" / "ui" / "urls.py"


def urlconf():
    """A URLconf mounting the app at a prefix, the way a host would."""
    patterns = [path("catalogue/", include("literature.ui.urls"))]
    return type("URLConf", (), {"urlpatterns": patterns})


class TestURLs:
    @pytest.mark.parametrize(
        ("name", "kwargs", "expected"),
        [
            ("literature:item-list", {}, "/catalogue/"),
            ("literature:item-detail", {"pk": 1}, "/catalogue/1/"),
            ("literature:contributor-detail", {"pk": 1}, "/catalogue/contributors/1/"),
        ],
    )
    def test_route_reverses_under_the_mounted_prefix(self, name, kwargs, expected):
        with override_settings(ROOT_URLCONF=urlconf()):
            assert reverse(name, kwargs=kwargs) == expected

    def test_the_catalogue_route_serves_the_table_by_default(self):
        # The package's documented catalogue route serves the table
        # with no configuration. The route resolves to the one view in this
        # app a project may choose, which picks its class per
        # request; which class it picks, and how a project changes it, is
        # tests/test_ui/test_catalogue.py's.
        with override_settings(ROOT_URLCONF=urlconf()):
            assert resolve("/catalogue/").func is catalogue
        assert catalogue_view_class() is views.ItemTableView

    def test_importing_urls_has_no_import_time_side_effect_on_the_core(self):
        tree = ast.parse(URLS_PATH.read_text())
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        assert "literature" not in imported_roots


class TestCreateRouteReverses:
    def test_item_create_reverses(self):
        assert reverse("literature:item-create") == "/catalogue/add/"


class TestUpdateRouteReverses:
    def test_item_update_reverses(self):
        assert (
            reverse("literature:item-update", kwargs={"pk": 1})
            == "/catalogue/1/update/"
        )


class TestDeleteRouteReverses:
    def test_item_delete_reverses(self):
        assert (
            reverse("literature:item-delete", kwargs={"pk": 1})
            == "/catalogue/1/delete/"
        )


class TestImportRouteReverses:
    def test_item_import_reverses(self):
        assert reverse("literature:item-import") == "/catalogue/import/"

    def test_item_import_resolves_to_the_import_view(self):
        assert resolve("/catalogue/import/").func.view_class is views.ItemImportView


class TestImportPreviewAndRestartRoutesReverse:
    def test_item_import_preview_reverses(self):
        assert reverse("literature:item-import-preview") == "/catalogue/import/preview/"

    def test_item_import_preview_resolves_to_the_preview_view(self):
        assert (
            resolve("/catalogue/import/preview/").func.view_class
            is views.ItemImportPreviewView
        )

    def test_item_import_restart_reverses(self):
        assert reverse("literature:item-import-restart") == "/catalogue/import/restart/"

    def test_item_import_restart_resolves_to_the_restart_view(self):
        assert (
            resolve("/catalogue/import/restart/").func.view_class
            is views.ItemImportRestartView
        )


class TestCRUDViewsReverse:
    # A shown action with no route raises NoReverseMatch at render, so this is driven by
    # each view's show_<action>_action flags rather than a hand-picked list.

    @pytest.mark.parametrize(
        "view_class",
        [
            views.ItemListView,
            views.ItemTableView,
            views.ItemDetailView,
            views.ItemCreateView,
            views.ItemUpdateView,
            views.ItemDeleteView,
        ],
        ids=lambda view_class: view_class.__name__,
    )
    def test_every_action_the_view_shows_reverses(self, view_class):
        model_meta = Item._meta
        shown_actions = [
            action
            for action in view_class.crud_views
            if getattr(view_class, f"show_{action}_action", False)
        ]
        assert shown_actions, f"{view_class.__name__} shows no CRUD action to test"
        for action in shown_actions:
            url_name = view_class.crud_views[action].format(
                model_name=model_meta.model_name, app_name=model_meta.app_label
            )
            # Like "list"/"create", "import" names no object, so it takes no pk.
            kwargs = {} if action in {"list", "create", "import"} else {"pk": 1}
            reverse(
                url_name, kwargs=kwargs
            )  # raises NoReverseMatch if the action is not registered

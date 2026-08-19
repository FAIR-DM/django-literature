"""Tests for ``literature/ui/urls.py``."""

import ast
from pathlib import Path

import pytest
from django.test import override_settings
from django.urls import include, path, resolve, reverse

from literature.models import Item
from literature.ui import views

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

    def test_the_catalogue_route_serves_the_table_by_default(self):
        # FR-021 — the package's documented catalogue route serves the table
        # with no configuration; the card stays reachable as a routable
        # class of its own (plan.md D-1), never at this route.
        with override_settings(ROOT_URLCONF=_urlconf()):
            assert resolve("/catalogue/").func.view_class is views.ItemTableView

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


class TestCreateRouteReverses:
    """T007/T008 — the create flow's route, added by US-1 (plan.md D-6, D-8)."""

    def test_item_create_reverses(self):
        assert reverse("literature:item-create") == "/catalogue/add/"


class TestUpdateRouteReverses:
    """T017 — the update flow's route, added by US-2 (plan.md D-6, D-8)."""

    def test_item_update_reverses(self):
        assert reverse("literature:item-update", kwargs={"pk": 1}) == "/catalogue/1/update/"


class TestDeleteRouteReverses:
    """T020 — the delete flow's route, added by US-3 (plan.md D-6, D-8)."""

    def test_item_delete_reverses(self):
        assert reverse("literature:item-delete", kwargs={"pk": 1}) == "/catalogue/1/delete/"


class TestCRUDViewsReverse:
    """plan.md D-6 — an action a view *shows* must have a resolvable route, or
    ``get_breadcrumbs()`` raises ``NoReverseMatch`` at render time instead of
    the button simply not appearing. Checking every ``show_<action>_action``
    against ``crud_views`` (rather than listing action names by hand) is what
    DR-006 fixed: a partial per-view override could pass a hand-picked
    subset while still breaking on the action it left out.

    Every view that carries ``crud_views`` is in the list below, including
    ``ItemDeleteView``. The check is deliberately driven by each view's own
    ``show_<action>_action`` flags rather than by a fixed set of action names,
    so a view that switches an action on without a route to match fails here
    rather than at render time.
    """

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
            action for action in view_class.crud_views if getattr(view_class, f"show_{action}_action", False)
        ]
        assert shown_actions, f"{view_class.__name__} shows no CRUD action to test"
        for action in shown_actions:
            url_name = view_class.crud_views[action].format(
                model_name=model_meta.model_name, app_name=model_meta.app_label
            )
            kwargs = {} if action in {"list", "create"} else {"pk": 1}
            reverse(url_name, kwargs=kwargs)  # raises NoReverseMatch if the action is not registered

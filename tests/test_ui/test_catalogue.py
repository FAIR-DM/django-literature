"""Tests for ``literature/ui/catalogue.py`` — which view the catalogue route serves.

US-4 (FR-022, FR-027). ``TestTheCardListStaysAvailable`` in
``test_views.py`` asserts that the card view still works when a URL is
pointed straight at it. This module asserts the mechanism a project
actually uses to choose it: the ``LITERATURE["CATALOGUE_VIEW"]`` setting,
read on the one route whose view is a project's to pick.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from literature.ui.catalogue import catalogue_view_class
from literature.ui.views import ItemListView, ItemTableView
from tests.factories import ItemFactory

CARD_VIEW = "literature.ui.views.ItemListView"


class ItemTableViewSubclass(ItemTableView):
    """A project's own subclass, to prove the setting takes any view and not
    only the two paths this package ships."""

    paginate_by = 5


class TestTheDefault:
    """The table is what a project gets with nothing configured (FR-021)."""

    def test_no_setting_at_all_resolves_to_the_table(self):
        assert catalogue_view_class() is ItemTableView

    def test_the_setting_present_without_the_key_resolves_to_the_table(self, settings):
        settings.LITERATURE = {"BIB_FORMATS": []}

        assert catalogue_view_class() is ItemTableView

    def test_the_catalogue_route_renders_a_table(self, client, db):
        ItemFactory(title="A Table-Rendered Reference")
        content = client.get(reverse("literature:item-list")).content.decode()

        assert "<table" in content
        assert "A Table-Rendered Reference" in content


class TestChoosingTheCardList:
    """The documented way to prefer cards (FR-022)."""

    def test_the_setting_resolves_to_the_card_view(self, settings):
        settings.LITERATURE = {"CATALOGUE_VIEW": CARD_VIEW}

        assert catalogue_view_class() is ItemListView

    def test_the_catalogue_route_then_renders_cards(self, client, db, settings):
        settings.LITERATURE = {"CATALOGUE_VIEW": CARD_VIEW}
        ItemFactory(title="A Card-Rendered Reference")
        content = client.get(reverse("literature:item-list")).content.decode()

        # "<table" is unique to django-tables2's own template — nothing in
        # the card's chain renders one, so its absence tells the two
        # presentations apart directly.
        assert "<table" not in content
        assert "A Card-Rendered Reference" in content

    def test_every_other_route_still_reverses_and_resolves(self, client, db, settings):
        # The failure this mechanism exists to avoid. Every route in this
        # app shares one namespace through one include(), so selecting the
        # card list by registering a second include() over the list route
        # breaks reverse() for the app's other routes. Choosing it behind
        # the route name cannot: the create action rendered on the card page
        # below is reversed from inside the view that the setting selected.
        settings.LITERATURE = {"CATALOGUE_VIEW": CARD_VIEW}
        item = ItemFactory()

        content = client.get(reverse("literature:item-list")).content.decode()
        assert f'href="{reverse("literature:item-create")}"' in content

        for name, kwargs in (
            ("literature:item-detail", {"pk": item.pk}),
            ("literature:item-update", {"pk": item.pk}),
            ("literature:item-delete", {"pk": item.pk}),
            ("literature:item-create", {}),
        ):
            assert client.get(reverse(name, kwargs=kwargs)).status_code == 200

    def test_a_project_can_name_its_own_subclass(self, client, db, settings):
        settings.LITERATURE = {"CATALOGUE_VIEW": "tests.test_ui.test_catalogue.ItemTableViewSubclass"}
        ItemFactory.create_batch(8)

        assert catalogue_view_class() is ItemTableViewSubclass
        # The subclass's own page size, not ItemTableView's 24 — proof the
        # route served the configured class rather than its parent.
        assert client.get(reverse("literature:item-list")).context["page_obj"].paginator.per_page == 5


class TestAMisconfiguredSetting:
    """Named at the setting, not left to surface as a raw error from inside
    URL resolution — the same grounds as ``literature.importers.config``."""

    def test_a_literature_setting_that_is_not_a_dict_is_reported(self, settings):
        settings.LITERATURE = [CARD_VIEW]

        with pytest.raises(ImproperlyConfigured, match="LITERATURE must be a dict"):
            catalogue_view_class()

    def test_a_value_that_is_not_a_dotted_path_is_reported(self, settings):
        settings.LITERATURE = {"CATALOGUE_VIEW": ItemListView}

        with pytest.raises(ImproperlyConfigured, match="must be a dotted path"):
            catalogue_view_class()

    def test_a_path_that_does_not_import_is_reported(self, settings):
        settings.LITERATURE = {"CATALOGUE_VIEW": "literature.ui.views.NoSuchView"}

        with pytest.raises(ImproperlyConfigured, match="could not be imported"):
            catalogue_view_class()

    def test_a_path_that_is_not_a_view_is_reported(self, settings):
        settings.LITERATURE = {"CATALOGUE_VIEW": "literature.ui.views.CATALOGUE_TITLE"}

        with pytest.raises(ImproperlyConfigured, match="is not a class-based view"):
            catalogue_view_class()

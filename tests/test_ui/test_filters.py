"""Tests for ``literature/ui/filters.py`` — plan D-1, D-3."""

import pytest

from literature.models import Item
from literature.ui.filters import SEARCH_FIELDS


class TestSearchFields:
    """FR-002: the eight ORM paths a search matches against, and nothing else."""

    def test_is_exactly_the_eight_declared_paths(self):
        assert SEARCH_FIELDS == [
            "citation_key",
            "title",
            "title_short",
            "original_title",
            "container_title",
            "item_names__name__family",
            "item_names__name__given",
            "item_names__name__literal",
        ]

    @pytest.mark.parametrize("path", SEARCH_FIELDS)
    def test_every_path_resolves_against_the_model(self, path):
        # Building the filter (never evaluating it) is enough: Django
        # resolves an ORM lookup path into fields at .filter()-call time, so
        # a renamed field raises FieldError here rather than as a silently
        # empty search once this list is wired into a view.
        Item.objects.filter(**{f"{path}__icontains": "x"})

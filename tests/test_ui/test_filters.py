"""Tests for ``literature/ui/filters.py`` — plan D-1, D-3, D-4, D-5."""

import pytest

from literature.choices import DateType, ItemType, NameRole
from literature.models import Item
from literature.ui.filters import SEARCH_FIELDS, ItemFilterSet
from tests.factories import ItemDateFactory, ItemFactory, ItemNameFactory, NameFactory


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


@pytest.mark.django_db
class TestItemFilterSetType:
    """FR-010: item type offers translatable labels and narrows on the stored value."""

    def test_narrows_to_the_chosen_type(self):
        book = ItemFactory(type=ItemType.BOOK)
        ItemFactory(type=ItemType.ARTICLE_JOURNAL)
        filterset = ItemFilterSet(data={"type": ItemType.BOOK}, queryset=Item.objects.all())
        assert list(filterset.qs) == [book]

    def test_choices_are_the_translatable_type_labels(self):
        filterset = ItemFilterSet(data={}, queryset=Item.objects.all())
        choices = list(filterset.filters["type"].field.choices)
        assert (ItemType.BOOK, ItemType.BOOK.label) in choices


@pytest.mark.django_db
class TestItemFilterSetContributor:
    """FR-011: matches family, given or literal in any role."""

    def test_matches_a_family_name_fragment(self):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(family="Darwin"))
        other = ItemFactory()
        ItemNameFactory(item=other, name=NameFactory(family="Wallace"))
        filterset = ItemFilterSet(data={"contributor": "darwin"}, queryset=Item.objects.all())
        assert list(filterset.qs) == [item]

    def test_matches_a_given_name_fragment(self):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(given="Charles"))
        filterset = ItemFilterSet(data={"contributor": "charles"}, queryset=Item.objects.all())
        assert item in filterset.qs

    def test_matches_a_literal_organizational_name(self):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(family="", given="", literal="Smithsonian Institution"))
        filterset = ItemFilterSet(data={"contributor": "smithsonian"}, queryset=Item.objects.all())
        assert item in filterset.qs

    def test_matches_a_contributor_regardless_of_role(self):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(family="Darwin"), role=NameRole.EDITOR)
        filterset = ItemFilterSet(data={"contributor": "darwin"}, queryset=Item.objects.all())
        assert item in filterset.qs


@pytest.mark.django_db
class TestItemFilterSetDistinct:
    """FR-005, FR-011, plan D-4: a filter match returns each reference once."""

    def test_a_contributor_credited_in_two_roles_is_returned_once(self):
        item = ItemFactory()
        darwin = NameFactory(family="Darwin")
        ItemNameFactory(item=item, name=darwin, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=darwin, role=NameRole.EDITOR)
        filterset = ItemFilterSet(data={"contributor": "darwin"}, queryset=Item.objects.all())
        assert list(filterset.qs) == [item]

    def test_two_related_rows_matching_the_same_filter_still_return_the_reference_once(self):
        item = ItemFactory()
        ItemNameFactory(item=item, name=NameFactory(family="Darwin"), role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=NameFactory(given="Darwiniana"), role=NameRole.EDITOR)
        filterset = ItemFilterSet(data={"contributor": "darwin"}, queryset=Item.objects.all())
        assert list(filterset.qs) == [item]


@pytest.mark.django_db
class TestItemFilterSetLanguage:
    """FR-013: the distinct language values the catalogue holds, as stored.

    Asserted against ``extra["choices"]`` — the list ``LanguageFilter.field``
    computes itself — rather than the built form field's own ``.choices``:
    the field additionally prepends its own "any" option (also keyed ``""``,
    a UI affordance and not a language), which would confound a check on the
    empty string specifically.
    """

    @staticmethod
    def _computed_choices(filterset):
        language_filter = filterset.filters["language"]
        _ = language_filter.field  # triggers LanguageFilter.field, which populates extra["choices"]
        return language_filter.extra["choices"]

    def test_choices_are_the_distinct_stored_languages(self):
        ItemFactory(language="en")
        ItemFactory(language="fr")
        filterset = ItemFilterSet(data={}, queryset=Item.objects.all())
        values = {value for value, _ in self._computed_choices(filterset)}
        assert values == {"en", "fr"}

    def test_choices_never_include_the_empty_string(self):
        ItemFactory(language="")
        ItemFactory(language="en")
        filterset = ItemFilterSet(data={}, queryset=Item.objects.all())
        values = {value for value, _ in self._computed_choices(filterset)}
        assert "" not in values

    def test_choices_never_offer_a_value_the_catalogue_does_not_hold(self):
        ItemFactory(language="en")
        filterset = ItemFilterSet(data={}, queryset=Item.objects.all())
        values = {value for value, _ in self._computed_choices(filterset)}
        assert "de" not in values

    def test_narrows_to_the_chosen_language(self):
        en_item = ItemFactory(language="en")
        ItemFactory(language="fr")
        filterset = ItemFilterSet(data={"language": "en"}, queryset=Item.objects.all())
        assert list(filterset.qs) == [en_item]


@pytest.mark.django_db
class TestItemFilterSetIssuedYear:
    """FR-012, plan D-5: the year filter, on the shared ``issued`` annotation."""

    def test_a_year_only_stored_date_qualifies(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        other = ItemFactory()
        ItemDateFactory(item=other, date_type=DateType.ISSUED, begin="2021")
        filterset = ItemFilterSet(data={"issued_year": 2020}, queryset=Item.objects.all())
        assert list(filterset.qs) == [item]

    def test_a_range_qualifies_for_the_year_it_begins_in(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2019", end="2021")
        other = ItemFactory()
        ItemDateFactory(item=other, date_type=DateType.ISSUED, begin="2021")
        filterset = ItemFilterSet(data={"issued_year": 2019}, queryset=Item.objects.all())
        assert list(filterset.qs) == [item]

    def test_a_range_does_not_qualify_for_a_year_it_only_ends_in(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2019", end="2021")
        filterset = ItemFilterSet(data={"issued_year": 2021}, queryset=Item.objects.all())
        assert list(filterset.qs) == []

    def test_a_reference_with_no_issued_date_is_excluded(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2020")
        filterset = ItemFilterSet(data={"issued_year": 2020}, queryset=Item.objects.all())
        assert list(filterset.qs) == []

    def test_a_reference_carrying_no_date_at_all_is_excluded(self):
        ItemFactory()
        filterset = ItemFilterSet(data={"issued_year": 2020}, queryset=Item.objects.all())
        assert list(filterset.qs) == []

    def test_unfiltered_the_annotation_is_still_present_for_ordering(self):
        # T007's own contract, not just the year filter's: the annotation is
        # applied unconditionally in filter_queryset(), so a view relying on
        # it for sort (ItemTable.order_issued) gets it whether or not a year
        # was requested.
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="2020")
        undated = ItemFactory()
        filterset = ItemFilterSet(data={}, queryset=Item.objects.all())
        annotated = {row.pk: row.issued for row in filterset.qs}
        assert annotated[item.pk] is not None
        assert annotated[undated.pk] is None

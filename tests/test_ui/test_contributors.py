"""Tests for ``literature/ui/contributors.py``."""

import pytest
from django.utils.translation import override

from literature.choices import NameRole
from literature.models import ItemName
from literature.ui.contributors import ContributorGroups, contributor_groups
from tests.factories import ItemFactory, ItemNameFactory, NameFactory


class TestRoleLabel:
    """A role's heading carries its own plural form, not a template-level "s"."""

    def test_one_name_reads_the_singular(self):
        assert ContributorGroups.role_label(NameRole.AUTHOR, 1) == "Author"

    def test_more_than_one_name_reads_the_plural(self):
        assert ContributorGroups.role_label(NameRole.AUTHOR, 3) == "Authors"

    def test_the_plural_is_a_message_of_its_own_not_the_singular_plus_a_letter(self):
        # The point of the pair: a translator supplies each form, so a language
        # whose plural is not "the singular plus a letter" is served correctly.
        # ``Boîtiers``-style forms and the three- and four-form languages both
        # depend on this being a separate message rather than a suffix.
        assert ContributorGroups.role_label(NameRole.EDITORIAL_DIRECTOR, 2) == "Editorial Directors"

    def test_every_role_has_a_label_pair(self):
        assert set(ContributorGroups.ROLE_LABELS) == set(NameRole)

    def test_an_unknown_role_falls_back_to_the_stored_value(self):
        # ``ItemName.role`` carries choices but the store accepts what it is
        # given; ``get_role_display()`` returns an unmapped value unchanged and
        # this does the same rather than raising on a row the catalogue holds.
        assert ContributorGroups.role_label("dedicatee", 2) == "dedicatee"

    def test_the_label_is_resolved_in_the_active_language(self):
        # Nothing is translated yet — the package ships the base English
        # catalog only — so this pins the mechanism rather than a translation:
        # the pair is evaluated at call time under the active locale, not
        # frozen at import.
        with override("en"):
            assert ContributorGroups.role_label(NameRole.TRANSLATOR, 2) == "Translators"


@pytest.mark.django_db
class TestContributorGroups:
    """Contributors grouped by role, in the order the store holds them."""

    def test_a_role_with_several_names_is_one_group_headed_by_the_plural(self):
        item = ItemFactory()
        for _ in range(3):
            ItemNameFactory(item=item, role=NameRole.AUTHOR)
        (group,) = contributor_groups(item)
        assert group["label"] == "Authors"
        assert len(group["names"]) == 3

    def test_a_role_with_one_name_is_headed_by_the_singular(self):
        item = ItemFactory()
        ItemNameFactory(item=item, role=NameRole.EDITOR)
        (group,) = contributor_groups(item)
        assert group["label"] == "Editor"

    def test_each_role_is_its_own_group(self):
        item = ItemFactory()
        ItemNameFactory(item=item, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, role=NameRole.EDITOR)
        labels = [group["label"] for group in contributor_groups(item)]
        assert labels == ["Authors", "Editor"]

    def test_names_keep_the_position_order_stored_within_a_role(self):
        item = ItemFactory()
        first = ItemNameFactory(item=item, role=NameRole.AUTHOR, name=NameFactory(family="Aardvark"))
        second = ItemNameFactory(item=item, role=NameRole.AUTHOR, name=NameFactory(family="Zebra"))
        (group,) = contributor_groups(item)
        assert group["names"] == [first.name, second.name]

    def test_an_item_with_no_contributors_has_no_groups(self):
        assert contributor_groups(ItemFactory()) == []

    def test_the_result_can_be_iterated_more_than_once(self):
        # The catalogue row is rendered from an annotation on the page's items;
        # a generator would be empty the second time anything looked at it.
        item = ItemFactory()
        ItemNameFactory(item=item, role=NameRole.AUTHOR)
        groups = contributor_groups(item)
        assert list(groups) == list(groups)

    def test_grouping_relies_on_the_stores_declared_role_ordering(self):
        # ``groupby`` only groups *consecutive* equal keys, so a role appearing
        # twice non-consecutively would render as two headings. What keeps that
        # from happening is ItemName's own ordering, not anything here.
        assert ItemName._meta.ordering == ["item", "role", "order"]

    def test_a_subclass_can_supply_its_own_role_labels(self):
        # The reason this is a class: a host calling its authors something else
        # overrides the table rather than patching a module function.
        class CreatorGroups(ContributorGroups):
            ROLE_LABELS = {**ContributorGroups.ROLE_LABELS, NameRole.AUTHOR: "Creators"}

        item = ItemFactory()
        ItemNameFactory(item=item, role=NameRole.AUTHOR)
        (group,) = CreatorGroups(item).groups()
        assert group["label"] == "Creators"

    def test_it_reads_the_prefetch_rather_than_querying_per_role(self, django_assert_num_queries):
        item = ItemFactory()
        ItemNameFactory(item=item, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, role=NameRole.EDITOR)
        prefetched = type(item).objects.prefetch_related("item_names__name").get(pk=item.pk)
        with django_assert_num_queries(0):
            contributor_groups(prefetched)

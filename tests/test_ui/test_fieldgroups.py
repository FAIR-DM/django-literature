"""Tests for ``literature/ui/fieldgroups.py`` — the type-to-field mapping.

Structural guarantees only (plan.md D-1, D-2): the partition of ``Item``'s form
fields into groups, and the per-type assignment's shape. What each of the 45
types is actually assigned is reviewed by reading the module itself, one
comment per type naming the criterion that decided it — a test can check the
shape of the mapping, not whether a particular editorial call was right.
"""

import pytest

from literature.choices import ItemType
from literature.ui.fieldgroups import FieldGroups
from tests.factories import ItemFactory
from tests.test_ui.conftest import EXCLUDED_FROM_FORM, scalar_field_names


class TestFieldPartition:
    """Every field of ``Item`` bar the four excluded ones belongs to exactly one group."""

    def test_every_form_field_is_assigned_to_a_group(self):
        assigned = {name for fields in FieldGroups.GROUPS.values() for name in fields}
        assert assigned == scalar_field_names() - EXCLUDED_FROM_FORM

    def test_no_field_belongs_to_two_groups(self):
        assigned = [name for fields in FieldGroups.GROUPS.values() for name in fields]
        assert len(assigned) == len(set(assigned))

    def test_none_of_the_four_excluded_fields_appear_in_any_group(self):
        assigned = {name for fields in FieldGroups.GROUPS.values() for name in fields}
        assert assigned.isdisjoint(EXCLUDED_FROM_FORM)


class TestTypeCoverage:
    """Every one of the 45 ``ItemType`` values resolves to a set of groups."""

    def test_every_item_type_has_an_entry(self):
        assert set(FieldGroups.TYPE_GROUPS.keys()) == set(ItemType.values)

    def test_core_and_general_are_in_every_types_groups(self):
        for item_type in ItemType.values:
            groups = FieldGroups.groups_for(item_type)
            assert "core" in groups
            assert "general" in groups

    def test_processor_is_in_no_types_groups(self):
        for item_type in ItemType.values:
            assert "processor" not in FieldGroups.groups_for(item_type)

    def test_every_group_a_type_names_is_a_real_group(self):
        referenced = {"core", "general"}
        for extra_groups in FieldGroups.TYPE_GROUPS.values():
            referenced |= set(extra_groups)
        assert referenced <= set(FieldGroups.GROUPS.keys())


class TestAssignmentCeiling:
    """A degenerate mapping — every group offered to every type — has nothing to fail it
    without an explicit ceiling (SC-002, DR-013)."""

    def test_article_journal_uses_fewer_than_half_the_forms_fields(self):
        groups = FieldGroups.groups_for(ItemType.ARTICLE_JOURNAL)
        assigned_field_count = sum(len(FieldGroups.GROUPS[group]) for group in groups)
        total_field_count = sum(len(fields) for fields in FieldGroups.GROUPS.values())
        # research.md §1's band tops out at 35 of a possible ~60; half is a
        # ceiling wide enough for a legitimately broad type while still
        # failing a mapping that assigns everything to everything.
        assert assigned_field_count < total_field_count / 2


class TestCorrectedC2Criterion:
    """C2a (plan.md D-1): a type that sits inside a container takes ``container``,
    not ``numbering`` alone. The first pass at this mapping read C2 as though the
    four clusters named in its parenthetical were the whole of it, so it read
    ``numbering`` off the "paginated inside a host" reasoning and never reached
    ``container`` for these types."""

    @pytest.mark.parametrize(
        "item_type",
        [
            ItemType.ARTICLE_JOURNAL,
            ItemType.ARTICLE_MAGAZINE,
            ItemType.ARTICLE_NEWSPAPER,
            ItemType.CHAPTER,
            ItemType.ENTRY,
            ItemType.ENTRY_DICTIONARY,
            ItemType.ENTRY_ENCYCLOPEDIA,
            ItemType.PAPER_CONFERENCE,
            ItemType.REVIEW,
            ItemType.REVIEW_BOOK,
            ItemType.BOOK,
            ItemType.BROADCAST,
            ItemType.MOTION_PICTURE,
            ItemType.REPORT,
            ItemType.SONG,
            ItemType.SPEECH,
            ItemType.WEBPAGE,
        ],
    )
    def test_container_is_offered_to_types_naming_a_containing_work(self, item_type):
        assert "container" in FieldGroups.groups_for(item_type)

    def test_software_is_offered_publication_for_its_version_field(self):
        assert "publication" in FieldGroups.groups_for(ItemType.SOFTWARE)

    def test_song_is_offered_numbering_for_its_chapter_number_field(self):
        # plan.md D-1 point 2: "`chapter-number` names chapter and song" — the
        # same itemized C2 evidence the original pass skipped for `container`
        # was skipped here too, since `song` is not one of the four named
        # clusters (legal/review/event/physical).
        assert "numbering" in FieldGroups.groups_for(ItemType.SONG)

    def test_book_is_offered_numbering_for_its_number_of_volumes_field(self):
        # plan.md D-1 point 2: "`number-of-volumes` and `ISBN` name the
        # book-like types."
        assert "numbering" in FieldGroups.groups_for(ItemType.BOOK)

    def test_patent_is_offered_legal_for_its_authority_and_jurisdiction_fields(self):
        # plan.md D-1 point 2: "`authority`, `jurisdiction` and `division`
        # name patent and the legal types" — patent is not itself one of the
        # named "legal types" cluster (legal_case, legislation, bill,
        # hearing, regulation, treaty), so this needed the itemized reading.
        assert "legal" in FieldGroups.groups_for(ItemType.PATENT)


class TestFieldsFor:
    def test_returns_the_fields_declared_for_the_named_group(self):
        assert FieldGroups.fields_for("core") == FieldGroups.GROUPS["core"]


@pytest.mark.django_db
class TestGroupsHoldingValues:
    """The forced-visible set FR-010 and FR-014 need — a group with a populated
    field stays on the page even when the current type does not use it."""

    def test_a_populated_fields_group_is_reported(self):
        item = ItemFactory(volume="12")
        assert "numbering" in FieldGroups.groups_holding_values(item)

    def test_a_group_with_no_populated_field_is_not_reported(self):
        item = ItemFactory()
        assert "numbering" not in FieldGroups.groups_holding_values(item)

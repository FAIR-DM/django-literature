"""Tests for ``literature/ui/fieldgroups.py``: the type-to-field mapping.

Structural guarantees only. Each type's assignment is an editorial call reviewed in the module
itself, not something a test can judge.
"""

import pytest

from literature.choices import DateType, ItemType
from literature.ui.fieldgroups import FieldGroups
from tests.factories import ItemFactory
from tests.test_ui.conftest import EXCLUDED_FROM_FORM, scalar_field_names


class TestFieldPartition:
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
    def test_article_journal_uses_fewer_than_half_the_forms_fields(self):
        groups = FieldGroups.groups_for(ItemType.ARTICLE_JOURNAL)
        assigned_field_count = sum(len(FieldGroups.GROUPS[group]) for group in groups)
        total_field_count = sum(len(fields) for fields in FieldGroups.GROUPS.values())
        # The broadest real type uses about 35 of ~60 fields; half is a
        # ceiling wide enough for a legitimately broad type while still
        # failing a mapping that assigns everything to everything.
        assert assigned_field_count < total_field_count / 2


class TestCorrectedC2Criterion:
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
        # `chapter-number` names chapter and song; `song` is not one of the four
        # named clusters, so a cluster-only reading misses it.
        assert "numbering" in FieldGroups.groups_for(ItemType.SONG)

    def test_book_is_offered_numbering_for_its_number_of_volumes_field(self):
        # `number-of-volumes` and `ISBN` name the book-like types.
        assert "numbering" in FieldGroups.groups_for(ItemType.BOOK)

    def test_patent_is_offered_legal_for_its_authority_and_jurisdiction_fields(self):
        # `authority`, `jurisdiction` and `division` name patent and the legal
        # types — patent is not itself one of the
        # named "legal types" cluster (legal_case, legislation, bill,
        # hearing, regulation, treaty), so this needed the itemized reading.
        assert "legal" in FieldGroups.groups_for(ItemType.PATENT)


class TestFieldsFor:
    def test_returns_the_fields_declared_for_the_named_group(self):
        assert FieldGroups.fields_for("core") == FieldGroups.GROUPS["core"]


class TestDateSlotCoverage:
    def test_every_item_type_has_an_entry(self):
        assert set(FieldGroups.TYPE_DATE_SLOTS.keys()) == set(ItemType.values)

    def test_every_named_slot_is_a_real_date_type(self):
        for slots in FieldGroups.TYPE_DATE_SLOTS.values():
            assert set(slots) <= set(DateType.values)

    def test_issued_is_never_named_because_it_is_always_on(self):
        # `issued` is the date-slot equivalent of `core`/`general` — carried by
        # every type without being named in any single entry.
        for slots in FieldGroups.TYPE_DATE_SLOTS.values():
            assert DateType.ISSUED not in slots

    def test_the_existing_field_partition_is_untouched(self):
        # Extending the mapping to date slots must not disturb the
        # scalar-field partition this test class already guards.
        assigned = {name for fields in FieldGroups.GROUPS.values() for name in fields}
        assert assigned == scalar_field_names() - EXCLUDED_FROM_FORM


class TestDateSlotAssignment:
    def test_webpage_leads_with_accessed(self):
        # CSL Appendix III: "Intended for
        # sources which are intrinsically online."
        assert DateType.ACCESSED in FieldGroups.TYPE_DATE_SLOTS[ItemType.WEBPAGE]

    def test_post_leads_with_accessed(self):
        # Appendix III: "A post on a online forum, social media platform...".
        assert DateType.ACCESSED in FieldGroups.TYPE_DATE_SLOTS[ItemType.POST]

    def test_post_weblog_does_not_lead_with_accessed(self):
        # post-weblog's own one-line definition ("A blog post") never uses
        # the word "online" the way post's does, so it stays at the baseline
        # rather than borrowing its sibling's evidence.
        assert (
            DateType.ACCESSED not in FieldGroups.TYPE_DATE_SLOTS[ItemType.POST_WEBLOG]
        )

    def test_paper_conference_leads_with_event_date(self):
        # The type already carries `event` in TYPE_GROUPS.
        assert (
            DateType.EVENT_DATE
            in FieldGroups.TYPE_DATE_SLOTS[ItemType.PAPER_CONFERENCE]
        )

    def test_event_speech_and_performance_lead_with_event_date(self):
        for item_type in (ItemType.EVENT, ItemType.SPEECH, ItemType.PERFORMANCE):
            assert DateType.EVENT_DATE in FieldGroups.TYPE_DATE_SLOTS[item_type]

    def test_book_leads_with_original_date(self):
        # "A translated or reissued work"; the type already carries `original` in TYPE_GROUPS.
        assert DateType.ORIGINAL_DATE in FieldGroups.TYPE_DATE_SLOTS[ItemType.BOOK]

    def test_classic_leads_with_original_date(self):
        assert DateType.ORIGINAL_DATE in FieldGroups.TYPE_DATE_SLOTS[ItemType.CLASSIC]

    def test_manuscript_leads_with_submitted(self):
        # Appendix IV's own definition of `submitted`: "Date the item (e.g. a
        # manuscript) was submitted for publication."
        assert DateType.SUBMITTED in FieldGroups.TYPE_DATE_SLOTS[ItemType.MANUSCRIPT]

    def test_article_journal_leads_with_available_date(self):
        # Appendix IV's own definition of `available-date`: "e.g. the online
        # publication date of a journal article before its formal
        # publication date".
        assert (
            DateType.AVAILABLE_DATE
            in FieldGroups.TYPE_DATE_SLOTS[ItemType.ARTICLE_JOURNAL]
        )

    def test_treaty_leads_with_available_date(self):
        # Appendix IV's own definition of `available-date`: "the date a
        # treaty was made available for signing".
        assert DateType.AVAILABLE_DATE in FieldGroups.TYPE_DATE_SLOTS[ItemType.TREATY]

    def test_document_has_no_evidenced_slot_beyond_issued(self):
        # CSL's catch-all type, named by neither appendix for any date slot.
        assert FieldGroups.TYPE_DATE_SLOTS[ItemType.DOCUMENT] == frozenset()


@pytest.mark.django_db
class TestGroupsHoldingValues:
    def test_a_populated_fields_group_is_reported(self):
        item = ItemFactory(volume="12")
        assert "numbering" in FieldGroups.groups_holding_values(item)

    def test_a_group_with_no_populated_field_is_not_reported(self):
        item = ItemFactory()
        assert "numbering" not in FieldGroups.groups_holding_values(item)

"""Tests for ``literature/ui/fields.py``."""

import pytest

from literature.choices import DateType
from literature.ui.fieldgroups import FieldGroups
from literature.ui.fields import field_sections, issued_year
from tests.factories import ItemDateFactory, ItemFactory


def labels_of(sections):
    return [str(section["label"]) for section in sections]


def rows_of(sections):
    return {
        str(label): value for section in sections for label, value in section["rows"]
    }


@pytest.mark.django_db
class TestFieldSections:
    def test_a_carried_field_appears_under_its_groups_heading(self):
        item = ItemFactory(volume="12")
        sections = field_sections(item)
        numbering = next(
            section
            for section in sections
            if section["label"] == FieldGroups.GROUP_LABELS["numbering"]
        )
        assert (item._meta.get_field("volume").verbose_name, "12") in numbering["rows"]

    def test_blank_and_null_fields_are_left_out(self):
        item = ItemFactory(volume="", issue="")
        rows = rows_of(field_sections(item))
        assert str(item._meta.get_field("volume").verbose_name) not in rows
        assert str(item._meta.get_field("issue").verbose_name) not in rows

    def test_a_group_holding_no_value_has_no_section(self):
        item = ItemFactory(volume="12")
        assert str(FieldGroups.GROUP_LABELS["legal"]) not in labels_of(
            field_sections(item)
        )

    def test_sections_follow_the_edit_forms_group_order(self):
        item = ItemFactory(volume="12", publisher="MIT Press", note="A note")
        order = [str(label) for label in FieldGroups.GROUP_LABELS.values()]
        labels = labels_of(field_sections(item))
        assert labels == sorted(labels, key=order.index)

    def test_fields_shown_in_the_page_header_are_not_repeated(self):
        item = ItemFactory(title="A Title", abstract="An abstract", citation_key="K1")
        rows = rows_of(field_sections(item))
        for name in ("type", "citation_key", "title", "abstract"):
            assert str(item._meta.get_field(name).verbose_name) not in rows


@pytest.mark.django_db
class TestIssuedYear:
    def test_returns_the_year_of_the_issued_date(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin="1948-07")
        assert issued_year(item) == 1948

    def test_ignores_other_kinds_of_date(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ACCESSED, begin="2020")
        assert issued_year(item) is None

    def test_an_issued_date_held_only_as_text_has_no_year(self):
        item = ItemFactory()
        ItemDateFactory(item=item, date_type=DateType.ISSUED, literal="Spring 1990")
        assert issued_year(item) is None

"""Tests for ``literature/models.py``."""

import pytest
from django.core.exceptions import ValidationError
from partial_date import PartialDate

from literature.choices import DateType, IdentifierType, ItemType, NameRole
from literature.models import Item, ItemDate, ItemIdentifier, ItemName, Name
from tests.factories import (
    ItemDateFactory,
    ItemFactory,
    ItemIdentifierFactory,
    ItemNameFactory,
    NameFactory,
)


@pytest.mark.django_db
class TestItemModel:
    @pytest.mark.parametrize("item_type", ItemType.values)
    def test_crud_all_types(self, item_type):
        citation_key = f"TestKey2024_{item_type}"
        item = ItemFactory(citation_key=citation_key, type=item_type)
        retrieved = Item.objects.get(pk=item.pk)
        assert retrieved.citation_key == citation_key
        assert retrieved.type == item_type

    def test_required_fields_only(self):
        item = ItemFactory(citation_key="Minimal2024", type=ItemType.ARTICLE_JOURNAL)
        assert item.pk is not None

    def test_optional_fields_persist(self):
        item = ItemFactory(
            citation_key="Full2024",
            type=ItemType.BOOK,
            title="The Full Book",
            title_short="Full Book",
            abstract="An abstract.",
            publisher="Test Publisher",
            publisher_place="Test City",
            volume="2",
            issue="3",
            page="100-200",
            language="en",
            keyword="science, research",
            categories=["cat1", "cat2"],
            custom={"extra": "value"},
        )
        retrieved = Item.objects.get(pk=item.pk)
        assert retrieved.title == "The Full Book"
        assert retrieved.title_short == "Full Book"
        assert retrieved.abstract == "An abstract."
        assert retrieved.publisher == "Test Publisher"
        assert retrieved.publisher_place == "Test City"
        assert retrieved.volume == "2"
        assert retrieved.issue == "3"
        assert retrieved.page == "100-200"
        assert retrieved.language == "en"
        assert retrieved.keyword == "science, research"
        assert retrieved.categories == ["cat1", "cat2"]
        assert retrieved.custom == {"extra": "value"}

    def test_str_returns_citation_key(self):
        item = ItemFactory(citation_key="CiteKey2024", type=ItemType.ARTICLE)
        assert str(item) == "CiteKey2024"
        assert len(str(item)) > 0

    def test_str_returns_title_when_set(self):
        item = ItemFactory(
            citation_key="CiteKey2024", type=ItemType.ARTICLE, title="A Short Title"
        )
        assert str(item) == "A Short Title"

    def test_str_fallback_to_citation_key(self):
        item = ItemFactory(citation_key="FallbackKey", type=ItemType.BOOK, title="")
        assert str(item) == "FallbackKey"

    def test_str_truncates_long_title(self):
        long_title = "A" * 81
        item = ItemFactory(
            citation_key="LongTitle2024", type=ItemType.BOOK, title=long_title
        )
        result = str(item)
        assert result == "A" * 80 + "…"
        assert len(result) == 81  # 80 chars + 1 ellipsis char

    def test_auto_timestamps_set_on_creation(self):
        item = ItemFactory(citation_key="Auto2024", type=ItemType.REPORT)
        assert item.created is not None
        assert item.modified is not None


@pytest.mark.django_db
class TestNameModel:
    def test_all_parts_persist(self):
        name = NameFactory(
            family="Smith",
            given="John A.",
            dropping_particle="von",
            non_dropping_particle="de",
            suffix="Jr.",
            literal="",
            comma_suffix=True,
            static_ordering=False,
            parse_names=True,
        )
        retrieved = Name.objects.get(pk=name.pk)
        assert retrieved.family == "Smith"
        assert retrieved.given == "John A."
        assert retrieved.dropping_particle == "von"
        assert retrieved.non_dropping_particle == "de"
        assert retrieved.suffix == "Jr."
        assert retrieved.comma_suffix is True
        assert retrieved.static_ordering is False
        assert retrieved.parse_names is True

    def test_literal_only(self):
        name = NameFactory(family="", given="", literal="World Health Organization")
        retrieved = Name.objects.get(pk=name.pk)
        assert retrieved.literal == "World Health Organization"
        assert retrieved.family == ""
        assert retrieved.given == ""

    def test_str_family_given(self):
        name = NameFactory(family="Smith", given="John")
        result = str(name)
        assert len(result) > 0
        assert "Smith" in result

    def test_str_family_given_format(self):
        name = NameFactory(family="Smith", given="John")
        assert str(name) == "Smith, John"

    def test_str_family_only(self):
        name = NameFactory(family="Smith", given="")
        assert str(name) == "Smith"

    def test_str_literal_fallback(self):
        name = NameFactory(family="", given="", literal="Harvard University")
        assert str(name) == "Harvard University"

    def test_str_pk_fallback(self):
        name = NameFactory(family="", given="", literal="")
        assert str(name) == f"Name #{name.pk}"

    def test_str_literal_only(self):
        name = NameFactory(family="", given="", literal="World Health Organization")
        result = str(name)
        assert len(result) > 0
        assert "World Health Organization" in result


@pytest.mark.django_db
class TestItemNameModel:
    def test_records_role(self, item, name):
        item_name = ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)
        assert item_name.role == NameRole.AUTHOR

    def test_unique_constraint(self, item, name):
        ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)
        with pytest.raises(Exception):  # IntegrityError on duplicate
            ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)

    def test_multiple_roles_same_name(self, item, name):
        ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=name, role=NameRole.EDITOR)
        assert ItemName.objects.filter(item=item, name=name).count() == 2

    def test_ordering_preserved(self, item):
        n1 = NameFactory(family="First", given="A")
        n2 = NameFactory(family="Second", given="B")
        n3 = NameFactory(family="Third", given="C")
        ItemNameFactory(item=item, name=n1, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=n2, role=NameRole.AUTHOR)
        ItemNameFactory(item=item, name=n3, role=NameRole.AUTHOR)
        ordered = list(
            ItemName.objects.filter(item=item, role=NameRole.AUTHOR).order_by("order")
        )
        assert [in_.name.family for in_ in ordered] == ["First", "Second", "Third"]

    def test_ordering_scoped_per_role(self, item):
        a1 = ItemNameFactory(
            item=item, name=NameFactory(family="Auth1"), role=NameRole.AUTHOR
        )
        e1 = ItemNameFactory(
            item=item, name=NameFactory(family="Edit1"), role=NameRole.EDITOR
        )
        a2 = ItemNameFactory(
            item=item, name=NameFactory(family="Auth2"), role=NameRole.AUTHOR
        )
        a1.refresh_from_db()
        e1.refresh_from_db()
        a2.refresh_from_db()
        assert [a1.order, a2.order] == [0, 1]
        assert e1.order == 0

    def test_str_non_empty(self, item, name):
        item_name = ItemNameFactory(item=item, name=name, role=NameRole.AUTHOR)
        assert len(str(item_name)) > 0


@pytest.mark.django_db
class TestItemDateModel:
    def test_year_only(self, item):
        item_date = ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin=PartialDate("2019")
        )
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin) == "2019"

    def test_year_month(self, item):
        item_date = ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08")
        )
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08")

    def test_full_date(self, item):
        item_date = ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16")
        )
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08-16")

    def test_range(self, item):
        item_date = ItemDateFactory(
            item=item,
            date_type=DateType.EVENT_DATE,
            begin=PartialDate("2019-08-12"),
            end=PartialDate("2019-08-16"),
        )
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08-12")
        assert str(retrieved.end).startswith("2019-08-16")

    def test_unique_constraint(self, item):
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2019"))
        with pytest.raises(Exception):  # IntegrityError on duplicate
            ItemDateFactory(
                item=item, date_type=DateType.ISSUED, begin=PartialDate("2020")
            )

    def test_str_non_empty(self, item):
        item_date = ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin=PartialDate("2019-08-16")
        )
        assert len(str(item_date)) > 0

    def test_all_fields(self, item):
        item_date = ItemDateFactory(
            item=item,
            date_type=DateType.SUBMITTED,
            season="1",
            circa=True,
            literal="Spring 2019",
            raw="2019 spring",
            raw_date_parts=[[2019]],
        )
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert retrieved.season == "1"
        assert retrieved.circa is True
        assert retrieved.literal == "Spring 2019"
        assert retrieved.raw == "2019 spring"
        assert retrieved.raw_date_parts == [[2019]]


@pytest.mark.django_db
class TestItemDateSpanRule:
    def test_end_without_begin_is_rejected(self, item):
        with pytest.raises(ValidationError):
            ItemDateFactory(
                item=item,
                date_type=DateType.EVENT_DATE,
                begin=None,
                end=PartialDate("2019-08-16"),
            )
        assert not ItemDate.objects.filter(
            item=item, date_type=DateType.EVENT_DATE
        ).exists()

    def test_end_before_begin_is_rejected(self, item):
        with pytest.raises(ValidationError):
            ItemDateFactory(
                item=item,
                date_type=DateType.EVENT_DATE,
                begin=PartialDate("2019-08-16"),
                end=PartialDate("2019-08-12"),
            )
        assert not ItemDate.objects.filter(
            item=item, date_type=DateType.EVENT_DATE
        ).exists()

    def test_end_equal_to_begin_is_accepted(self, item):
        item_date = ItemDateFactory(
            item=item,
            date_type=DateType.EVENT_DATE,
            begin=PartialDate("2019-08-16"),
            end=PartialDate("2019-08-16"),
        )
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08-16")
        assert str(retrieved.end).startswith("2019-08-16")

    def test_end_after_begin_is_accepted(self, item):
        item_date = ItemDateFactory(
            item=item,
            date_type=DateType.EVENT_DATE,
            begin=PartialDate("2019-08-12"),
            end=PartialDate("2019-08-16"),
        )
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08-12")
        assert str(retrieved.end).startswith("2019-08-16")

    def test_mixed_precision_span_is_accepted(self, item):
        item_date = ItemDateFactory(
            item=item,
            date_type=DateType.EVENT_DATE,
            begin=PartialDate("2019-08-16"),
            end=PartialDate("2020"),
        )
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08-16")
        assert str(retrieved.end) == "2020"

    def test_direct_create_rejects_the_defect(self, item):
        with pytest.raises(ValidationError):
            ItemDate.objects.create(
                item=item,
                date_type=DateType.EVENT_DATE,
                begin=None,
                end=PartialDate("2019"),
            )

    def test_instance_save_rejects_the_defect(self, item):
        with pytest.raises(ValidationError):
            ItemDate(
                item=item,
                date_type=DateType.EVENT_DATE,
                begin=None,
                end=PartialDate("2019"),
            ).save()

    def test_an_empty_string_end_is_treated_as_no_end(self, item):
        # A ModelForm leaves a blank optional end as "", never None, and clean() sees it
        # unconverted.
        item_date = ItemDate(
            item=item,
            date_type=DateType.EVENT_DATE,
            begin=PartialDate("2019-08-16"),
            end="",
        )
        item_date.save()
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08-16")
        assert not retrieved.end

    def test_raw_date_strings_are_compared_correctly(self, item):
        # clean() alone never runs clean_fields(), so a raw date string reaches it unconverted.
        item_date = ItemDate(
            item=item,
            date_type=DateType.EVENT_DATE,
            begin="2019-08-12",
            end="2019-08-16",
        )
        item_date.save()
        retrieved = ItemDate.objects.get(pk=item_date.pk)
        assert str(retrieved.begin).startswith("2019-08-12")
        assert str(retrieved.end).startswith("2019-08-16")

    def test_raw_date_strings_out_of_order_are_still_rejected(self, item):
        with pytest.raises(ValidationError):
            ItemDate(
                item=item,
                date_type=DateType.EVENT_DATE,
                begin="2019-08-16",
                end="2019-08-12",
            ).save()


@pytest.mark.django_db
class TestItemIdentifierModel:
    @pytest.mark.parametrize(
        "identifier_type,value",
        [
            (IdentifierType.DOI, "10.1093/gji/ggz376"),
            (IdentifierType.ISBN, "978-3-16-148410-0"),
            (IdentifierType.ISSN, "0956-540X"),
            (IdentifierType.PMID, "19482853"),
            (IdentifierType.PMCID, "PMC2728067"),
            (IdentifierType.URL, "https://example.com/article"),
        ],
    )
    def test_known_types(self, item, identifier_type, value):
        ident = ItemIdentifierFactory(item=item, type=identifier_type, value=value)
        retrieved = ItemIdentifier.objects.get(pk=ident.pk)
        assert retrieved.type == identifier_type
        assert retrieved.value == value

    def test_unknown_type(self, item):
        ident = ItemIdentifierFactory(item=item, type="arXiv", value="2103.12345")
        retrieved = ItemIdentifier.objects.get(pk=ident.pk)
        assert retrieved.type == "arXiv"
        assert retrieved.value == "2103.12345"

    def test_unique_constraint(self, item):
        ItemIdentifierFactory(item=item, type=IdentifierType.DOI, value="10.1234/first")
        with pytest.raises(Exception):  # IntegrityError on duplicate
            ItemIdentifierFactory(
                item=item, type=IdentifierType.DOI, value="10.1234/second"
            )

    def test_str_non_empty(self, item):
        ident = ItemIdentifierFactory(
            item=item, type=IdentifierType.DOI, value="10.1234/test"
        )
        assert len(str(ident)) > 0


@pytest.mark.django_db
class TestItemIdentifierWritePathValidation:
    @pytest.mark.parametrize(
        "identifier_type,value",
        [
            (IdentifierType.DOI, "not-a-doi"),
            (IdentifierType.ISBN, "978-3-16-148410-1"),
            (IdentifierType.ISSN, "0956540X"),
            (IdentifierType.PMID, "not-numeric"),
            (IdentifierType.PMCID, "PMC-oops"),
            (IdentifierType.URL, "/relative/path"),
        ],
    )
    def test_direct_create_rejects_invalid_known_type(
        self, item, identifier_type, value
    ):
        with pytest.raises(ValidationError):
            ItemIdentifier.objects.create(item=item, type=identifier_type, value=value)
        assert not ItemIdentifier.objects.filter(
            item=item, type=identifier_type
        ).exists()

    def test_instance_save_rejects_invalid_known_type(self, item):
        with pytest.raises(ValidationError):
            ItemIdentifier(
                item=item, type=IdentifierType.DOI, value="10.1/too-few-digits"
            ).save()

    def test_update_to_invalid_value_is_rejected(self, item):
        ident = ItemIdentifierFactory(
            item=item, type=IdentifierType.DOI, value="10.1234/valid"
        )
        ident.value = "not-a-doi"
        with pytest.raises(ValidationError):
            ident.save()
        assert ItemIdentifier.objects.get(pk=ident.pk).value == "10.1234/valid"

    def test_direct_create_accepts_unknown_type(self, item):
        ident = ItemIdentifier.objects.create(
            item=item, type="arXiv", value="anything at all"
        )
        assert ItemIdentifier.objects.get(pk=ident.pk).value == "anything at all"

    def test_bulk_create_bypasses_validation(self, item):
        ItemIdentifier.objects.bulk_create(
            [ItemIdentifier(item=item, type=IdentifierType.DOI, value="not-a-doi")]
        )
        assert (
            ItemIdentifier.objects.get(item=item, type=IdentifierType.DOI).value
            == "not-a-doi"
        )


#: Item fields with no CSL JSON key: Django bookkeeping and reverse relations.
NON_CSL_FIELDS = frozenset(
    {
        "id",
        "created",
        "modified",
        "item_names",
        "itemname_set",
        "itemdate_set",
        "itemidentifier_set",
        "item_dates",
        "item_identifiers",
    }
)

ITEM_CSL_FIELD_NAMES = [
    field.name
    for field in Item._meta.get_fields()
    if field.name not in NON_CSL_FIELDS and hasattr(field, "help_text")
]


class TestHelpTextCoverage:
    @pytest.mark.parametrize("field_name", ITEM_CSL_FIELD_NAMES)
    def test_item_field_has_help_text(self, field_name):
        field = Item._meta.get_field(field_name)
        assert field.help_text, (
            f"Item.{field_name} is missing help_text describing its CSL JSON mapping"
        )
